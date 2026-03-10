import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import uuid

import os #serve a Python per andare a "pescare" le informazioni 
          #che non sono scritte nel codice, 
          #ma che si trovano nascoste nel file Token.env.

#Importa la funzione per caricare i file Token.env
from dotenv import load_dotenv #Il file Token.env è come un foglietto segreto dove scrivi le tue chiavi segrete



app = Flask(__name__)
CORS(app)


# CONFIGURAZIONE AI
load_dotenv("Token.env") #Legge il file .env che hai creato e carica tutte le scritte (tipo HF_TOKEN=...) nella memoria temporanea del computer.
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
    "Content-Type": "application/json", # Dice al server: " i dati che ti sto mandando sono in formato JSON".
    "User-Agent": "SafeClaimBot/1.0" # serve per far capire chi sta facendo la richiesta.
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
# dove il server si segna le chat aperte in questo momento.
active_sessions = {}

# questa classe contiene I msg dell'utente
    def __init__(self, session_id):
        self.session_id = session_id
        self.messages = []  # Lista dei messaggi (Bot e Utente)
        self.created_at = datetime.now()
        self.feedback_data = [] # Qui salviamo le stelline/voti
        
    # Funzione per aggiungere un nuovo pezzetto alla chat
    def add_message(self, role, content):
        self.messages.append({
            "role": role, # Chi parla? "user" o "assistant"
            "content": content, # Cosa ha detto?
            "timestamp": datetime.now().isoformat()
        })
        
    # Funzione per rileggere gli ultimi messaggi 
    def get_context(self):
        context = ""
        # Prende solo gli ultimi 6 messaggi per non confondere troppo il bot
        for msg in self.messages[-6:]:
            context += f"{msg['role'].upper()}: {msg['content']}\n"
        return context
    
    # Serve per trasformare tutto in un formato che il database (MongoDB) capisce
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "created_at": self.created_at.isoformat()
        }


# Questa funzione apre il file .txt dove abbiamo scritto le regole dei sinistri.
def carica_conoscenza():
    try:
        # Apre il file .txt in modalità lettura
        with open("RegoleSinistriChatBot.txt", "r", encoding="utf-8") as f:
            return f.read() # Legge tutto testo delle regole
    except FileNotFoundError:
        # Se il file non esiste, restituisce un messaggio di base
        return "Info: Compilare modulo CAI." 


# Decide quali tasti/domande suggerire all'utente sotto la risposta del bot
def genera_suggerimenti(conversazione):
    if len(conversazione.messages) < 2:
        return ["Come funziona il processo di sinistro?", "Quali documenti servono?"]
    return ["Puoi spiegare meglio?", "Quali sono i prossimi step?"]

# --- ROTTA: INIZIO CHAT ---
# Quando clicchi "Inizia", genera un codice unico per la tua stanza
@app.route('/chat/init', methods=['POST'])
def init_chat():
    session_id = str(uuid.uuid4()) # Crea un ID 
    active_sessions[session_id] = ConversationSession(session_id) # Crea la cartella per l'utente
    return jsonify({"status": "success", "session_id": session_id}), 200

# --- ROTTA: CHAT ---
# Qui arriva il messaggio da Postman, il server lo elabora e risponde l'AI
@app.route('/chat', methods=['POST'])
def chat_bot():
    # Prende i dati che arrivano dal sito e li trasforma in un formato leggibile da Python
    data = request.json
    # Estrae l'ID della sessione e il messaggio scritto dall'utente
    session_id = data.get('session_id')
    messaggio = data.get('messaggio')
    
    # Controllo sicurezza: se mancano i dati, dà errore
    if not session_id or not messaggio:
        return jsonify({"error": "Mancano i dati"}), 400
    
    # Cerca in (active_sessions) se esiste già questa chat; se è nuova, crea una cartella da zero per l'utente
    conversazione = active_sessions.get(session_id, ConversationSession(session_id))
    conversazione.add_message("user", messaggio) # Segna cosa ha scritto l'utente
    
    context = carica_conoscenza() # Chiama la funzione che apre il file .txt e legge tutte le regole di SafeClaim
    # Recupera i messaggi scambiati in precedenza per permettere al bot di capire i riferimenti
    history = conversazione.get_context() # Prende i messaggi precedenti
    
    # PROMPT: con le regole, la cronologia e la nuova domanda
    # Diamo all'AI tutte le istruzioni necessarie, gli diciamo  quali sono le regole e cosa ha detto l'utente.
    prompt = f"<|user|>\nRegole: {context}\nChat: {history}\nDomanda: {messaggio}\n<|end|>\n<|assistant|>"
    
    # Configura le istruzioni per l'AI: quanti caratteri può scrivere e quanto deve essere "creativa" (temperature)
    try:
        # Pacchetto da spedire a Hugging Face
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 300, "temperature": 0.4}
        }
        
        # Spedisce il tutto a Hugging Face usando il Token segreto e aspetta la risposta (massimo 30 secondi)
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        # Converte la risposta che arriva dal server AI in un formato che Python può usare
        output = response.json()
        # Estrae solo il testo generato dal bot, eliminando eventuali spazi vuoti inutili all'inizio o alla fine
        risposta_ai = output[0]['generated_text'].strip()
        
        # Salva la risposta appena data dal bot nella cronologia, così alla prossima domanda il bot saprà cosa ha detto
        conversazione.add_message("assistant", risposta_ai)
        
        # Invia la risposta finale all'utente insieme ai suggerimenti per continuare la conversazione
        return jsonify({
            "risposta": risposta_ai,
            "suggerimenti": genera_suggerimenti(conversazione)
        }), 200
    # Se qualcosa va storto, mostra l'errore e lo mostra senza far crashare il server
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ROTTA: FINE CHAT ---
# Quando l'utente chiude, salviamo tutta la cartella su MongoDB per non perderla
@app.route('/chat/end/<session_id>', methods=['POST'])
def end_chat(session_id):
    if session_id in active_sessions:
        conversazione = active_sessions[session_id]
        if mongo_client:
            # Scrive tutto su MongoDB
            db["conversations"].insert_one(conversazione.to_dict())
        del active_sessions[session_id] # Pulisce la memoria del server
    return jsonify({"status": "success"}), 200

# --- AVVIO ---
if __name__ == '__main__':
    print("Il server SafeClaim è acceso e pronto!")
    app.run(debug=True, port=5001)
