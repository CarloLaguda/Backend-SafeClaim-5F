# Import delle librerie necessarie per costruire l'API REST
from flask import Flask, request, jsonify               # Flask gestisce le richieste HTTP
import pymongo                                          # Driver per comunicare con MongoDB
from datetime import datetime                          # Servirà per registrare timestamp
from bson import ObjectId                               # Per convertire stringhe in ObjectId

# Creiamo l'istanza dell'applicazione Flask
app = Flask(__name__)

# --- CONFIGURAZIONE DATABASE ---

# Stringa di connessione fornita da MongoDB Atlas; contiene credenziali e cluster da utilizzare
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
# Nome del database che useremo per archiviare i sinistri
DB_NAME = "FakeClaim"

# Proviamo a stabilire la connessione con MongoDB all'avvio dell'app
try:
    mongo_client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client[DB_NAME]                      # Selezioniamo il database
    # Eseguiamo un comando ping per confermare che il server è raggiungibile
    mongo_client.admin.command('ping')
    print("Connessione a MongoDB Atlas riuscita!")
except Exception as e:
    # In caso di errore durante la connessione, lo stampiamo sulla console
    print(f"Errore critico di connessione a MongoDB: {e}")

# --- ENDPOINTS ---

### 1. POST /soccorso --> Creazione di una nuova richiesta di soccorso
@app.route('/soccorso', methods=['POST'])                # Definiamo la rotta e il verbo HTTP
def crea_richiesta_soccorso():                            # Funzione chiamata quando arriva una POST
    try:
        data = request.json                              # Flask converte automaticamente il corpo JSON
        if not data:                                     # Controllo che il corpo non sia vuoto
            return jsonify({"error": "Corpo della richiesta mancante"}), 400

        # Estraiamo i campi attesi dal payload
        targa_veicolo = data.get('targa')
        descrizione_guasto = data.get('descrizione', "Richiesta soccorso stradale")
        lat = data.get('lat')                           # Latitudine inviata dal client
        lon = data.get('lon')                           # Longitudine inviata dal client

        # Verifichiamo i campi obbligatori
        if not targa_veicolo:
            return jsonify({"error": "La targa del veicolo è obbligatoria"}), 400

        # Costruiamo il documento da inserire in MongoDB
        # Qui non facciamo alcuna validazione esterna (es. MySQL), inseriamo direttamente
        nuovo_soccorso_mongo = {
            "targa": targa_veicolo,
            "posizione": {"lat": lat, "lon": lon},
            "stato": "Richiesto",                   # Stato iniziale dell'intervento
            "dettagli": descrizione_guasto,
            "data_richiesta": datetime.utcnow()      # Timestamp UTC al momento della richiesta
        }
        
        # Inseriamo il documento nella collezione 'Sinistro' del database selezionato
        result_mongo = mongo_db.Sinistro.insert_one(nuovo_soccorso_mongo)
        mongo_id = str(result_mongo.inserted_id)      # Convertiamo l'ObjectId in stringa
        
        # Restituiamo una risposta JSON con informazioni utili
        return jsonify({
            "message": "Soccorso registrato con successo",
            "intervento_id": mongo_id,
            "database_utilizzato": DB_NAME,
            "stato": "Richiesto"
        }), 201                                      # HTTP 201 Created

    except pymongo.errors.PyMongoError as e:            # Gestione degli errori specifici di MongoDB
        return jsonify({"error": f"Errore Database MongoDB: {str(e)}"}), 500
    except Exception as e:                               # Gestione di eventuali altri errori
        return jsonify({"error": f"Errore generico: {str(e)}"}), 500


### 2. GET /soccorso/<identificatore> --> Recupero dettagli di un soccorso
@app.route('/soccorso/<string:identificatore>', methods=['GET'])  # Parametro dinamico nella rotta
def get_dettaglio_soccorso(identificatore):                       # Flask passa il valore a questa funzione
    try:
        # Determiniamo se l'identificatore è un ObjectId valido oppure una targa
        if ObjectId.is_valid(identificatore):                     # Controllo formato ObjectId
            # Cerchiamo per _id (ricerca diretta tramite MongoDB)
            mongo_data = mongo_db.Sinistro.find_one({"_id": ObjectId(identificatore)})
        else:
            # Se non è un ObjectId, consideriamo che sia una targa e cerchiamo l'ultimo intervento
            mongo_data = mongo_db.Sinistro.find_one(
                {"targa": identificatore}, 
                sort=[("data_richiesta", -1)]                 # Ordinamento decrescente per ottenere l'ultimo
            )
        
        # Se non troviamo nulla, restituiamo un errore 404
        if not mongo_data:
            return jsonify({"error": "Nessun intervento trovato"}), 404
        
        # Convertiamo l'ObjectId in stringa per poterlo inviare nel JSON di risposta
        mongo_data['_id'] = str(mongo_data['_id'])

        # Mappiamo i dati del soccorso dentro un oggetto JSON e restituiamo
        return jsonify({
            "soccorso_info": mongo_data
        }), 200

    except Exception as e:
        # In caso di qualunque errore, restituiamo un messaggio generico
        return jsonify({"error": f"Errore nel recupero dati: {str(e)}"}), 500

# Se eseguiamo il file direttamente, avviamo il server Flask in modalita' debug
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)