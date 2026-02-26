from flask import Flask, request, jsonify
import pymysql
import pymongo
from datetime import datetime
from bson import ObjectId
from urllib.parse import quote_plus

app = Flask(__name__)

# --- CONFIGURAZIONE DATABASE ---

# 1. Configurazione MySQL (Dati strutturati)
mysql_config = {
    'host': 'mysql-safeclaim.aevorastudios.com',
    'port': 3306,
    'user': 'safeclaim',
    'password': '0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
    'database': 'safeclaim_db',
   # 'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 10
}

# 2. Configurazione MongoDB Atlas (Nuove credenziali)
# Utilizziamo le nuove credenziali fornite per Cluster0
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

def get_db_connection():
    """Ritorna una nuova connessione a MySQL con gestione errore"""
    try:
        return pymysql.connect(**mysql_config)
    except Exception as e:
        print(f"Errore connessione MySQL: {e}")
        return None

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

        connection = get_db_connection()
        if connection is None:
            return jsonify({"error": "Database MySQL non raggiungibile"}), 500

        with connection.cursor() as cursor:
            # A. Verifica esistenza veicolo su MySQL
            cursor.execute("SELECT id FROM Veicolo WHERE targa = %s", (targa_veicolo,))
            veicolo = cursor.fetchone()
            
            if not veicolo:
                return jsonify({"error": f"Veicolo con targa {targa_veicolo} non trovato"}), 404

            # B. Inserimento dati dinamici su MongoDB
            nuovo_soccorso_mongo = {
                "veicolo_id": veicolo['id'],
                "targa": targa_veicolo,
                "posizione": {"lat": lat, "lon": lon},
                "stato": "Richiesto",
                "dettagli": descrizione_guasto,
                "data_richiesta": datetime.utcnow()
            }
            
            # Usiamo la collezione 'Sinistro' nel nuovo DB 'FakeClaim'
            result_mongo = mongo_db.Sinistro.insert_one(nuovo_soccorso_mongo)
            mongo_id = str(result_mongo.inserted_id)

            # C. Registrazione log su MySQL
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
                "database_utilizzato": DB_NAME,
                "stato": "In attesa"
            }), 201

    except pymongo.errors.PyMongoError as e:
        return jsonify({"error": f"Errore Database MongoDB: {str(e)}"}), 500
    except pymysql.MySQLError as e:
        if 'connection' in locals() and connection: connection.rollback()
        return jsonify({"error": f"Errore Database MySQL: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Errore generico: {str(e)}"}), 500
    finally:
        if 'connection' in locals() and connection: connection.close()


### 2. GET /soccorso/<identificatore>
@app.route('/soccorso/<string:identificatore>', methods=['GET'])
def get_dettaglio_soccorso(identificatore):
    connection = None
    try:
        # A. Ricerca su MongoDB (FakeClaim)
        if ObjectId.is_valid(identificatore):
            mongo_data = mongo_db.Sinistro.find_one({"_id": ObjectId(identificatore)})
        else:
            mongo_data = mongo_db.Sinistro.find_one(
                {"targa": identificatore}, 
                sort=[("data_richiesta", -1)]
            )
        
        if not mongo_data:
            return jsonify({"error": "Nessun intervento trovato"}), 404
        
        mongo_data['_id'] = str(mongo_data['_id'])

        # B. Recupero dati tecnici da MySQL
        connection = get_db_connection()
        if connection:
            with connection.cursor() as cursor:
                sql = "SELECT targa, marca, modello, anno_immatricolazione FROM Veicolo WHERE id = %s"
                cursor.execute(sql, (mongo_data['veicolo_id'],))
                veicolo_data = cursor.fetchone()
        else:
            veicolo_data = "Servizio MySQL momentaneamente non disponibile"

        return jsonify({
            "soccorso_info": mongo_data,
            "veicolo_certificato": veicolo_data
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore nel recupero dati: {str(e)}"}), 500
    finally:
        if connection: connection.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)