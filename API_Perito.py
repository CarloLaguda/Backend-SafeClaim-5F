from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
import pymongo
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import urllib.parse

app = Flask(__name__)

# --- 1. CONFIGURAZIONE ---

# Configurazione MySQL
mysql_config = {
    'host': 'localhost',
    'user': 'pythonuser',
    'password': 'password123',
    'database': 'Locale_DB'
}

# Configurazione MongoDB
user = "dbFakeClaim"
password = "xxx123##"
encoded_password = urllib.parse.quote_plus(password)
CONNECTION_STRING = f"mongodb+srv://{user}:{encoded_password}@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
DB_NAME = "FakeClaim"

# Inizializzazione MongoDB
try:
    mongo_client = MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    db = mongo_client[DB_NAME]
    mongo_client.admin.command('ping')
    print("✅ MongoDB Connesso!")
except Exception as e:
    print(f"❌ Errore MongoDB: {e}")

# Helper per connessione MySQL
def get_mysql_connection():
    return mysql.connector.connect(**mysql_config)

# --- 2. ROTTE API CON INTEGRAZIONE MYSQL ---

# A. APERTURA PRATICA
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica', methods=['POST'])
def crea_pratica(id_sinistro, id_perito):
    conn = None
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Dati mancanti"}), 400

        # --- VALIDAZIONE MYSQL ---
        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Perito WHERE id = %s", (id_perito,))
        perito = cursor.fetchone()
        
        if not perito:
            return jsonify({"error": f"Perito con ID {id_perito} non trovato nel database relazionale"}), 404

        # --- OPERAZIONE MONGODB ---
        s_id = ObjectId(id_sinistro)
        doc_perizia = {
            "sinistro_id": s_id,
            "perito_id": int(id_perito), # Salviamo come intero per coerenza con MySQL
            "data_perizia": data.get("data_perizia"),
            "ora_perizia": data.get("ora_perizia"),
            "note_tecniche": data.get("note_tecniche"),
            "documenti": data.get("documenti", []),
            "stato": "aperta",
            "data_inserimento": datetime.now()
        }

        res = db.perizie.insert_one(doc_perizia)
        perizia_id = res.inserted_id

        db.sinistri.update_one(
            {"_id": s_id},
            {"$set": {
                "stato": "in_perizia",
                "perito_id": int(id_perito),
                "perizia_id": perizia_id,
                "data_aggiornamento": datetime.now()
            }}
        )

        return jsonify({
            "status": "Pratica creata e Perito verificato", 
            "id_perizia": str(perizia_id)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# B. REGISTRAZIONE RIMBORSO (Solo MongoDB, come da tua logica)
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/rimborso', methods=['POST'])
def registra_rimborso(id_sinistro, id_perito, id_perizia):
    try:
        data = request.get_json()
        db.perizie.update_one(
            {"_id": ObjectId(id_perizia)},
            {"$set": {
                "stima_danno": data.get("stima_danno"),
                "esito": data.get("esito"),
                "stato": "rimborso_inserito",
                "data_aggiornamento": datetime.now()
            }}
        )
        db.sinistri.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {"stato": "rimborso_proposto", "data_aggiornamento": datetime.now()}}
        )
        return jsonify({"status": "Rimborso salvato correttamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# C. ASSEGNAZIONE INTERVENTO
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/intervento', methods=['POST'])
def assegna_intervento(id_sinistro, id_perito, id_perizia):
    conn = None
    try:
        data = request.get_json()
        id_officina = data.get("id_officina")

        # --- VALIDAZIONE MYSQL ---
        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Officina WHERE id = %s", (id_officina,))
        officina = cursor.fetchone()

        if not officina:
            return jsonify({"error": f"Officina con ID {id_officina} non esistente"}), 404

        # --- OPERAZIONE MONGODB ---
        db.sinistri.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {
                "id_officina": id_officina,
                "stato": "in_riparazione",
                "data_inizio_lavori": data.get("data_inizio_lavori"),
                "data_aggiornamento": datetime.now()
            }}
        )
        db.perizie.update_one(
            {"_id": ObjectId(id_perizia)},
            {"$set": {"stato": "inviata_officina", "id_officina": id_officina}}
        )
        return jsonify({"status": "Intervento assegnato e Officina verificata"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)