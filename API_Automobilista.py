from flask import Flask, request, jsonify
import pymongo
from datetime import datetime
from bson import ObjectId

app = Flask(__name__)

# --- CONFIGURAZIONE DATABASE ---

# Configurazione MongoDB Atlas
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
DB_NAME = "FakeClaim"

try:
    mongo_client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client[DB_NAME]
    # Test connessione rapido
    mongo_client.admin.command('ping')
    print("Connessione a MongoDB Atlas riuscita!")
except Exception as e:
    print(f"Errore critico di connessione a MongoDB: {e}")

# --- ENDPOINTS ---

### 1. POST /soccorso
@app.route('/soccorso', methods=['POST'])
def crea_richiesta_soccorso():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Corpo della richiesta mancante"}), 400

        targa_veicolo = data.get('targa')
        descrizione_guasto = data.get('descrizione', "Richiesta soccorso stradale")
        lat = data.get('lat')
        lon = data.get('lon')

        if not targa_veicolo:
            return jsonify({"error": "La targa del veicolo è obbligatoria"}), 400

        # Inserimento dati dinamici direttamente su MongoDB (Senza verifica MySQL)
        nuovo_soccorso_mongo = {
            "targa": targa_veicolo,
            "posizione": {"lat": lat, "lon": lon},
            "stato": "Richiesto",
            "dettagli": descrizione_guasto,
            "data_richiesta": datetime.utcnow()
        }
        
        # Usiamo la collezione 'Sinistro' nel DB 'FakeClaim'
        result_mongo = mongo_db.Sinistro.insert_one(nuovo_soccorso_mongo)
        mongo_id = str(result_mongo.inserted_id)
        
        return jsonify({
            "message": "Soccorso registrato con successo",
            "intervento_id": mongo_id,
            "database_utilizzato": DB_NAME,
            "stato": "Richiesto"
        }), 201

    except pymongo.errors.PyMongoError as e:
        return jsonify({"error": f"Errore Database MongoDB: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Errore generico: {str(e)}"}), 500


### 2. GET /soccorso/<identificatore>
@app.route('/soccorso/<string:identificatore>', methods=['GET'])
def get_dettaglio_soccorso(identificatore):
    try:
        # Ricerca esclusiva su MongoDB (FakeClaim)
        if ObjectId.is_valid(identificatore):
            mongo_data = mongo_db.Sinistro.find_one({"_id": ObjectId(identificatore)})
        else:
            mongo_data = mongo_db.Sinistro.find_one(
                {"targa": identificatore}, 
                sort=[("data_richiesta", -1)]
            )
        
        if not mongo_data:
            return jsonify({"error": "Nessun intervento trovato"}), 404
        
        # Convertiamo l'ID in formato leggibile per il JSON
        mongo_data['_id'] = str(mongo_data['_id'])

        # Restituiamo solo le informazioni del soccorso (niente più dati veicolo da MySQL)
        return jsonify({
            "soccorso_info": mongo_data
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore nel recupero dati: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)