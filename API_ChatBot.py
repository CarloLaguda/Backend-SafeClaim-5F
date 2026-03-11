import requests  # Importa la libreria per fare richieste HTTP (usata per chiamare l'API AI di Hugging Face)
from flask import Flask, request, jsonify  # Importa Flask per creare l'API web, gestire richieste e risposte JSON
from flask_cors import CORS  # Abilita CORS per permettere richieste da frontend diversi (evita errori cross-origin)
from pymongo import MongoClient  # Connette a MongoDB per salvare conversazioni persistenti
from datetime import datetime  # Gestisce timestamp per messaggi e sessioni
import uuid  # Genera ID unici per le sessioni di chat

app = Flask(__name__)  # Crea l'app Flask principale
CORS(app)  # Abilita CORS per tutte le route dell'app

# CONFIGURAZIONE AI
API_URL = "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct"  # URL dell'API AI per generare risposte (modello Phi-3)

headers = {  # Intestazioni HTTP per le richieste all'API AI (specificano tipo contenuto e user-agent)
    "Content-Type": "application/json",
    "User-Agent": "SafeClaimBot/1.0"
}

# CONFIGURAZIONE MONGODB
MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"  # Stringa di connessione a MongoDB (include credenziali codificate)
MONGO_DB_NAME = "safeclaim_mongo"  # Nome del database MongoDB

try:  # Blocco try-except per gestire errori di connessione
    mongo_client = MongoClient(MONGO_URI)  # Crea client MongoDB
    db = mongo_client[MONGO_DB_NAME]  # Seleziona il database
    conversations_collection = db["conversations"]  # Seleziona la collezione per salvare conversazioni (dati vanno qui se la connessione riesce)
    print("✅ MongoDB: Connesso")  # Messaggio di successo (stampa su console)
except Exception as e:  # Cattura errori (es. connessione fallita)
    print(f"⚠️ MongoDB: Connessione fallita ({e})")  # Messaggio di errore (stampa su console)
    mongo_client = None  # Imposta client a None per disabilitare salvataggi MongoDB

# STORE IN-MEMORY PER SESSIONI
active_sessions = {}  # Dizionario in memoria per memorizzare sessioni attive (chiave: session_id, valore: oggetto ConversationSession; dati rimangono in RAM fino alla fine della sessione)

class ConversationSession:  # Classe per gestire una sessione di conversazione
    def __init__(self, session_id):  # Costruttore: inizializza la sessione con ID unico
        self.session_id = session_id  # ID della sessione (stringa UUID)
        self.messages = []  # Lista di messaggi (user/assistant) con timestamp
        self.created_at = datetime.now()  # Timestamp di creazione della sessione
        self.feedback_data = []  # Lista di feedback dell'utente
        
    def add_message(self, role, content):  # Metodo: aggiunge un messaggio alla conversazione
        self.messages.append({  # Aggiunge dizionario alla lista messages (dati vanno in self.messages, in memoria)
            "role": role,  # Ruolo: "user" o "assistant"
            "content": content,  # Contenuto del messaggio
            "timestamp": datetime.now().isoformat()  # Timestamp ISO
        })
        
    def get_context(self):  # Metodo: ottiene contesto recente (ultimi 6 messaggi) per il prompt AI
        context = ""  # Stringa vuota per costruire il contesto
        for msg in self.messages[-6:]:  # Cicla sugli ultimi 6 messaggi
            context += f"{msg['role'].upper()}: {msg['content']}\n"  # Aggiunge ruolo e contenuto (dati vanno nella stringa context, usata nel prompt AI)
        return context  # Restituisce la stringa contesto
    
    def add_feedback(self, rating, comment=""):  # Metodo: aggiunge feedback alla sessione
        self.feedback_data.append({  # Aggiunge dizionario alla lista feedback_data (dati vanno in self.feedback_data, in memoria)
            "rating": rating,  # Valutazione numerica
            "comment": comment,  # Commento opzionale
            "timestamp": datetime.now().isoformat()  # Timestamp
        })
    
    def to_dict(self):  # Metodo: converte la sessione in dizionario per salvataggio
        return {  # Restituisce dizionario con tutti i dati della sessione (usato per salvare in MongoDB)
            "session_id": self.session_id,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "feedback": self.feedback_data
        }

