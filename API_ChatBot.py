import requests  # Importa la libreria per effettuare richieste HTTP ai server esterni
from flask import Flask, request, jsonify  # Importa Flask per creare l'API web, request per gestire i dati in entrata, jsonify per restituire risposte JSON
from flask_cors import CORS  # Importa CORS per permettere richieste da domini diversi 
from pymongo import MongoClient  # Importa MongoClient per connettersi al database MongoDB
from datetime import datetime  # Importa datetime per gestire date e orari
import uuid  # Importa uuid per generare ID unici per le sessioni

import os  # Importa os per accedere alle variabili d'ambiente e al sistema operativo
# serve a Python per andare a "pescare" le informazioni
# che non sono scritte nel codice,
# ma che si trovano nascoste nel file Token.env.

# Importa la funzione per caricare i file Token.env
from dotenv import load_dotenv  # Importa load_dotenv per caricare le variabili dal file Token.env
# Il file Token.env è come un foglietto segreto dove scrivi le tue chiavi segrete

app = Flask(__name__)  # Crea un'istanza dell'applicazione Flask
CORS(app)  # Abilita CORS per l'app Flask

# CONFIGURAZIONE AI
load_dotenv("Token.env")  # Carica le variabili d'ambiente dal file Token.env
# Legge il file Token.env che hai creato e carica tutte le scritte (tipo HF_TOKEN=...) nella memoria temporanea del computer.
# Recupera il valore associato alla chiave "HF_TOKEN" definito nel file Token.env.
# La variabile 'token' ora contiene la chiave segreta da usare.
token = os.getenv("HF_TOKEN")  # Ottiene il token Hugging Face dalla variabile d'ambiente

# Verifica rapida all'avvio (senza stampare tutto il token per sicurezza)
if token:  # Se il token è stato trovato
    print(f" Token caricato correttamente: {token[:4]}***")  # Stampa i primi 4 caratteri del token per conferma
else:  # Altrimenti
    print(" ERRORE: Token non trovato nel file Token.env")  # Stampa un messaggio di errore

# URL del modello AI
# Endpoint di Hugging Face per il modello Phi-3 Mini (4K context) - utilizzato per generare risposte intelligenti
API_URL = "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct"   

# 4. Creo gli headers
# sono come le informazioni che scrivi sulla busta di una lettera raccomandata prima di spedirla
# Senza queste "etichette", il server di Hugging Face non saprebbe nemmeno chi sei o come leggere il contenuto della tua richiesta.
headers = {  # Definisce gli header per le richieste HTTP
    "Authorization": f"Bearer {token}",  # Header per l'autenticazione con il token
    # Invia il token segreto insieme alla richiesta.
    # Hugging Face deve sapere chi sta facendo la domanda. Senza questo,
    # il server risponderebbe con un errore, perché non sa se hai il permesso di usare quel modello.
    "Content-Type": "application/json",  # Specifica che il contenuto è JSON
    # Dice al server: " i dati che ti sto mandando sono in formato JSON".
    "User-Agent": "SafeClaimBot/1.0"  # Identifica l'applicazione che fa la richiesta
    # serve per far capire chi sta facendo la richiesta.
}

# CONFIGURAZIONE MONGODB
MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"  # URI di connessione a MongoDB
MONGO_DB_NAME = "safeclaim_mongo"  # Nome del database MongoDB

try:  # Prova a connettersi a MongoDB
    mongo_client = MongoClient(MONGO_URI)  # Crea il client MongoDB
    db = mongo_client[MONGO_DB_NAME]  # Seleziona il database
    conversations_collection = db["conversations"]  # Seleziona la collezione per le conversazioni
    print(" MongoDB: Connesso")  # Stampa conferma connessione
except Exception as e:  # Se c'è un errore
    print(f" MongoDB: Connessione fallita ({e})")  # Stampa l'errore
    mongo_client = None  # Imposta il client a None

# STORE IN-MEMORY PER SESSIONI
# dove il server si segna le chat aperte in questo momento.
active_sessions = {}  # Dizionario per memorizzare le sessioni attive in memoria

