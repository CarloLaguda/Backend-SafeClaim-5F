from flask import Flask, request, jsonify
import pymysql
import pymongo
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAZIONE DATABASE (Remoto) ---

mysql_config = {
    'host': 'mysql-safeclaim.aevorastudios.com',
    'port': 3306,
    'user': 'safeclaim',
    'password': '0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
    'database': 'safeclaim_db',
    'cursorclass': pymysql.cursors.DictCursor
}

# La password viene passata con quote_plus per gestire i caratteri speciali (+)
mongo_uri = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
mongo_client = pymongo.MongoClient(mongo_uri)
mongo_db = mongo_client["safeclaim_mongo"]

def get_db_connection():
    return pymysql.connect(**mysql_config)

# --- ENDPOINTS RICHIESTI ---

### 1. POST /SOCCORSO
# Registra un intervento di soccorso su MongoDB e crea il riferimento in MySQL
@app.route('/soccorso', methods=['POST'])
def crea_richiesta_soccorso():
    data = request.json
    
    # Campi necessari dall'input
    targa_veicolo = data.get('targa')
    descrizione_guasto = data.get('descrizione', "Richiesta soccorso stradale")
    lat = data.get('lat')
    lon = data.get('lon')

    if not targa_veicolo:
        return jsonify({"error": "La targa del veicolo è obbligatoria"}), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Verifichiamo se il veicolo esiste in MySQL
            cursor.execute("SELECT id, automobilista_id FROM Veicolo WHERE targa = %s", (targa_veicolo,))
            veicolo = cursor.fetchone()
            
            if not veicolo:
                return jsonify({"error": "Veicolo non trovato nel database"}), 404

            # 1. Creiamo l'evento dinamico su MongoDB (Sinistro/Soccorso)
            nuovo_soccorso_mongo = {
                "veicolo_id": veicolo['id'],
                "targa": targa_veicolo,
                "posizione": {"lat": lat, "lon": lon},
                "stato": "Richiesto",
                "dettagli": descrizione_guasto,
                "data_richiesta": datetime.utcnow()
            }
            # Inseriamo nella collezione 'Sinistro' (come da docx, che gestisce dati GPS flessibili)
            result_mongo = mongo_db.Sinistro.insert_one(nuovo_soccorso_mongo)
            mongo_id = str(result_mongo.inserted_id)

            # 2. Registriamo il riferimento in MySQL su Documenti_Anagrafica 
            # (usiamo questa tabella esistente per tracciare il legame tra entità e documento mongo)
            sql_mysql = """
                INSERT INTO Documenti_Anagrafica 
                (entita_tipo, entita_id, mongo_doc_id, tipo_documento, descrizione) 
                VALUES ('soccorso', %s, %s, 'intervento_stradale', %s)
            """
            cursor.execute(sql_mysql, (veicolo['id'], mongo_id, descrizione_guasto))
            
            connection.commit()
            return jsonify({
                "message": "Soccorso prenotato",
                "mongo_id": mongo_id,
                "stato": "In attesa"
            }), 201

    except Exception as e:
        if connection: connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if connection: connection.close()

### 2. GET /soccorso/<id>
# Recupera i dettagli del soccorso tramite l'ID di MongoDB
@app.route('/soccorso/<string:id>', methods=['GET'])
def get_dettaglio_soccorso(id):
    try:
        # 1. Recuperiamo i dati dinamici da MongoDB
        from bson import ObjectId
        mongo_data = mongo_db.Sinistro.find_one({"_id": ObjectId(id)})
        
        if not mongo_data:
            return jsonify({"error": "Intervento non trovato"}), 404
        
        mongo_data['_id'] = str(mongo_data['_id']) # Convertiamo per JSON

        # 2. Recuperiamo i dati strutturati del veicolo da MySQL
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT targa, marca, modello FROM Veicolo WHERE id = %s"
            cursor.execute(sql, (mongo_data['veicolo_id'],))
            veicolo_data = cursor.fetchone()

            # Uniamo i dati
            risultato = {
                "soccorso_details": mongo_data,
                "veicolo": veicolo_data
            }
            
            return jsonify(risultato), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'connection' in locals(): connection.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)