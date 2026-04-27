import os
import uuid
import requests
import pymongo
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv

# --- IMPORT PER IL RAG (Gestione Documenti) ---
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

app = Flask(__name__)
CORS(app)

# --- 1. CONFIGURAZIONE AI & TOKEN ---
load_dotenv("Token.env")
token = os.getenv("HF_TOKEN")

# Usiamo Phi-3: molto più performante per seguire le regole del tuo file TXT
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-v0.1"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "SafeClaimBot/1.0"
}

# --- 2. CONFIGURAZIONE MONGODB ATLAS ---
# Utilizziamo la tua stringa di connessione Atlas che funziona correttamente
MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
MONGO_DB_NAME = "FakeClaim"

try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client[MONGO_DB_NAME]
    conversations_collection = db["conversations"]
    mongo_client.server_info()
    print("✅ MongoDB Atlas: Connesso correttamente")
except Exception as e:
    print(f"⚠️ MongoDB Atlas: Connessione fallita ({e})")
    mongo_client = None

# --- 3. INIZIALIZZAZIONE RAG (Caricamento RegoleSinistriChatBot.txt) ---
embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_db = None

def inizializza_rag():
    global vector_db
    try:
        if os.path.exists("RegoleSinistriChatBot.txt"):
            with open("RegoleSinistriChatBot.txt", "r", encoding="utf-8") as f:
                documento = f.read()
            
            text_splitter = CharacterTextSplitter(chunk_size=400, chunk_overlap=50, separator="\n")
            chunks = text_splitter.split_text(documento)
            vector_db = FAISS.from_texts(chunks, embeddings_model)
            print(f"✅ RAG: Conoscenza caricata dal file ({len(chunks)} frammenti)")
        else:
            print("⚠️ RAG: File RegoleSinistriChatBot.txt non trovato!")
    except Exception as e:
        print(f"⚠️ RAG: Errore durante l'inizializzazione ({e})")

inizializza_rag()

# --- 4. GESTIONE SESSIONI ---
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

# --- 5. FUNZIONI DI SUPPORTO ---
def recupera_conoscenza_rag(domanda):
    if vector_db is None:
        return "Info base: Seguire la procedura CAI standard."
    documenti_trovati = vector_db.similarity_search(domanda, k=3)
    return "\n".join([d.page_content for d in documenti_trovati])

def genera_suggerimenti(conversazione):
    if len(conversazione.messages) < 2:
        return ["Come funziona il processo di sinistro?", "Quali documenti servono?"]
    return ["E se l'altro non firma?", "Quali sono i prossimi step?"]

# --- 6. ROTTE API ---

@app.route('/chat/init', methods=['POST'])
def chat_init():
    """Inizializza una nuova sessione di chat"""
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = ConversationSession(session_id)
    return jsonify({"status": "success", "session_id": session_id}), 200

@app.route('/chat', methods=['POST'])
def chat_bot():
    """Riceve il messaggio, consulta il RAG e risponde tramite AI"""
    data = request.json
    session_id = data.get('session_id')
    messaggio = data.get('messaggio')

    if not session_id or not messaggio:
        return jsonify({"error": "Dati mancanti"}), 400

    if session_id not in active_sessions:
        active_sessions[session_id] = ConversationSession(session_id)
    
    conversazione = active_sessions[session_id]
    conversazione.add_message("user", messaggio)

    context_rag = recupera_conoscenza_rag(messaggio)
    context_history = conversazione.get_context()

    prompt = f"<|user|>\nSei l'assistente SafeClaim. Usa queste regole: {context_rag}\nStoria: {context_history}\nDomanda: {messaggio}\n<|end|>\n<|assistant|>"

    try:
        payload = {
            "inputs": prompt, 
            "parameters": {"max_new_tokens": 300, "temperature": 0.4},
            "options": {"wait_for_model": True}
        }
        res = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if res.status_code == 200:
            output = res.json()
            risposta_full = output[0].get('generated_text', '')
            risposta_ai = risposta_full.split("<|assistant|>")[-1].strip()
        else:
            risposta_ai = "Sistemi momentaneamente occupati. Riprova tra poco."

        conversazione.add_message("assistant", risposta_ai)
        return jsonify({
            "risposta": risposta_ai,
            "session_id": session_id,
            "suggerimenti": genera_suggerimenti(conversazione)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat/end', methods=['POST'])
def chat_end():
    """Chiude la sessione e salva su MongoDB"""
    data = request.json
    session_id = data.get('session_id')
    
    if session_id in active_sessions:
        conversazione = active_sessions[session_id]
        if mongo_client:
            db[MONGO_DB_NAME]["conversations"].insert_one({
                "session_id": session_id,
                "messages": conversazione.messages,
                "feedback": conversazione.feedback_data,
                "timestamp": datetime.now()
            })
        del active_sessions[session_id]
        return jsonify({"status": "success", "message": "Sessione salvata e chiusa"}), 200
    return jsonify({"error": "Sessione non trovata"}), 404

if __name__ == '__main__':
    print("🚀 Chatbot SafeClaim pronto sulla porta 5001!")
    app.run(debug=True, port=5001)