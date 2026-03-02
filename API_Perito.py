from flask import Flask, request, jsonify
import mysql.connector
import pymongo
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import urllib.parse

app = Flask(__name__)

# --- 1. CONFIGURAZIONE ---
user = "dbFakeClaim"
password = "xxx123##"
encoded_password = urllib.parse.quote_plus(password)
CONNECTION_STRING = f"mongodb+srv://{user}:{encoded_password}@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
DB_NAME = "FakeClaim"

# Connessione MongoDB
try:
    mongo_client = MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    db = mongo_client[DB_NAME]
    mongo_client.admin.command('ping')
    print("✅ MongoDB Connesso!")
except Exception as e:
    print(f"❌ Errore MongoDB: {e}")

# --- 2. ROTTE API (TUTTE BYPASSATE PER I TEST) ---

# A. APERTURA PRATICA
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica', methods=['POST'])
def crea_pratica(id_sinistro, id_perito):
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Dati mancanti"}), 400

        # Bypass MySQL per test
        perito_esiste = True 

        s_id = ObjectId(id_sinistro)
        doc_perizia = {
            "sinistro_id": s_id,
            "perito_id": id_perito,
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
                "perito_id": id_perito,
                "perizia_id": perizia_id,
                "data_aggiornamento": datetime.now()
            }}
        )

        return jsonify({"status": "Successo (MySQL Bypass)", "id_perizia": str(perizia_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# B. REGISTRAZIONE RIMBORSO
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
        return jsonify({"status": "Rimborso salvato"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# C. ASSEGNAZIONE INTERVENTO
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/intervento', methods=['POST'])
def assegna_intervento(id_sinistro, id_perito, id_perizia):
    try:
        data = request.get_json()
        # Bypass MySQL per test
        officina_esiste = True 
        id_officina = data.get("id_officina")

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
        return jsonify({"status": "Intervento assegnato"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)