def carica_conoscenza():  # Funzione: carica regole da file per il contesto AI
    try:  # Prova ad aprire il file
        with open("RegoleSinistriChatBot.txt", "r", encoding="utf-8") as f:  # Apre file di testo
            return f.read()  # Restituisce contenuto del file (dati vanno nella stringa context del prompt AI)
    except FileNotFoundError:  # Se file non trovato
        return "Info: Compilare modulo CAI."  # Restituisce messaggio di fallback (dati vanno nel prompt AI)

def genera_suggerimenti(conversazione):  # Funzione: genera suggerimenti basati sulla conversazione
    if len(conversazione.messages) < 2:  # Se meno di 2 messaggi
        return [  # Restituisce lista di suggerimenti iniziali (dati vanno nella risposta JSON)
            "Come funziona il processo di sinistro?",
            "Quali documenti mi servono?",
            "Quanto tempo ci vuole?"
        ]
    return [  # Altrimenti, suggerimenti avanzati (dati vanno nella risposta JSON)
        "Puoi spiegare meglio?",
        "Quali sono i prossimi step?",
        "Come contatto l'assistenza?"
    ]

@app.route('/chat/init', methods=['POST'])  # Route Flask: inizializza una nuova sessione di chat
def init_chat():  # Funzione handler per POST /chat/init
    session_id = str(uuid.uuid4())  # Genera ID unico per la sessione
    active_sessions[session_id] = ConversationSession(session_id)  # Crea e salva sessione in memoria (dati vanno in active_sessions)
    return jsonify({  # Restituisce risposta JSON (dati vanno al client/frontend)
        "status": "success",
        "session_id": session_id
    }), 200  # Codice HTTP 200 (OK)

@app.route('/chat', methods=['POST'])  # Route Flask: gestisce messaggi di chat
def chat_bot():  # Funzione handler per POST /chat
    data = request.json  # Ottiene dati JSON dalla richiesta (da client/frontend)
    session_id = data.get('session_id')  # Estrae session_id
    messaggio = data.get('messaggio')  # Estrae messaggio utente
    
    if not session_id or not messaggio:  # Se mancano dati obbligatori
        return jsonify({"error": "Mancano session_id o messaggio"}), 400  # Errore 400 (dati vanno al client)
    
    if session_id not in active_sessions:  # Se sessione non esiste
        active_sessions[session_id] = ConversationSession(session_id)  # Crea nuova sessione (dati in active_sessions)
    
    conversazione = active_sessions[session_id]  # Ottiene oggetto sessione
    conversazione.add_message("user", messaggio)  # Aggiunge messaggio utente (dati in conversazione.messages)
    
    context = carica_conoscenza()  # Carica regole da file (dati nel prompt AI)
    context_history = conversazione.get_context()  # Ottiene contesto messaggi (dati nel prompt AI)
    
    prompt = f"""<|user|>  # Costruisce prompt per AI (include regole, storia e messaggio; dati vanno all'API Hugging Face)
Sei l'assistente SafeClaim. Aiuta l'utente durante la sua esperienza.

INFO REGOLE: {context}

{context_history}

Domanda attuale: {messaggio}

Fornisci una risposta chiara, concisa e utile. Sii empatico e disponibile.
<|end|>
<|assistant|>"""
    
    try:  # Blocco try-except per chiamata API
        payload = {  # Payload JSON per richiesta API AI
            "inputs": prompt,  # Prompt costruito
            "parameters": {"max_new_tokens": 300, "temperature": 0.4, "return_full_text": False},  # Parametri AI
            "options": {"wait_for_model": True}  # Opzioni attesa modello
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)  # Chiama API AI (dati vanno a Hugging Face, risposta torna qui)
        
        if response.status_code != 200:  # Se errore API
            return jsonify({  # Restituisce errore JSON (dati al client)
                "error": "Errore server AI",
                "status_code": response.status_code
            }), response.status_code
        
        output = response.json()  # Parsa risposta JSON da API
        risposta_ai = output[0]['generated_text'].strip()  # Estrae testo generato
        
        conversazione.add_message("assistant", risposta_ai)  # Aggiunge risposta AI (dati in conversazione.messages)
        suggerimenti = genera_suggerimenti(conversazione)  # Genera suggerimenti (dati nella risposta)
        
        return jsonify({  # Restituisce risposta JSON con dati della chat (dati al client)
            "status": "success",
            "session_id": session_id,
            "risposta": risposta_ai,
            "suggerimenti": suggerimenti,
            "numero_messaggi": len(conversazione.messages)
        }), 200
    
    except Exception as e:  # Cattura errori generici
        return jsonify({"status": "error", "message": str(e)}), 500  # Errore 500 (dati al client)

