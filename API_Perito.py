from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import mysql.connector
import firebase_admin
from firebase_admin import credentials, messaging 
import urllib.parse # <--- MANCAVA QUESTO

app = Flask(__name__)
# CORS è fondamentale per permettere al frontend (su GitHub o altro) di parlare col tuo PC
CORS(app)

# --- CONFIGURAZIONE FIREBASE ---
# Assicurati che il file firebase-key.json sia nella stessa cartella!
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

# --- CONNESSIONI MONGODB ---
user = "dbFakeClaim"
password = "xxx123##"
encoded_password = urllib.parse.quote_plus(password)
CONNECTION_STRING = f"mongodb+srv://{user}:{encoded_password}@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
DB_NAME = "FakeClaim"

try:
    mongo_client = MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    db = mongo_client[DB_NAME]
    # Definisco col_pratiche qui, altrimenti le funzioni sotto danno errore
    col_pratiche = db["pratiche"] 
    mongo_client.admin.command('ping')
    print("✅ MongoDB Connesso!")
except Exception as e:
    print(f"❌ Errore MongoDB: {e}")

# --- ENDPOINTS ---

@app.route("/invia-notifica", methods=["POST"])
def invia_notifica():
    data = request.get_json()
    token_dispositivo = data.get('token') 
    titolo = data.get('titolo', 'SafeClaim Update')
    messaggio = data.get('messaggio', "C'è una novità sulla tua pratica.")

    if not token_dispositivo:
        return jsonify({"error": "Token mancante"}), 400

    message = messaging.Message(
        notification=messaging.Notification(
            title=titolo,
            body=messaggio,
        ),
        token=token_dispositivo,
    )

    try:
        response = messaging.send(message)
        return jsonify({"success": True, "fcm_id": response}), 200
    except Exception as e:
        print(f"❌ Errore Invio: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["GET"])
def get_pratica(sinistro_id, perito_id):
    query = {"sinistro_id": sinistro_id, "perito_id": perito_id}
    pratica = col_pratiche.find_one(query)
    
    if pratica:
        pratica["_id"] = str(pratica["_id"])
        return jsonify(pratica), 200
    
    return jsonify({"error": "Pratica non trovata"}), 404

@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["PUT"])
def update_pratica(sinistro_id, perito_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dati mancanti"}), 400

    query = {"sinistro_id": sinistro_id, "perito_id": perito_id}
    update_data = {
        "$set": {
            "titolo": data.get("titolo"),
            "descrizione": data.get("descrizione"),
            "stato": data.get("stato", "In lavorazione"),
            "note_perito": data.get("note_perito"),
            "sinistro_id": sinistro_id,
            "perito_id": perito_id
        }
    }
    
    col_pratiche.update_one(query, update_data, upsert=True)
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    # host="0.0.0.0" è corretto per il test da cellulare
    app.run(host="0.0.0.0", port=8000, debug=True)