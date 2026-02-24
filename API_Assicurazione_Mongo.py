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
    # Indice 2dsphere per le query geospaziali richieste dalla WBS
    sinistri_col.create_index([("posizione", "2dsphere")])
    print("Connessione MongoDB e Indice Geospaziale OK!")
except Exception as e:
    print(f"Errore connessione MongoDB: {e}")

# --- 1. ENDPOINT APERTURA SINISTRO (POST) ---

@app.route('/sinistro', methods=['POST'])
def crea_sinistro():
    data = request.json
    db_mysql = None
    
    try:
        # Validazione su MySQL: Verifica che Polizza, Veicolo e Automobilista siano correlati
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
            return jsonify({"error": "Validazione fallita: i dati forniti non corrispondono ad alcuna polizza attiva"}), 403

        # Creazione documento su MongoDB (Dati flessibili)
        nuovo_sinistro = {
            "polizza_id": int(data['polizza_id']),
            "automobilista_id": int(data['automobilista_id']),
            "targa_veicolo": validazione['targa'],
            "descrizione": data.get('descrizione', ''),
            "data_apertura": datetime.now(),
            "stato": "APERTO",
            "posizione": {
                "type": "Point",
                "coordinates": [float(data['longitudine']), float(data['latitudine'])]
            },
            "perizia_id": None,
            "officina_id": None,
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

# --- 2. ENDPOINT DETTAGLIO/AGGIORNAMENTO SINISTRO (PUT) ---
# Questo è l'endpoint finale richiesto dalla WBS per la gestione dello stato

@app.route('/sinistro/<id>', methods=['PUT'])
def aggiorna_sinistro(id):
    data = request.json
    
    # Campi che la WBS permette di aggiornare durante la gestione della pratica
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
        # Aggiornamento atomico su MongoDB
        result = sinistri_col.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_query}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404

        return jsonify({
            "messaggio": "Sinistro aggiornato con successo",
            "campi_modificati": list(update_query.keys())
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante l'aggiornamento: {str(e)}"}), 500

# --- 3. ENDPOINT LETTURA DETTAGLIO (GET) ---
# Utile per il front-end per visualizzare i dati uniti di MySQL e MongoDB

@app.route('/sinistro/<id>', methods=['GET'])
def get_sinistro(id):
    db_mysql = None
    try:
        sinistro_mongo = sinistri_col.find_one({"_id": ObjectId(id)})
        if not sinistro_mongo:
            return jsonify({"error": "Sinistro non trovato"}), 404
        
        # Recupero dati anagrafici da MySQL per completare la vista
        db_mysql = mysql.connector.connect(**mysql_config)
        cursor = db_mysql.cursor(dictionary=True)
        
        query_info = """
            SELECT a.nome, a.cognome, v.marca, v.modello
            FROM Automobilista a
            JOIN Veicolo v ON v.proprietario_id = a.id
            WHERE a.id = %s
        """
        cursor.execute(query_info, (sinistro_mongo['automobilista_id'],))
        info_extra = cursor.fetchone()

        # Unione dati
        sinistro_mongo['_id'] = str(sinistro_mongo['_id'])
        sinistro_mongo['info_veicolo'] = info_extra

        return jsonify(sinistro_mongo), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if db_mysql and db_mysql.is_connected():
            db_mysql.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)