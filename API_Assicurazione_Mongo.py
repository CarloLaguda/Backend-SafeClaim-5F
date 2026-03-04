from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAZIONE CONNESSIONI ---

# MySQL Config
mysql_config = {
    'user': 'safeclaim',
    'password': '0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
    'host': 'mysql-safeclaim.aevorastudios.com',
    'database': 'safeclaim_db',
    'port': 3306
}

# --- CONNESSIONE MONGODB ATLAS ---
MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123%23%23@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    
    # --- CORREZIONE QUI: Il database su Atlas si chiama FakeClaim ---
    db_mongo = mongo_client["FakeClaim"] 
    sinistri_col = db_mongo["Sinistro"]
    
    mongo_client.admin.command('ping')
    print("Connessione a MongoDB Atlas (Database: FakeClaim) riuscita!")
except Exception as e:
    print(f"Errore connessione MongoDB: {e}")

# --- ENDPOINT AGGIORNAMENTO SINISTRO (PUT) ---

@app.route('/sinistro/<id>', methods=['PUT'])
def aggiorna_sinistro(id):
    data = request.json
    
    if not data:
        return jsonify({"error": "Corpo della richiesta vuoto"}), 400

    campi_ammessi = [
        'stato', 
        'descrizione', 
        'perizia_id', 
        'officina_id', 
        'documenti_allegati'
    ]
    
    update_query = {k: v for k, v in data.items() if k in campi_ammessi}
    
    if not update_query:
        return jsonify({"error": "Nessun dato valido fornito per l'aggiornamento"}), 400

    try:
        # Verifichiamo che l'ID sia nel formato corretto prima di interrogare Atlas
        if not ObjectId.is_valid(id):
            return jsonify({"error": "Formato ID non valido"}), 400

        # Esecuzione dell'aggiornamento
        result = sinistri_col.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_query}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato nel database FakeClaim"}), 404

        return jsonify({
            "messaggio": "Sinistro aggiornato con successo su Atlas",
            "stato_aggiornamento": "OK",
            "campi_modificati": list(update_query.keys())
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore interno: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)