# questa classe contiene I msg dell'utente
class ConversationSession:  # Definisce la classe per gestire una sessione di conversazione
    def __init__(self, session_id):  # Metodo inizializzatore
        self.session_id = session_id  # ID della sessione
        self.messages = []  # Lista dei messaggi (Bot e Utente)
        self.created_at = datetime.now()  # Data di creazione
        self.feedback_data = []  # Qui salviamo le stelline/voti

    # Funzione per aggiungere un nuovo pezzetto alla chat
    def add_message(self, role, content):  # Metodo per aggiungere un messaggio
        self.messages.append({  # Aggiunge un dizionario alla lista dei messaggi
            "role": role,  # Chi parla? "user" o "assistant"
            "content": content,  # Cosa ha detto?
            "timestamp": datetime.now().isoformat()  # Timestamp in formato ISO
        })

    # Funzione per rileggere gli ultimi messaggi
    def get_context(self):  # Metodo per ottenere il contesto della conversazione
        context = ""  # Inizializza una stringa vuota
        # Prende solo gli ultimi 6 messaggi per non confondere troppo il bot
        for msg in self.messages[-6:]:  # Cicla sugli ultimi 6 messaggi
            context += f"{msg['role'].upper()}: {msg['content']}\n"  # Aggiunge il messaggio al contesto
        return context  # Restituisce il contesto

    # Serve per trasformare tutto in un formato che il database (MongoDB) capisce
    def to_dict(self):  # Metodo per convertire l'oggetto in dizionario
        return {  # Restituisce un dizionario
            "session_id": self.session_id,  # ID sessione
            "messages": self.messages,  # Lista messaggi
            "created_at": self.created_at.isoformat()  # Data creazione in ISO
        }

# Questa funzione apre il file .txt dove abbiamo scritto le regole dei sinistri.
def carica_conoscenza():  # Definisce la funzione per caricare la conoscenza dal file
    try:  # Prova ad aprire il file
        # Apre il file .txt in modalità lettura
        with open("RegoleSinistriChatBot.txt", "r", encoding="utf-8") as f:  # Apre il file con encoding UTF-8
            return f.read()  # Legge tutto testo delle regole
    except FileNotFoundError:  # Se il file non esiste
        # Se il file non esiste, restituisce un messaggio di base
        return "Info: Compilare modulo CAI."  # Restituisce un messaggio predefinito

# Decide quali tasti/domande suggerire all'utente sotto la risposta del bot
def genera_suggerimenti(conversazione):  # Definisce la funzione per generare suggerimenti
    if len(conversazione.messages) < 2:  # Se ci sono meno di 2 messaggi
        return ["Come funziona il processo di sinistro?", "Quali documenti servono?"]  # Suggerimenti iniziali
    return ["Puoi spiegare meglio?", "Quali sono i prossimi step?"]  # Suggerimenti successivi

# --- ROTTA: INIZIO CHAT ---
# Quando clicchi "Inizia", genera un codice unico per la tua stanza
@app.route('/chat/init', methods=['POST'])  # Definisce la rotta per inizializzare una chat
def init_chat():  # Funzione per inizializzare la chat
    session_id = str(uuid.uuid4())  # Crea un ID univoco per la sessione
    active_sessions[session_id] = ConversationSession(session_id)  # Crea la cartella per l'utente
    return jsonify({"status": "success", "session_id": session_id}), 200  # Restituisce JSON con successo e ID sessione

