from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import mysql.connector
from datetime import datetime
import urllib.parse

app = Flask(__name__)

# --- CONFIGURAZIONE CONNESSIONI ---

# MySQL (Dati strutturati)
mysql_config = {
    'user': 'safeclaim',
    'password': '0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
    'host': 'mysql-safeclaim.aevorastudios.com',
    'database': 'safeclaim_db',
    'port': 3306
}

# MongoDB (Dati flessibili e Geospaziali)
username = "safeclaim"
password = "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM="
safe_password = urllib.parse.quote_plus(password)
mongo_uri = f"mongodb://{username}:{safe_password}@mongo-safeclaim.aevorastudios.com:27017/safeclaim_mongo?authSource=admin"

try:
    mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db_mongo = mongo_client["safeclaim_mongo"]
    sinistri_col = db_mongo["Sinistro"]
    # Creazione indice per ricerca officine vicine (richiesto dalla WBS)
    sinistri_col.create_index([("posizione", "2dsphere")])
    print("Connessione MongoDB e Indice Geospaziale OK!")
except Exception as e:
    print(f"Errore connessione MongoDB: {e}")

# --- ENDPOINT APERTURA SINISTRO ---

@app.route('/sinistro', methods=['POST'])
def crea_sinistro():
    data = request.json
    db_mysql = None
    
    try:
        # 1. Validazione su MySQL (Verifica coerenza Polizza-Veicolo-Automobilista)
        db_mysql = mysql.connector.connect(**mysql_config)
        cursor = db_mysql.cursor(dictionary=True)
        
        query_check = """
            SELECT p.id, v.targa, p.tipo_copertura
            FROM Polizza p
            JOIN Veicolo v ON p.veicolo_id = v.id
            WHERE p.id = %s AND v.id = %s AND v.proprietario_id = %s
        """
        cursor.execute(query_check, (
            data.get('polizza_id'), 
            data.get('veicolo_id'), 
            data.get('automobilista_id')
        ))
        validazione = cursor.fetchone()

        if not validazione:
            return jsonify({"error": "Dati non validi o polizza non trovata per questo utente/veicolo"}), 403

        # 2. Creazione documento su MongoDB (come da specifica Documentazione DB- SC.docx)
        nuovo_sinistro = {
            "polizza_id": data['polizza_id'],
            "automobilista_id": data['automobilista_id'],
            "targa_veicolo": validazione['targa'],
            "descrizione": data.get('descrizione', ''),
            "data_apertura": datetime.now().isoformat(),
            "stato": "APERTO",
            # Formato GeoJSON per query spaziali (Longitudine, Latitudine)
            "posizione": {
                "type": "Point",
                "coordinates": [float(data['longitudine']), float(data['latitudine'])]
            },
            "perizia_id": None,
            "documenti_allegati": []
        }

        res = sinistri_col.insert_one(nuovo_sinistro)

        return jsonify({
            "messaggio": "Sinistro creato con successo",
            "sinistro_id": str(res.inserted_id),
            "stato": "APERTO"
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if db_mysql and db_mysql.is_connected():
            cursor.close()
            db_mysql.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)