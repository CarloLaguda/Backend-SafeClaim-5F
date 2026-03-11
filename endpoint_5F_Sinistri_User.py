from flask import Flask, request, jsonify
from datetime import datetime, UTC
import mysql.connector
import pymongo
from bson.objectid import ObjectId
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- CONFIGURAZIONE DATABASE ---

# MySQL (MariaDB)
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "pythonuser",
    "password": "password123",
    "database": "gestione_assicurazioni"
}

def get_db_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

# MongoDB Atlas
MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123%23%23@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client["FakeClaim"]
    sinistri_col = mongo_db["Sinistro"]
    soccorso_col = mongo_db["Soccorso"]
    
    mongo_client.admin.command('ping')
    print("✅ Connessione a MongoDB Atlas riuscita!")
except Exception as e:
    print(f"❌ Errore connessione MongoDB: {e}")

# --- ROTTE SINISTRI (MongoDB) ---

# CREATE: Apertura nuovo sinistro
@app.route('/sinistro', methods=['POST'])
def apri_sinistro():
    data = request.json
    required = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    
    if not all(k in data for k in required):
        return jsonify({"error": "Campi obbligatori mancanti"}), 400

    try:
        nuovo_sinistro = {
            "automobilista_id": data['automobilista_id'],
            "targa": data['targa'],
            "data_evento": data['data_evento'],
            "descrizione": data['descrizione'],
            "stato": "APERTO",
            "data_inserimento": datetime.now(UTC), # Corretto warning
            "immagini": []
        }
        result = sinistri_col.insert_one(nuovo_sinistro)
        return jsonify({"status": "success", "mongo_id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# READ: Visualizza TUTTI i sinistri (La rotta che mancava!)
@app.route('/sinistri', methods=['GET'])
def get_tutti_sinistri():
    try:
        sinistri = list(sinistri_col.find())
        for s in sinistri:
            s['_id'] = str(s['_id']) # Converte ID per JSON
        return jsonify(sinistri), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# UPDATE: Aggiunta immagine all'ultimo sinistro creato
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

# --- ROTTE SOCCORSO E VEICOLI (MySQL + MongoDB) ---

@app.route('/soccorso', methods=['POST'])
def crea_richiesta_soccorso():
    data = request.json
    targa = data.get('targa')
    if not targa:
        return jsonify({"error": "Targa obbligatoria"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM Veicolo WHERE targa = %s", (targa,))
        veicolo = cursor.fetchone()

        if not veicolo:
            return jsonify({"error": "Veicolo non trovato in MySQL"}), 404

        nuovo_soccorso = {
            "veicolo_id": veicolo['id'],
            "targa": targa,
            "posizione": {"lat": data.get('lat'), "lon": data.get('lon')},
            "stato": "Richiesto",
            "data_richiesta": datetime.now(UTC)
        }
        res = soccorso_col.insert_one(nuovo_soccorso)
        
        # Log su MySQL
        sql = "INSERT INTO Documenti_Anagrafica (entita_tipo, entita_id, mongo_doc_id, tipo_documento) VALUES ('soccorso', %s, %s, 'intervento')"
        cursor.execute(sql, (veicolo['id'], str(res.inserted_id)))
        conn.commit()

        return jsonify({"intervento_id": str(res.inserted_id), "stato": "In attesa"}), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/veicoli/<int:id>', methods=['GET'])
def get_veicoli(id=None):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if id:
            cursor.execute("SELECT * FROM Veicolo WHERE id = %s", (id,))
            res = cursor.fetchone()
        else:
            cursor.execute("SELECT * FROM Veicolo")
            res = cursor.fetchall()
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7000)