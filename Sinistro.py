import pymongo
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from bson.objectid import ObjectId

# Inizializziamo l'applicazione Flask
app = Flask(__name__)

# Abilitiamo CORS: permette al frontend (es. un'app React o un sito web) 
# di comunicare con questo server anche se sono su domini diversi.
CORS(app) 

# --- CONFIGURAZIONE MONGODB ATLAS ---
# Stringa di connessione che contiene utente, password e indirizzo del cluster
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
DB_NAME = "FakeClaim"

# Proviamo a stabilire la connessione all'avvio del server
try:
    # Creiamo il client MongoDB. 'serverSelectionTimeoutMS' evita che il server 
    # resti bloccato all'infinito se il database non risponde.
    client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    
    # Selezioniamo il database e la collezione specifica per i sinistri
    db = client[DB_NAME]
    sinistri_col = db['sinistri']
    
    # Forza una chiamata al server per verificare se siamo davvero connessi
    client.server_info() 
    print("✅ Connessione a MongoDB Atlas (FakeClaim) riuscita!")
except Exception as e:
    # Se la connessione fallisce, stampiamo l'errore e impostiamo la variabile a None
    print(f"❌ Errore critico di connessione al database: {e}")
    sinistri_col = None

# --- ROTTA 1: CREAZIONE DI UN NUOVO SINISTRO ---
@app.route('/sinistro', methods=['POST'])
def apri_sinistro():
    # Controllo di sicurezza: se il DB non è connesso, restituiamo errore 503
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    # Estraiamo i dati JSON inviati nel corpo della richiesta
    data = request.json
    
    # Definiamo i campi che l'utente DEVE obbligatoriamente inviare
    required_fields = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Campo mancante: {field}"}), 400

    try:
        # Prepariamo l'oggetto (documento) da salvare su MongoDB
        nuovo_sinistro = {
            "automobilista_id": data['automobilista_id'],
            "targa": data['targa'],
            "data_evento": data['data_evento'],
            "descrizione": data['descrizione'],
            "stato": "APERTO", # Stato iniziale predefinito
            "immagini": [],    # Lista vuota che verrà popolata in seguito
            "data_inserimento": datetime.now() # Data e ora del server
        }

        # Eseguiamo l'inserimento effettivo nella collezione
        risultato = sinistri_col.insert_one(nuovo_sinistro)
        
        # Restituiamo il successo e l'ID generato automaticamente da MongoDB
        return jsonify({
            "status": "success",
            "message": "Sinistro salvato correttamente",
            "mongo_id": str(risultato.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ROTTA 2: AGGIUNTA IMMAGINE TRAMITE ID ---
@app.route('/sinistro/<id>/immagini', methods=['POST'])
def aggiungi_immagine(id):
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    data = request.json
    if 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        # update_one cerca il documento con l'ID specificato.
        # $push aggiunge il nuovo valore alla lista 'immagini' senza cancellare quelle vecchie.
        risultato = sinistri_col.update_one(
            {"_id": ObjectId(id)}, 
            {"$push": {"immagini": data['immagine_base64']}}
        )

        # Se matched_count è 0, significa che l'ID fornito non esiste nel DB
        if risultato.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404

        return jsonify({"status": "success", "message": "Immagine caricata!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ROTTA 3: AGGIUNTA IMMAGINE ALL'ULTIMO SINISTRO (UTILE PER TEST) ---
@app.route('/sinistro/ultimo/immagini', methods=['POST'])
def aggiungi_immagine_ultimo():
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    data = request.json
    if 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        # Cerchiamo il sinistro più recente ordinando per 'data_inserimento' decrescente (-1)
        ultimo_sinistro = sinistri_col.find_one(sort=[("data_inserimento", -1)])

        if not ultimo_sinistro:
            return jsonify({"error": "Nessun sinistro trovato"}), 404

        # Aggiorniamo quel documento specifico
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

# --- ROTTA 4: RECUPERO SINISTRI (TUTTI O SINGOLO) ---
@app.route('/sinistri', defaults={'id_sinistro': None}, methods=['GET'])
@app.route('/sinistri/<id_sinistro>', methods=['GET'])
def ottieni_sinistri(id_sinistro):
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    try: 
        # SE viene fornito un ID nell'URL, cerchiamo solo quel sinistro
        if id_sinistro:
            sinistro = sinistri_col.find_one({"_id": ObjectId(id_sinistro)})
            if not sinistro:
                return jsonify({"status": "error", "message": "Sinistro non trovato"}), 404
            
            # Convertiamo l'ObjectId e la Data in formati leggibili dal JSON (stringhe)
            sinistro['_id'] = str(sinistro['_id'])
            if 'data_inserimento' in sinistro:
                sinistro['data_inserimento'] = sinistro['data_inserimento'].isoformat()
            
            return jsonify({"status": "success", "data": sinistro}), 200
        
        # ALTRIMENTI recuperiamo l'intera lista
        else:
            cursor = sinistri_col.find() # Restituisce un cursore a tutti i documenti
            lista_sinistri = []
            for s in cursor:
                s['_id'] = str(s['_id'])
                if 'data_inserimento' in s:
                    s['data_inserimento'] = s['data_inserimento'].isoformat()
                lista_sinistri.append(s)
            
            return jsonify({
                "status": "success",
                "count": len(lista_sinistri),
                "data": lista_sinistri
            }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Avvio del server Flask
if __name__ == '__main__':
    # debug=True permette di vedere gli errori dettagliati nel terminale durante lo sviluppo
    app.run(debug=True, port=5000)