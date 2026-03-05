import pymongo
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from bson.objectid import ObjectId

# --- INIZIALIZZAZIONE ---
# Creiamo l'oggetto Flask che gestisce il server web
app = Flask(__name__)

# Abilitiamo CORS: è fondamentale per permettere a un frontend (es. React o Vue) 
# di fare richieste a questo server se si trovano su indirizzi diversi.
CORS(app) 

# --- CONFIGURAZIONE MONGODB ATLAS ---
# Stringa di connessione: contiene le credenziali e l'indirizzo del cluster MongoDB.
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
DB_NAME = "FakeClaim"

# Proviamo a connetterci al database all'avvio del server
try:
    # Creiamo il client. 'serverSelectionTimeoutMS' evita che il server rimanga bloccato
    # se il database Atlas non risponde entro 5 secondi.
    client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    
    # Puntiamo al database specifico e alla collezione (tabella) dei sinistri
    db = client[DB_NAME]
    sinistri_col = db['sinistri']
    
    # Forza un controllo immediato della connessione per confermare che sia attiva
    client.server_info() 
    print("Connessione a MongoDB Atlas (FakeClaim) riuscita!")
except Exception as e:
    # Se la connessione fallisce (es. password errata), impostiamo la variabile a None
    # per evitare che il server crashi durante l'esecuzione.
    print(f"Errore critico di connessione al database: {e}")
    sinistri_col = None

