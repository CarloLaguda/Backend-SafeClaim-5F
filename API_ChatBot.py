import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import uuid
from dotenv import load_dotenv

# --- NUOVI IMPORT PER IL RAG ---
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

app = Flask(__name__)
CORS(app)

# CONFIGURAZIONE AI
# Usa un modello pubblico disponibile su Hugging Face Inference.
# Se continui a ricevere 404, il problema è probabilmente il token/permessi, non il modello.
API_URL = "https://api-inference.huggingface.co/models/gpt2"
load_dotenv('Token.env')
HF_API_TOKEN = os.getenv('HF_TOKEN', '')

headers = {
    "Content-Type": "application/json",
    "User-Agent": "SafeClaimBot/1.0"
}

if HF_API_TOKEN:
    headers["Authorization"] = f"Bearer {HF_API_TOKEN}"

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

# --- CONFIGURAZIONE RAG (FAISS) ---
embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_db = None

def inizializza_rag():
    global vector_db
    try:
        # Apriamo il file di testo contenente le regole dei sinistri
        with open("RegoleSinistriChatBot.txt", "r", encoding="utf-8") as f:
            documento = f.read()
            
        # Creiamo i chunk
        text_splitter = CharacterTextSplitter(
            chunk_size=300,      # Aumentato un po' rispetto a Colab per dare più contesto
            chunk_overlap=50,
            separator="\n"
        )
        chunks = text_splitter.split_text(documento)
        
        # Inizializziamo il database vettoriale in memoria
        vector_db = FAISS.from_texts(chunks, embeddings_model)
        print(f"✅ RAG: Database vettoriale pronto! Creati {len(chunks)} chunk.")
    except Exception as e:
        print(f"⚠️ RAG: Errore durante l'inizializzazione ({e})")

# Chiamiamo la funzione all'avvio dell'app per preparare il database
inizializza_rag()

# --- GESTIONE SESSIONI ---
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

# --- FUNZIONE MODIFICATA PER RECUPERARE IL CONTESTO TRAMITE RAG ---
def recupera_conoscenza_rag(domanda):
    if vector_db is None:
        return "Info: Compilare modulo CAI." # Fallback se FAISS non è partito
    
    # Cerchiamo i 3 chunk più simili alla domanda dell'utente
    documenti_trovati = vector_db.similarity_search(domanda, k=3)
    
    # Uniamo i risultati
    return "\n".join([d.page_content for d in documenti_trovati])

