import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import uuid
#serve a Python per andare a "pescare" le informazioni che non sono scritte nel codice, 
#ma che si trovano nascoste nel file Token.env.
import os 
#Importa la funzione per caricare i file Token.env
from dotenv import load_dotenv #Il file Token.env è come un foglietto segreto dove scrivi le tue chiavi segrete



app = Flask(__name__)
CORS(app)


# CONFIGURAZIONE AI
load_dotenv() #Legge il file .env che hai creato e carica tutte le scritte (tipo HF_TOKEN=...) nella memoria temporanea del computer.
# Recupera il valore associato alla chiave "HF_TOKEN" definito nel file .env.
# La variabile 'token' ora contiene la chiave segreta da usare.
token = os.getenv("HF_TOKEN") 

# Verifica rapida all'avvio (senza stampare tutto il token per sicurezza)
if token:
    print(f" Token caricato correttamente: {token[:4]}***")
else:
    print(" ERRORE: Token non trovato nel file Token.env")

# URL del modello AI
API_URL = "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct"

# 4. Creo gli headers con l'Authorization con il token
headers = {
    "Authorization": f"Bearer {token}", #Invia il token segreto insieme alla richiesta. 
    #Hugging Face deve sapere chi sta facendo la domanda. Senza questo, 
    #il server risponderebbe con un errore, perché non sa se hai il permesso di usare quel modello.
    "Content-Type": "application/json",
    "User-Agent": "SafeClaimBot/1.0"
}


# CONFIGURAZIONE MONGODB
MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
MONGO_DB_NAME = "safeclaim_mongo"

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[MONGO_DB_NAME]
    conversations_collection = db["conversations"]
    print("✅ MongoDB: Connesso")
except Exception as e:
    print(f"⚠️ MongoDB: Connessione fallita ({e})")
    mongo_client = None


# STORE IN-MEMORY PER SESSIONI
active_sessions = {}


class ConversationSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.messages = []
        self.created_at = datetime.now()
        self.feedback_data = []
        
    def add_message(self, role, content):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_context(self):
        context = ""
        for msg in self.messages[-6:]:
            context += f"{msg['role'].upper()}: {msg['content']}\n"
        return context
    
    def add_feedback(self, rating, comment=""):
        self.feedback_data.append({
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.now().isoformat()
        })
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "feedback": self.feedback_data
        }


def carica_conoscenza():
    try:
        with open("RegoleSinistriChatBot.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Info: Compilare modulo CAI."


def genera_suggerimenti(conversazione):
    if len(conversazione.messages) < 2:
        return [
            "Come funziona il processo di sinistro?",
            "Quali documenti mi servono?",
            "Quanto tempo ci vuole?"
        ]
    return [
        "Puoi spiegare meglio?",
        "Quali sono i prossimi step?",
        "Come contatto l'assistenza?"
    ]


@app.route('/chat/init', methods=['POST'])
def init_chat():
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = ConversationSession(session_id)
    return jsonify({
        "status": "success",
        "session_id": session_id
    }), 200


@app.route('/chat', methods=['POST'])
def chat_bot():
    data = request.json
    session_id = data.get('session_id')
    messaggio = data.get('messaggio')
    
    if not session_id or not messaggio:
        return jsonify({"error": "Mancano session_id o messaggio"}), 400
    
    if session_id not in active_sessions:
        active_sessions[session_id] = ConversationSession(session_id)
    
    conversazione = active_sessions[session_id]
    conversazione.add_message("user", messaggio)
    
    context = carica_conoscenza()
    context_history = conversazione.get_context()
    
    prompt = f"""<|user|>
Sei l'assistente SafeClaim. Aiuta l'utente durante la sua esperienza.

INFO REGOLE: {context}

{context_history}

Domanda attuale: {messaggio}

Fornisci una risposta chiara, concisa e utile. Sii empatico e disponibile.
<|end|>
<|assistant|>"""
    
    try:
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 300, "temperature": 0.4, "return_full_text": False},
            "options": {"wait_for_model": True}
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            return jsonify({
                "error": "Errore server AI",
                "status_code": response.status_code
            }), response.status_code
        
        output = response.json()
        risposta_ai = output[0]['generated_text'].strip()
        
        conversazione.add_message("assistant", risposta_ai)
        suggerimenti = genera_suggerimenti(conversazione)
        
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "risposta": risposta_ai,
            "suggerimenti": suggerimenti,
            "numero_messaggi": len(conversazione.messages)
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/chat/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    session_id = data.get('session_id')
    rating = data.get('rating', 0)
    comment = data.get('comment', '')
    
    if not session_id or session_id not in active_sessions:
        return jsonify({"error": "Sessione non trovata"}), 404
    
    conversazione = active_sessions[session_id]
    conversazione.add_feedback(rating, comment)
    
    if mongo_client:
        try:
            conversations_collection.insert_one(conversazione.to_dict())
        except Exception as e:
            print(f"⚠️ Errore MongoDB: {e}")
    
    return jsonify({"status": "success"}), 200


@app.route('/chat/history/<session_id>', methods=['GET'])
def get_history(session_id):
    if session_id not in active_sessions:
        return jsonify({"error": "Sessione non trovata"}), 404
    
    conversazione = active_sessions[session_id]
    return jsonify({
        "status": "success",
        "messages": conversazione.messages
    }), 200


@app.route('/chat/end/<session_id>', methods=['POST'])
def end_chat(session_id):
    if session_id not in active_sessions:
        return jsonify({"error": "Sessione non trovata"}), 404
    
    conversazione = active_sessions[session_id]
    
    if mongo_client:
        try:
            conversations_collection.insert_one(conversazione.to_dict())
        except Exception as e:
            print(f"⚠️ Errore MongoDB: {e}")
    
    del active_sessions[session_id]
    return jsonify({"status": "success"}), 200


if __name__ == '__main__':
    print("Chatbot SafeClaim pronto sulla porta 5001!")
    app.run(debug=True, port=5001)