# --- ROTTA 1: CREAZIONE DI UN NUOVO SINISTRO (POST) ---
@app.route('/sinistro', methods=['POST'])
def apri_sinistro():
    # Se la variabile della collezione è None, il database non è connesso
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    # Recuperiamo i dati inviati dal client (solitamente un JSON)
    data = request.json
    
    # Validazione: verifichiamo che i campi richiesti esistano nel JSON ricevuto
    required_fields = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Campo mancante: {field}"}), 400

    try:
        # Prepariamo il dizionario (documento) da salvare su MongoDB
        nuovo_sinistro = {
            "automobilista_id": data['automobilista_id'],
            "targa": data['targa'],
            "data_evento": data['data_evento'],
            "descrizione": data['descrizione'],
            "stato": "APERTO",            # Stato di default per le nuove pratiche
            "immagini": [],               # Prepariamo una lista vuota per le future foto
            "data_inserimento": datetime.now() # Salviamo il momento esatto del caricamento
        }

        # Eseguiamo l'inserimento nel database
        risultato = sinistri_col.insert_one(nuovo_sinistro)
        
        # Restituiamo il successo e l'ID unico generato da MongoDB (convertito in stringa)
        return jsonify({
            "status": "success",
            "message": "Sinistro salvato correttamente",
            "mongo_id": str(risultato.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ROTTA 2: AGGIUNTA IMMAGINE TRAMITE ID SPECIFICO (POST) ---
@app.route('/sinistro/<id>/immagini', methods=['POST'])
def aggiungi_immagine(id):
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    data = request.json
    # Verifichiamo che l'utente stia inviando effettivamente una stringa immagine (Base64)
    if 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        # update_one: cerca il documento con l'ID fornito nell'URL.
        # $push: operatore MongoDB che aggiunge un elemento a un array senza sovrascrivere quelli esistenti.
        risultato = sinistri_col.update_one(
            {"_id": ObjectId(id)}, 
            {"$push": {"immagini": data['immagine_base64']}}
        )

        # Se matched_count è 0, significa che non esiste alcun documento con quell'ID
        if risultato.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404

        return jsonify({"status": "success", "message": "Immagine caricata!"}), 200
    except Exception as e:
        # Se l'ID passato nell'URL non è un formato valido (es. troppo corto), restituiamo errore
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ROTTA 3: AGGIUNTA IMMAGINE ALL'ULTIMO SINISTRO CREATO (POST) ---
# Utile per testare rapidamente l'app senza dover copiare ogni volta l'ID
@app.route('/sinistro/ultimo/immagini', methods=['POST'])
def aggiungi_immagine_ultimo():
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    data = request.json
    if 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        # Cerchiamo l'ultimo documento inserito ordinando per 'data_inserimento' decrescente (-1)
        ultimo_sinistro = sinistri_col.find_one(sort=[("data_inserimento", -1)])

        if not ultimo_sinistro:
            return jsonify({"error": "Nessun sinistro trovato"}), 404

        # Aggiorniamo l'ultimo documento trovato aggiungendo l'immagine
        sinistri_col.update_one(
            {"_id": ultimo_sinistro["_id"]}, 
            {"$push": {"immagini": data['immagine_base64']}}
        )

        return jsonify({
            "status": "success", 
            "message": "Immagine caricata sull'ultimo sinistro creato!",
            "id_usato": str(ultimo_sinistro["_id"])
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ROTTA 4: RECUPERO SINISTRI (GET) ---
# Gestisce sia la lista completa (/sinistri) che il singolo elemento (/sinistri/ID)
@app.route('/sinistri', defaults={'id_sinistro': None}, methods=['GET'])
@app.route('/sinistri/<id_sinistro>', methods=['GET'])
def ottieni_sinistri(id_sinistro):
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    try: 
        # CASO 1: L'utente ha chiesto un ID specifico
        if id_sinistro:
            sinistro = sinistri_col.find_one({"_id": ObjectId(id_sinistro)})
            if not sinistro:
                return jsonify({"status": "error", "message": "Sinistro non trovato"}), 404
            
            # Trasformiamo l'ID di sistema in testo leggibile per il JSON
            sinistro['_id'] = str(sinistro['_id'])
            # Convertiamo la data di sistema in formato standard ISO (testo)
            if 'data_inserimento' in sinistro:
                sinistro['data_inserimento'] = sinistro['data_inserimento'].isoformat()
            
            return jsonify({"status": "success", "data": sinistro}), 200
        
        # CASO 2: L'utente ha chiesto tutti i sinistri
        else:
            # Recuperiamo tutti i documenti tramite find()
            cursor = sinistri_col.find() 
            lista_sinistri = []
            for s in cursor:
                # Per ogni sinistro, convertiamo ID e date in stringhe
                s['_id'] = str(s['_id'])
                if 'data_inserimento' in s:
                    s['data_inserimento'] = s['data_inserimento'].isoformat()
                lista_sinistri.append(s)
            
            return jsonify({
                "status": "success",
                "count": len(lista_sinistri), # Indica quanti elementi ci sono in totale
                "data": lista_sinistri
            }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- CONFIGURAZIONE AI ---


# URL del modello Mistral-7B, che è uno dei migliori compromessi tra velocità e intelligenza per un chatbot in italiano.
# API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"


def carica_conoscenza():
    """
    Funzione per
    Leggere il file di testo, e trasformarlo in una stringa di testo
    che verrà inviata all'IA come base di conoscenza.
    """
    try:
        # Tentativo di apertura del file 'RegoleSinistriChatBot.txt'
        with open("RegoleSinistriChatBot.txt", "r", encoding="utf-8") as f:
            return f.read() # Restituisce tutto il testo contenuto nel file
    except FileNotFoundError:
        # Se il file non esiste ancora, restituiamo un testo predefinito per non bloccare il bot
        return "Info base: Compilare il modulo CAI e scattare foto ai danni del veicolo."

# --- ROTTA PER IL CHATBOT ---
@app.route('/chat', methods=['POST'])
def chat_bot():
    """
    Endpoint che riceve il messaggio dell'automobilista e restituisce la risposta dell'IA.
    """
    # Recuperiamo il JSON inviato (es. da Postman o dall'app mobile)
    data = request.json
    messaggio_utente = data.get('messaggio')
    
    # Controllo: se l'utente non ha scritto nulla, restituiamo un errore 400
    if not messaggio_utente:
        return jsonify({"error": "Il campo 'messaggio' è obbligatorio"}), 400

    # 1. Recuperiamo le regole scritte da Mihali nel file di testo
    context = carica_conoscenza()

    # 2. COSTRUZIONE DEL PROMPT (Istruzioni per l'IA)
    # Fondiamo insieme l'identità del bot, il file con le regole e la domanda dell'utente.
    prompt = (
        f"Sei l'assistente virtuale di SafeClaim. Rispondi in italiano in modo professionale.\n"
        f"Usa esclusivamente queste informazioni per rispondere: {context}\n\n"
        f"Domanda dell'utente: {messaggio_utente}\n"
        f"Risposta dell'assistente:"
    )

    try:
        # 3. Preparazione dei parametri per Hugging Face
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 250, # Numero massimo di parole/token nella risposta
                "temperature": 0.5,     # Bilanciamento tra precisione (0.1) e creatività (0.9)
                "return_full_text": False # Indica di restituire solo la risposta, non tutto il prompt
            }
        }
        
        # Invio effettivo della richiesta tramite il modulo 'requests'
        response = requests.post(API_URL, headers=headers, json=payload)
        
        # Se lo status code non è 200, c'è un problema (es. Token errato o server AI sovraccarico)
        if response.status_code != 200:
            return jsonify({
                "error": "Errore nella comunicazione con il server AI", 
                "details": response.text
            }), response.status_code

        # Estraiamo la risposta JSON dall'IA
        output = response.json()
        
        # Puliamo il testo eliminando spazi bianchi inutili all'inizio e alla fine
        risposta_finale = output[0]['generated_text'].strip()

        # Restituiamo il successo e la risposta del bot al cliente
        return jsonify({
            "status": "success",
            "risposta": risposta_finale
        }), 200

    except Exception as e:
        # Gestione di errori generici nel codice Python
        return jsonify({"status": "error", "message": str(e)}), 500

# --- AVVIO DEL SERVER ---
if __name__ == '__main__':
    # debug=True: il server si riavvia da solo a ogni modifica e mostra errori dettagliati
    app.run(debug=True, port=5000)