# --- ROTTA: CHAT ---
# Qui arriva il messaggio da Postman, il server lo elabora e risponde l'AI
@app.route('/chat', methods=['POST'])  # Definisce la rotta per il chat
def chat_bot():  # Funzione principale del chatbot
    # Prende i dati che arrivano dal sito e li trasforma in un formato leggibile da Python
    data = request.json  # Ottiene i dati JSON dalla richiesta
    # Estrae l'ID della sessione e il messaggio scritto dall'utente
    session_id = data.get('session_id')  # Estrae session_id dai dati
    messaggio = data.get('messaggio')  # Estrae messaggio dai dati

    # Controllo sicurezza: se mancano i dati, dà errore
    if not session_id or not messaggio:  # Se mancano session_id o messaggio
        return jsonify({"error": "Mancano i dati"}), 400  # Restituisce errore 400

    # Cerca in (active_sessions) se esiste già questa chat; se è nuova, crea una cartella da zero per l'utente
    conversazione = active_sessions.get(session_id, ConversationSession(session_id))  # Ottiene o crea la sessione
    conversazione.add_message("user", messaggio)  # Segna cosa ha scritto l'utente

    context = carica_conoscenza()  # Chiama la funzione che apre il file .txt e legge tutte le regole di SafeClaim
    # Recupera i messaggi scambiati in precedenza per permettere al bot di capire i riferimenti
    history = conversazione.get_context()  # Prende i messaggi precedenti

    # PROMPT: con le regole, la cronologia e la nuova domanda
    # Diamo all'AI tutte le istruzioni necessarie, gli diciamo quali sono le regole e cosa ha detto l'utente.
    prompt = f"<|user|>\nRegole: {context}\nChat: {history}\nDomanda: {messaggio}\n<|end|>\n<|assistant|>"  # Costruisce il prompt per l'AI

    # Configura le istruzioni per l'AI: quanti caratteri può scrivere e quanto deve essere "creativa" (temperature)
    try:
        # Prepariamo i dati per Hugging Face
        payload = { # Il pacchetto di dati che stiamo inviando a Hugging Face
            "inputs": prompt, 
            "parameters": {"max_new_tokens": 300, "temperature": 0.4},
            "options": {"wait_for_model": True} # Forza l'attesa se il modello è in standby
        }

        # Invio richiesta all'AI
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30) # Invia la richiesta POST a Hugging Face con un timeout di 30 secondi
        
        if response.status_code != 200:
            
            # Stampiamo nel TUO terminale (non lo vede l'utente) il codice errore e il testo tecnico
            # Questo ti serve per capire se il token è scaduto (401) o se hai finito i crediti (429)
            print(f"ERRORE API HF: Stato {response.status_code} - Messaggio: {response.text}")
            
            # Restituiamo una risposta JSON "pulita" a chi ha fatto la chiamata (es. Postman)
            # Usiamo il codice 503 che significa "Servizio non disponibile"
            return jsonify({
                "error": "L'IA non è disponibile al momento", 
                "dettaglio": f"Hugging Face Status {response.status_code}"
            }), 503

        # 2. Se siamo arrivati qui, lo stato è 200, ma la risposta potrebbe essere malformata
        try:
            # Proviamo a trasformare il corpo della risposta in un dizionario Python (JSON)
            output = response.json()

        # 3. Se la trasformazione fallisce (perché la risposta è vuota o non è un JSON)
        except Exception as json_err:
            
            # Stampiamo l'errore tecnico nel terminale per il debug
            print(f"ERRORE DECODIFICA JSON: {json_err}")
            
            # Restituiamo un errore 502 (Bad Gateway), dicendo che i dati ricevuti non sono validi
            return jsonify({"error": "Risposta non valida dal server AI"}), 502

        # Debug: stampa nel terminale cosa risponde l'AI (utile per capire errori 500)
        print(f" DEBUG AI RESPONSE \n{output}\n------------------------")

        # Controllo se la risposta è nel formato lista previsto
        if isinstance(output, list) and len(output) > 0:
            # Estraiamo il testo e puliamo eventuali rimasugli del prompt
            risposta_full = output[0].get('generated_text', '') 
            # Prendiamo solo la parte dopo <|assistant|> per evitare ripetizioni
            risposta_ai = risposta_full.split("<|assistant|>")[-1].strip() # Pulisce la risposta per mostrare solo il testo generato dall'AI
        else:
            # Se Hugging Face risponde con un errore (es. quota superata)
            risposta_ai = "Scusa, sto ricaricando i miei sistemi. Riprova tra un istante."

        # Salviamo la risposta nella cronologia
        conversazione.add_message("assistant", risposta_ai)

        # Rispondiamo al client
        return jsonify({
            "risposta": risposta_ai,
            "suggerimenti": genera_suggerimenti(conversazione)
        }), 200

    except Exception as e:
        # Se il server crasha, stampiamo l'errore esatto nel terminale
        print(f" ERRORE CRITICO: {str(e)}")
        return jsonify({"error": "Errore interno del server", "dettaglio": str(e)}), 500

# --- ROTTA: FINE CHAT ---
# Quando l'utente chiude, salviamo tutta la cartella su MongoDB per non perderla
@app.route('/chat/end/<session_id>', methods=['POST'])  # Definisce la rotta per terminare la chat
def end_chat(session_id):  # Funzione per terminare la chat
    if session_id in active_sessions:  # Se la sessione esiste
        conversazione = active_sessions[session_id]  # Ottiene la conversazione
        if mongo_client:  # Se MongoDB è connesso
            # Scrive tutto su MongoDB
            db["conversations"].insert_one(conversazione.to_dict())  # Inserisce nel database
        del active_sessions[session_id]  # Pulisce la memoria del server
    return jsonify({"status": "success"}), 200  # Restituisce successo

# --- AVVIO ---
if __name__ == '__main__':  # Se il file è eseguito direttamente
    print("Il server SafeClaim è acceso e pronto!")  # Messaggio di avvio
    app.run(debug=True, port=5001)  # Avvia il server Flask in debug sulla porta 5001