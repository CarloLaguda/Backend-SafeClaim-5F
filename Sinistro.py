import pymongo  # Importa la libreria per gestire il database MongoDB
import requests  # Importa la libreria per inviare messaggi via internet (all'AI)
from flask import Flask, request, jsonify  # Importa i componenti per creare il server web
from flask_cors import CORS  # Importa il modulo per evitare i blocchi di sicurezza del browser
from datetime import datetime  # Importa la gestione di date e orari
from bson.objectid import ObjectId  # Importa il traduttore per gli ID speciali di MongoDB

# --- INIZIALIZZAZIONE ---
app = Flask(__name__)  # Crea l'applicazione server SafeClaim
CORS(app)  # Permette a programmi esterni (come il frontend) di parlare con questo server

# --- CONFIGURAZIONE MONGODB ATLAS ---
# Questa è la stringa segreta per connettersi al database nel cloud
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
DB_NAME = "FakeClaim"  # Definisce il nome del database

try:
    # Prova a stabilire il contatto con il server di MongoDB Atlas
    client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    
    # Seleziona il database 'FakeClaim'
    db = client[DB_NAME]
    # Seleziona la collezione (tabella) chiamata 'sinistri'
    sinistri_col = db['sinistri']
    
    # Chiede al database se è davvero attivo (test di connessione)
    client.server_info() 
    print("Connessione a MongoDB Atlas (FakeClaim) riuscita!") # Messaggio di successo
except Exception as e:
    # Se qualcosa non va (es. internet assente), stampa l'errore e mette la collezione a None
    print(f"Errore critico di connessione al database: {e}")
    sinistri_col = None

# --- ROTTA 1: CREAZIONE DI UN NUOVO SINISTRO (POST) ---
@app.route('/sinistro', methods=['POST']) # Definisce l'indirizzo per aprire una pratica
def apri_sinistro():
    # Se il database non è connesso, restituisce errore 503 (Servizio non disponibile)
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    # Prende i dati JSON inviati dall'utente 
    data = request.json
    
    # Lista dei campi obbligatori per legge/regolamento
    required_fields = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    # Controlla uno per uno se i campi richiesti ci sono
    for field in required_fields:
        if field not in data:
            # Se manca un campo, risponde con errore 400 (Richiesta sbagliata)
            return jsonify({"error": f"Campo mancante: {field}"}), 400

    try:
        # Prepara lo schema del documento da salvare nel database
        nuovo_sinistro = {
            "automobilista_id": data['automobilista_id'], # ID del guidatore
            "targa": data['targa'], # Targa dell'auto
            "data_evento": data['data_evento'], # Data dell'incidente
            "descrizione": data['descrizione'], # Cosa è successo
            "stato": "APERTO", # Imposta lo stato iniziale della pratica
            "immagini": [], # Crea uno spazio vuoto per le foto future
            "data_inserimento": datetime.now() # Segna il momento esatto della registrazione
        }

        # Inserisce fisicamente il documento nella collezione 'sinistri'
        risultato = sinistri_col.insert_one(nuovo_sinistro)
        
        # Risponde all'utente confermando il salvataggio e inviando l'ID unico creato
        return jsonify({
            "status": "success",
            "message": "Sinistro salvato correttamente",
            "mongo_id": str(risultato.inserted_id) # Converte l'ID di MongoDB in testo
        }), 201
    except Exception as e:
        # Se c'è un errore imprevisto, restituisce errore 500
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ROTTA 2: AGGIUNTA IMMAGINE TRAMITE ID SPECIFICO (POST) ---
@app.route('/sinistro/<id>/immagini', methods=['POST']) # Indirizzo che contiene l'ID della pratica
def aggiungi_immagine(id):
    # Controllo se il database è acceso
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    # Legge l'immagine inviata nel corpo della richiesta
    data = request.json
    # Verifica che ci sia il campo con la stringa dell'immagine
    if 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        # Cerca il sinistro col suo ID e aggiunge l'immagine alla lista 'immagini'
        risultato = sinistri_col.update_one(
            {"_id": ObjectId(id)}, # Converte il testo dell'ID in formato MongoDB
            {"$push": {"immagini": data['immagine_base64']}} # Aggiunge alla lista senza sovrascrivere
        )

        # Se matched_count è 0, significa che quell'ID non esiste nel database
        if risultato.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404

        # Conferma il caricamento della foto
        return jsonify({"status": "success", "message": "Immagine caricata!"}), 200
    except Exception as e:
        # Gestisce errori di ID scritti male o problemi del server
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ROTTA 3: RECUPERO SINISTRI (GET) ---
@app.route('/sinistri', defaults={'id_sinistro': None}, methods=['GET']) # Indirizzo per tutti i sinistri
@app.route('/sinistri/<id_sinistro>', methods=['GET']) # Indirizzo per un sinistro singolo
def ottieni_sinistri(id_sinistro):
    # Controllo connessione database
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    try: 
        # SE l'utente ha chiesto un ID specifico
        if id_sinistro:
            # Cerca nel DB solo quel sinistro
            sinistro = sinistri_col.find_one({"_id": ObjectId(id_sinistro)})
            # Se non lo trova, risponde 404
            if not sinistro:
                return jsonify({"status": "error", "message": "Sinistro non trovato"}), 404
            
            # Converte l'ID in testo per il JSON
            sinistro['_id'] = str(sinistro['_id'])
            # Converte la data in formato leggibile ISO
            if 'data_inserimento' in sinistro:
                sinistro['data_inserimento'] = sinistro['data_inserimento'].isoformat()
            
            # Invia i dati del sinistro trovato
            return jsonify({"status": "success", "data": sinistro}), 200
        
        # SE l'utente non ha messo ID, vuole tutta la lista
        else:
            # Prende tutti i documenti nella collezione
            cursor = sinistri_col.find() 
            lista_sinistri = [] # Crea una lista vuota dove metterli
            for s in cursor:
                # Per ogni elemento, converte ID e Data
                s['_id'] = str(s['_id'])
                if 'data_inserimento' in s:
                    s['data_inserimento'] = s['data_inserimento'].isoformat()
                # Aggiunge il sinistro sistemato alla lista finale
                lista_sinistri.append(s)
            
            # Invia tutta la lista dei sinistri
            return jsonify({
                "status": "success",
                "count": len(lista_sinistri), # Dice quanti ne ha trovati
                "data": lista_sinistri
            }), 200
    except Exception as e:
        # Invia l'errore se qualcosa fallisce nel recupero dati
        return jsonify({"status": "error", "message": str(e)}), 500


# --- AVVIO DEL SERVER ---
if __name__ == '__main__':
    # Avvia Flask sulla porta 5000 in modalità debug (si riavvia se modifichi il file)
    app.run(debug=True, port=5000)