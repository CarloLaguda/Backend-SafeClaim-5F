from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import mysql.connector
import firebase_admin
from firebase_admin import credentials, messaging 

app = Flask(__name__)
CORS(app)

# --- CONFIGURAZIONE FIREBASE ---
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

# --- CONNESSIONI ---

# Credenziali e stringa di connessione per il Database NoSQL (MongoDB Atlas)
user = "dbFakeClaim"
password = "xxx123##"
# Il password encoding serve per gestire caratteri speciali nella URL di connessione
encoded_password = urllib.parse.quote_plus(password)
CONNECTION_STRING = f"mongodb+srv://{user}:{encoded_password}@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
DB_NAME = "FakeClaim"

try:
    # Inizializzazione del client MongoDB con timeout di 5 secondi
    mongo_client = MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    db = mongo_client[DB_NAME]
    # Il comando 'ping' verifica se il server è effettivamente raggiungibile
    mongo_client.admin.command('ping')
    print("✅ MongoDB Connesso!")
except Exception as e:
    print(f"❌ Errore MongoDB: {e}")

def get_mysql_connection():
    """Ritorna un oggetto di connessione MySQL attivo."""
    return mysql.connector.connect(**mysql_config)

# MySQL (Dati strutturati)
def get_mysql():
    return mysql.connector.connect(
        host="mysql-safeclaim.aevorastudios.com",
        user="safeclaim",
        password="0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
        database="safeclaim_db"
    )

# --- ENDPOINTS ---

# Nuovo Endpoint per inviare notifiche push
@app.route("/invia-notifica", methods=["POST"])
def invia_notifica():
    data = request.get_json()
    token_dispositivo = data.get('token') # Il token che arriva dal frontend
    titolo = data.get('titolo', 'SafeClaim Update')
    messaggio = data.get('messaggio', 'C\'è una novità sulla tua pratica.')

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

# --- AVVIO ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)