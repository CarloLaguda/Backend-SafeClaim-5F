from flask import Flask, request, jsonify
import pymysql
import pymongo
from datetime import datetime
from bson import ObjectId
from urllib.parse import quote_plus

app = Flask(__name__)

# --- CONFIGURAZIONE DATABASE ---

# Configurazione MySQL (Dati strutturati)
mysql_config = {
    'host': 'mysql-safeclaim.aevorastudios.com',
    'port': 3306,
    'user': 'safeclaim',
    'password': '0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
    'database': 'safeclaim_db',
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 10
}

# Configurazione MongoDB (Dati flessibili e GPS)
# Usiamo quote_plus per assicurarci che il simbolo '+' nella password non interrompa la connessione
mongo_uri = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
mongo_client = pymongo.MongoClient(mongo_uri)
mongo_db = mongo_client["safeclaim_mongo"]

def get_db_connection():
    """Ritorna una nuova connessione a MySQL"""
    return pymysql.connect(**mysql_config)

# --- ENDPOINTS ---

### 1. POST /soccorso
# Crea una richiesta di soccorso incrociando i dati tra i due DB
@app.route('/soccorso', methods=['POST'])
def crea_richiesta_soccorso():
    data = request.json
    if not data:
        return jsonify({"error": "Corpo della richiesta mancante"}), 400

    targa_veicolo = data.get('targa')
    descrizione_guasto = data.get('descrizione', "Richiesta soccorso stradale")
    lat = data.get('lat')
    lon = data.get('lon')

    if not targa_veicolo:
        return jsonify({"error": "La targa del veicolo è obbligatoria"}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # A. Verifica esistenza veicolo su MySQL
            cursor.execute("SELECT id FROM Veicolo WHERE targa = %s", (targa_veicolo,))
            veicolo = cursor.fetchone()
            
            if not veicolo:
                return jsonify({"error": f"Veicolo con targa {targa_veicolo} non trovato"}), 404

            # B. Inserimento dati dinamici su MongoDB (Collezione Sinistro)
            nuovo_soccorso_mongo = {
                "veicolo_id": veicolo['id'],
                "targa": targa_veicolo,
                "posizione": {"lat": lat, "lon": lon},
                "stato": "Richiesto",
                "dettagli": descrizione_guasto,
                "data_richiesta": datetime.utcnow()
            }
            result_mongo = mongo_db.Sinistro.insert_one(nuovo_soccorso_mongo)
            mongo_id = str(result_mongo.inserted_id)

            # C. Registrazione log su MySQL (Tabella Documenti_Anagrafica)
            sql_mysql = """
                INSERT INTO Documenti_Anagrafica 
                (entita_tipo, entita_id, mongo_doc_id, tipo_documento, descrizione) 
                VALUES ('soccorso', %s, %s, 'intervento_stradale', %s)
            """
            cursor.execute(sql_mysql, (veicolo['id'], mongo_id, descrizione_guasto))
            
            connection.commit()
            return jsonify({
                "message": "Soccorso registrato con successo",
                "intervento_id": mongo_id,
                "targa": targa_veicolo,
                "stato": "In attesa di assegnazione"
            }), 201

    except Exception as e:
        if connection: connection.rollback()
        return jsonify({"error": f"Errore server: {str(e)}"}), 500
    finally:
        if connection: connection.close()


### 2. GET /soccorso/<identificatore>
# Recupera dettagli soccorso tramite ID MongoDB OPPURE tramite Targa
@app.route('/soccorso/<string:identificatore>', methods=['GET'])
def get_dettaglio_soccorso(identificatore):
    connection = None
    try:
        # A. Determina se l'input è un ID MongoDB o una Targa
        if ObjectId.is_valid(identificatore):
            # Ricerca per ID diretto
            mongo_data = mongo_db.Sinistro.find_one({"_id": ObjectId(identificatore)})
        else:
            # Ricerca per Targa (prende l'ultimo intervento inserito)
            mongo_data = mongo_db.Sinistro.find_one(
                {"targa": identificatore}, 
                sort=[("data_richiesta", -1)]
            )
        
        if not mongo_data:
            return jsonify({"error": "Nessun intervento trovato per l'identificatore fornito"}), 404
        
        # Convertiamo l'ID MongoDB per renderlo leggibile in JSON
        mongo_data['_id'] = str(mongo_data['_id'])

        # B. Recupero dati tecnici del veicolo da MySQL
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT targa, marca, modello, anno_immatricolazione FROM Veicolo WHERE id = %s"
            cursor.execute(sql, (mongo_data['veicolo_id'],))
            veicolo_data = cursor.fetchone()

            # Risposta integrata
            return jsonify({
                "soccorso_info": mongo_data,
                "veicolo_certificato": veicolo_data if veicolo_data else "Dati MySQL non trovati"
            }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero: {str(e)}"}), 500
    finally:
        if connection: connection.close()

if __name__ == '__main__':
    # Avvio del server sulla porta 5000
    app.run(debug=True, host='0.0.0.0', port=5000)