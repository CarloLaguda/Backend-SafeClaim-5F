from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import mysql.connector
from datetime import datetime
import urllib.parse  # <--- Necessario per gestire i caratteri speciali della password

app = Flask(__name__)

# --- CONFIGURAZIONE CONNESSIONI ---

# 1. Configurazione MySQL
mysql_config = {
    'user': 'safeclaim',
    'password': '0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
    'host': 'mysql-safeclaim.aevorastudios.com',
    'database': 'safeclaim_db',
    'port': 3306
}

# 2. Configurazione MongoDB con Fix Authentication
username = "safeclaim"
password = "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM="
# Eseguiamo l'encoding della password per evitare l'errore "Authentication failed"
safe_password = urllib.parse.quote_plus(password)

mongo_uri = f"mongodb://{username}:{safe_password}@mongo-safeclaim.aevorastudios.com:27017/safeclaim_mongo?authSource=admin"

try:
    mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client["safeclaim_mongo"]
    sinistri_col = mongo_db["Sinistro"]
    # Test connessione immediato
    mongo_client.admin.command('ping')
    print("Connessione MongoDB riuscita!")
except Exception as e:
    print(f"Errore connessione MongoDB: {e}")

# --- ENDPOINTS ---

@app.route('/sinistro', methods=['POST'])
def crea_sinistro():
    data = request.json
    try:
        # Validazione MySQL
        db_mysql = mysql.connector.connect(**mysql_config)
        cursor = db_mysql.cursor()
        cursor.execute("SELECT id FROM Polizza WHERE id = %s", (data.get('polizza_id'),))
        if not cursor.fetchone():
            return jsonify({"error": "Polizza non trovata"}), 404

        # Inserimento MongoDB
        nuovo = {
            "automobilista_id": data['automobilista_id'],
            "veicolo_id": data['veicolo_id'],
            "polizza_id": data['polizza_id'],
            "descrizione": data['descrizione'],
            "stato": "aperto",
            "data_apertura": datetime.now().isoformat()
        }
        res = sinistri_col.insert_one(nuovo)
        return jsonify({"id": str(res.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'db_mysql' in locals() and db_mysql.is_connected():
            cursor.close()
            db_mysql.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)