@app.route('/chat/feedback', methods=['POST'])  # Route Flask: riceve feedback sulla chat
def submit_feedback():  # Funzione handler per POST /chat/feedback
    data = request.json  # Ottiene dati JSON (da client)
    session_id = data.get('session_id')  # Estrae session_id
    rating = data.get('rating', 0)  # Estrae rating (default 0)
    comment = data.get('comment', '')  # Estrae commento (default vuoto)
    
    if not session_id or session_id not in active_sessions:  # Se sessione non valida
        return jsonify({"error": "Sessione non trovata"}), 404  # Errore 404 (dati al client)
    
    conversazione = active_sessions[session_id]  # Ottiene sessione
    conversazione.add_feedback(rating, comment)  # Aggiunge feedback (dati in conversazione.feedback_data)
    
    if mongo_client:  # Se MongoDB connesso
        try:  # Prova a salvare
            conversations_collection.insert_one(conversazione.to_dict())  # Salva conversazione in MongoDB (dati vanno nella collezione "conversations")
        except Exception as e:  # Errore salvataggio
            print(f"⚠️ Errore MongoDB: {e}")  # Stampa errore (su console)
    
    return jsonify({"status": "success"}), 200  # Successo (dati al client)

@app.route('/chat/history/<session_id>', methods=['GET'])  # Route Flask: ottiene storia messaggi di una sessione
def get_history(session_id):  # Funzione handler per GET /chat/history/<session_id>
    if session_id not in active_sessions:  # Se sessione non esiste
        return jsonify({"error": "Sessione non trovata"}), 404  # Errore 404 (dati al client)
    
    conversazione = active_sessions[session_id]  # Ottiene sessione
    return jsonify({  # Restituisce storia messaggi JSON (dati al client, da conversazione.messages)
        "status": "success",
        "messages": conversazione.messages
    }), 200

@app.route('/chat/end/<session_id>', methods=['POST'])  # Route Flask: termina sessione e salva
def end_chat(session_id):  # Funzione handler per POST /chat/end/<session_id>
    if session_id not in active_sessions:  # Se sessione non esiste
        return jsonify({"error": "Sessione non trovata"}), 404  # Errore 404 (dati al client)
    
    conversazione = active_sessions[session_id]  # Ottiene sessione
    
    if mongo_client:  # Se MongoDB connesso
        try:  # Prova a salvare
            conversations_collection.insert_one(conversazione.to_dict())  # Salva conversazione in MongoDB (dati vanno nella collezione "conversations")
        except Exception as e:  # Errore salvataggio
            print(f"⚠️ Errore MongoDB: {e}")  # Stampa errore (su console)
    
    del active_sessions[session_id]  # Rimuove sessione da memoria (dati eliminati da active_sessions)
    return jsonify({"status": "success"}), 200  # Successo (dati al client)

if __name__ == '__main__':  # Se script eseguito direttamente
    print("Chatbot SafeClaim pronto sulla porta 5001!")  # Messaggio di avvio (stampa su console)
    app.run(debug=True, port=5001)  # Avvia server Flask su porta 5001 (app ascolta richieste HTTP)

