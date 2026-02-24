from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import mysql.connector
from datetime import datetime
import urllib.parse

app = Flask(__name__)

# --- CONFIGURAZIONE CONNESSIONI ---

# MySQL Config (mantenuta per coerenza di sistema, anche se la PUT lavora su MongoDB)
mysql_config = {
    'user': 'safeclaim',
    'password': '0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
    'host': 'mysql-safeclaim.aevorastudios.com',
    'database': 'safeclaim_db',
    'port': 3306
}

# MongoDB Connection
username = "safeclaim"
password = "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM="
safe_password = urllib.parse.quote_plus(password)
mongo_uri = f"mongodb://{username}:{safe_password}@mongo-safeclaim.aevorastudios.com:27017/safeclaim_mongo?authSource=admin"

try:
    mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db_mongo = mongo_client["safeclaim_mongo"]
    sinistri_col = db_mongo["Sinistro"]
except Exception as e:
    print(f"Errore connessione MongoDB: {e}")

# --- ENDPOINT AGGIORNAMENTO SINISTRO (PUT) ---

@app.route('/sinistro/<id>', methods=['PUT'])
def aggiorna_sinistro(id):
    """
    Endpoint per aggiornare lo stato e i dettagli di un sinistro esistente.
    Permette l'avanzamento della pratica come richiesto dalla WBS.
    """
    data = request.json
    
    # Campi che la WBS permette di aggiornare durante la gestione della pratica
    campi_ammessi = [
        'stato',                # Es: "IN_PERIZIA", "CHIUSO", "IN_RIPARAZIONE"
        'descrizione',          # Aggiornamenti testuali sulla dinamica
        'perizia_id',           # Collegamento al documento Perizia su MongoDB
        'officina_id',          # ID dell'officina scelta (da MySQL)
        'documenti_allegati'    # Array di ID riferiti a Documenti_Anagrafica
    ]
    
    # Filtro dei dati in input: accettiamo solo i campi definiti sopra
    update_query = {k: v for k, v in data.items() if k in campi_ammessi}
    
    if not update_query:
        return jsonify({"error": "Nessun dato valido fornito per l'aggiornamento"}), 400

    try:
        # Esecuzione dell'aggiornamento su MongoDB tramite ObjectId
        result = sinistri_col.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_query}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato o ID non valido"}), 404

        return jsonify({
            "messaggio": "Sinistro aggiornato con successo",
            "stato_aggiornamento": "OK",
            "campi_modificati": list(update_query.keys())
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante l'aggiornamento: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)