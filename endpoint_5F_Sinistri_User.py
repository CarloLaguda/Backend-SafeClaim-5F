from flask import Flask, request, jsonify
from datetime import datetime
import mysql.connector
import pymongo
from bson.objectid import ObjectId
from flask_cors import CORS

app = Flask(__name__)

# Configurazione CORS per l'accesso da frontend esterni
CORS(app)

# Configurazione connessione MySQL
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "pythonuser",
    "password": "password123",
    "database": "gestione_assicurazioni" # Database aggiornato
}


def get_db_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

# Configurazione connessione MongoDB Atlas (Database: FakeClaim)
MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123%23%23@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client["FakeClaim"]
    
    # Collezioni per sinistri e soccorso
    sinistri_col = mongo_db["Sinistro"]
    soccorso_col = mongo_db["Soccorso"]
    
    mongo_client.admin.command('ping')
    print("Connessione a MongoDB Atlas (FakeClaim) riuscita!")
except Exception as e:
    print(f"Errore connessione MongoDB: {e}")

# CREATE: Apertura di un nuovo sinistro su MongoDB
@app.route('/sinistro', methods=['POST'])
def apri_sinistro():
    data = request.json
    required_fields = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Campo mancante: {field}"}), 400

    try:
        nuovo_sinistro = {
            "automobilista_id": data['automobilista_id'],
            "targa": data['targa'],
            "data_evento": data['data_evento'],
            "descrizione": data['descrizione'],
            "stato": "APERTO",
            "data_inserimento": datetime.utcnow(),
            "immagini": []
        }

        result = sinistri_col.insert_one(nuovo_sinistro)
        return jsonify({"status": "success", "mongo_id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# UPDATE: Aggiunta immagine Base64 a un sinistro specifico
@app.route('/sinistro/<id>/immagini', methods=['POST'])
def aggiungi_immagine(id):
    data = request.json
    if not data or 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        if not ObjectId.is_valid(id):
            return jsonify({"error": "ID malformato"}), 400

        result = sinistri_col.update_one(
            {"_id": ObjectId(id)},
            {"$push": {"immagini": data['immagine_base64']}}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# UPDATE: Caricamento immagine nell'ultimo sinistro creato
@app.route('/sinistro/ultimo/immagini', methods=['POST'])
def aggiungi_immagine_ultimo():
    data = request.json
    if not data or 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        ultimo = sinistri_col.find_one(sort=[("data_inserimento", -1)])
        if not ultimo:
            return jsonify({"error": "Nessun sinistro trovato"}), 404

        sinistri_col.update_one(
            {"_id": ultimo["_id"]},
            {"$push": {"immagini": data['immagine_base64']}}
        )
        return jsonify({"status": "success", "id_usato": str(ultimo["_id"])}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# CREATE: Richiesta soccorso stradale (Atlas + Log MySQL)
@app.route('/soccorso', methods=['POST'])
def crea_richiesta_soccorso():
    data = request.json
    if not data or not data.get('targa'):
        return jsonify({"error": "Targa obbligatoria"}), 400

    targa = data.get('targa')
    descrizione = data.get('descrizione', "Richiesta soccorso")
    
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id FROM Veicolo WHERE targa = %s", (targa,))
        veicolo = cursor.fetchone()

        if not veicolo:
            return jsonify({"error": "Veicolo non trovato nel database MySQL"}), 404

        nuovo_soccorso = {
            "veicolo_id": veicolo['id'],
            "targa": targa,
            "posizione": {"lat": data.get('lat'), "lon": data.get('lon')},
            "stato": "Richiesto",
            "dettagli": descrizione,
            "data_richiesta": datetime.utcnow()
        }
        result = soccorso_col.insert_one(nuovo_soccorso)
        mongo_id = str(result.inserted_id)

        sql = """
            INSERT INTO Documenti_Anagrafica
            (entita_tipo, entita_id, mongo_doc_id, tipo_documento, descrizione)
            VALUES ('soccorso', %s, %s, 'intervento_stradale', %s)
        """
        cursor.execute(sql, (veicolo['id'], mongo_id, descrizione))
        connection.commit()

        return jsonify({"intervento_id": mongo_id, "stato": "In attesa"}), 201
    except Exception as e:
        if connection: connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if connection: connection.close()

# READ: Recupero dettaglio soccorso e dati certificati veicolo
@app.route('/soccorso/<string:identificatore>', methods=['GET'])
def get_dettaglio_soccorso(identificatore):
    connection = None
    try:
        if ObjectId.is_valid(identificatore):
            mongo_data = soccorso_col.find_one({"_id": ObjectId(identificatore)})
        else:
            mongo_data = soccorso_col.find_one({"targa": identificatore}, sort=[("data_richiesta", -1)])

        if not mongo_data:
            return jsonify({"error": "Intervento non trovato"}), 404

        mongo_data['_id'] = str(mongo_data['_id'])

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Veicolo WHERE id = %s", (mongo_data['veicolo_id'],))
        veicolo = cursor.fetchone()

        return jsonify({"soccorso_info": mongo_data, "veicolo_certificato": veicolo}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection: connection.close()

#PER USER: VEDERE I SUO VEICOLI
@app.route('/veicoli/<int:id>', methods=['GET'])
def get_veicoli(id=None):
    """GET Unificata: recupera tutti i veicoli o uno specifico per ID"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if id:
            cursor.execute("SELECT * FROM Veicolo WHERE id = %s", (id,))
            veicolo = cursor.fetchone()
            if not veicolo: return jsonify({"error": "Veicolo non trovato"}), 404
            return jsonify(veicolo), 200
        else:
            cursor.execute("SELECT * FROM Veicolo")
            return jsonify(cursor.fetchall()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# AVVIO SERVER
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7000)