def genera_suggerimenti(conversazione):
    if len(conversazione.messages) < 2:
        return [
            "Come funziona il processo di sinistro?",
            "Quali documenti mi servono per il CID?",
            "Cosa faccio se l'altra persona non vuole firmare?"
        ]
    return [
        "Puoi spiegare meglio?",
        "Quali sono i prossimi step?",
        "Come contatto l'assistenza legale?"
    ]

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
    
    # --- RAG IN AZIONE ---
    # Recuperiamo SOLO le info pertinenti dal PDF/TXT usando FAISS
    context_rag = recupera_conoscenza_rag(messaggio) 
    context_history = conversazione.get_context()
    
    prompt = f"""[INST] Sei l'assistente dell'app SafeClaim. Aiuta l'utente coinvolto in un incidente d'auto a seguire correttamente le procedure.
Basa le tue risposte SOLO sulle seguenti regole del sistema. Se non trovi la risposta nelle regole, consiglia all'utente di chiamare il supporto clienti.

INFO REGOLE (CONTESTO SPECIFICO): 
{context_rag}

STORIA CONVERSAZIONE:
{context_history}

Domanda attuale dell'utente: {messaggio}

Fornisci una risposta chiara, concisa, passo-passo e utile. Sii empatico, rassicurante e disponibile. [/INST]"""
    
    try:
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 300, "temperature": 0.3, "return_full_text": False},
            "options": {"wait_for_model": True}
        }

        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            error_detail = response.text[:200] if response.text else "Errore sconosciuto"
            # FALLBACK: usa solo il contesto RAG senza AI
            risposta_ai = f"Basandomi sulle regole del sistema: {context_rag[:500]}... Per assistenza completa, contatta il supporto clienti."
            print(f"⚠️ API AI fallita ({response.status_code}), uso fallback")
        else:
            output = response.json()

            # Validazione della risposta
            if not output or len(output) == 0:
                risposta_ai = f"Basandomi sulle regole del sistema: {context_rag[:500]}... Per assistenza completa, contatta il supporto clienti."
                print("⚠️ Risposta AI vuota, uso fallback")
            elif 'generated_text' not in output[0]:
                risposta_ai = f"Basandomi sulle regole del sistema: {context_rag[:500]}... Per assistenza completa, contatta il supporto clienti."
                print("⚠️ Formato risposta AI inaspettato, uso fallback")
            else:
                risposta_ai = output[0]['generated_text'].strip()
                if not risposta_ai:
                    risposta_ai = f"Basandomi sulle regole del sistema: {context_rag[:500]}... Per assistenza completa, contatta il supporto clienti."
                    print("⚠️ Risposta AI vuota, uso fallback")
        
        conversazione.add_message("assistant", risposta_ai)
        suggerimenti = genera_suggerimenti(conversazione)
        
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "risposta": risposta_ai,
            "suggerimenti": suggerimenti,
            "numero_messaggi": len(conversazione.messages)
        }), 200
    
    except requests.exceptions.Timeout:
        return jsonify({"status": "error", "message": "API timeout - riprovare più tardi"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": f"Errore connessione API: {str(e)}"}), 503
    except (KeyError, IndexError, ValueError) as e:
        return jsonify({"status": "error", "message": "Errore parsing risposta AI"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ROUTE MANCANTI ---
@app.route('/chat/init', methods=['POST'])
def chat_init():
    """Inizializza una nuova sessione di chat"""
    try:
        session_id = str(uuid.uuid4())
        active_sessions[session_id] = ConversationSession(session_id)
        
        # Salva in MongoDB se disponibile
        if mongo_client:
            try:
                conversations_collection.insert_one({
                    "session_id": session_id,
                    "created_at": datetime.now(),
                    "status": "active"
                })
            except Exception as db_e:
                print(f"⚠️ Errore salvataggio MongoDB: {db_e}")
        
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "messaggio": "Sessione inizializzata"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/chat/feedback', methods=['POST'])
def chat_feedback():
    """Registra il feedback dell'utente sulla risposta del chatbot"""
    try:
        data = request.json
        session_id = data.get('session_id')
        rating = data.get('rating')  # 1-5
        comment = data.get('comment', '')
        
        if not session_id or rating is None:
            return jsonify({"error": "Mancano session_id o rating"}), 400
        
        if session_id not in active_sessions:
            return jsonify({"error": "Sessione non trovata"}), 404
        
        conversazione = active_sessions[session_id]
        conversazione.add_feedback(rating, comment)
        
        # Salva il feedback in MongoDB
        if mongo_client:
            try:
                conversations_collection.update_one(
                    {"session_id": session_id},
                    {"$push": {"feedback": {
                        "rating": rating,
                        "comment": comment,
                        "timestamp": datetime.now().isoformat()
                    }}}
                )
            except Exception as db_e:
                print(f"⚠️ Errore salvataggio feedback MongoDB: {db_e}")
        
        return jsonify({
            "status": "success",
            "message": "Feedback registrato",
            "session_id": session_id
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/chat/history/<session_id>', methods=['GET'])
def chat_history(session_id):
    """Recupera la cronologia della conversazione per una sessione"""
    try:
        if session_id not in active_sessions:
            return jsonify({"error": "Sessione non trovata"}), 404
        
        conversazione = active_sessions[session_id]
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "data": conversazione.to_dict()
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/chat/end', methods=['POST'])
def chat_end():
    """Termina una sessione e salva i dati"""
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({"error": "Manca session_id"}), 400
        
        if session_id not in active_sessions:
            return jsonify({"error": "Sessione non trovata"}), 404
        
        conversazione = active_sessions[session_id]
        
        # Salva i dati completi in MongoDB
        if mongo_client:
            try:
                conversations_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "messages": conversazione.messages,
                        "feedback": conversazione.feedback_data,
                        "ended_at": datetime.now().isoformat(),
                        "status": "closed"
                    }},
                    upsert=True
                )
            except Exception as db_e:
                print(f"⚠️ Errore salvataggio finale MongoDB: {db_e}")
        
        # Rimuovi dalla memoria attiva
        del active_sessions[session_id]
        
        return jsonify({
            "status": "success",
            "message": "Sessione terminata",
            "session_id": session_id,
            "numero_messaggi": len(conversazione.messages)
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Verifica lo stato del servizio"""
    try:
        mongo_status = "connected" if mongo_client else "disconnected"
        rag_status = "ready" if vector_db else "not_initialized"
        
        return jsonify({
            "status": "ok",
            "mongodb": mongo_status,
            "rag": rag_status,
            "active_sessions": len(active_sessions),
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == '__main__':
    print("✅ Chatbot SafeClaim pronto sulla porta 5001!")
    print(f"📊 Sessioni attive: {len(active_sessions)}")
    print(f"🤖 RAG: {'Abilitato' if vector_db else 'Non inizializzato'}")
    print(f"💾 MongoDB: {'Connesso' if mongo_client else 'Non disponibile'}")
    app.run(debug=True, port=5001)