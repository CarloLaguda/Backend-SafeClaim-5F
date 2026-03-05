from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import mysql.connector
from bson import ObjectId
from datetime import datetime

app = Flask(__name__)

# Configurazione CORS per l'accesso da frontend esterni
CORS(app)

# --- CONFIGURAZIONE DATABASE ---

# Configurazione connessione MySQL
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "pythonuser",
    "password": "password123",
    "database": "gestione_assicurazioni" # Database aggiornato
}


def get_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)

# Configurazione connessione MongoDB Atlas (Database: FakeClaim)
MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123%23%23@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client["FakeClaim"]
    
    # Collezioni per pratiche, perizie e sinistri
    col_pratiche = mongo_db["Pratica"]
    col_perizie = mongo_db["Perizia"]
    col_sinistri = mongo_db["Sinistro"]
    
    mongo_client.admin.command('ping')
    print("Connessione a MongoDB Atlas (FakeClaim) riuscita!")
except Exception as e:
    print(f"Errore connessione MongoDB: {e}")

# READ: Recupero dei dati di una pratica specifica
@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["GET"])
def get_pratica(sinistro_id, perito_id):
    pratica = col_pratiche.find_one({
        "sinistro_id": sinistro_id,
        "perito_id": perito_id
    })

    if not pratica:
        return jsonify({"error": "Pratica non trovata"}), 404

    pratica["_id"] = str(pratica["_id"])
    return jsonify(pratica), 200

# UPDATE/UPSERT: Aggiornamento o creazione rapida di una pratica base
@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["PUT"])
def update_pratica(sinistro_id, perito_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dati mancanti"}), 400

    query = {
        "sinistro_id": sinistro_id,
        "perito_id": perito_id
    }

    update_data = {
        "$set": {
            "titolo": data.get("titolo"),
            "descrizione": data.get("descrizione"),
            "stato": data.get("stato", "In lavorazione"),
            "note_perito": data.get("note_perito"),
            "data_aggiornamento": datetime.utcnow()
        }
    }

    col_pratiche.update_one(query, update_data, upsert=True)
    return jsonify({"status": "success"}), 200

# CREATE: Creazione perizia strutturata e aggiornamento stato sinistro
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica', methods=['POST'])
def crea_pratica_completa(id_sinistro, id_perito):
    data = request.get_json()

    # Verifica esistenza Perito su MySQL
    conn = get_mysql()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Perito WHERE id = %s", (id_perito,))
    perito_esiste = cursor.fetchone()
    cursor.close()
    conn.close()

    if not perito_esiste:
        return jsonify({"error": "Perito non trovato"}), 404

    try:
        s_id = ObjectId(id_sinistro)
    except:
        return jsonify({"error": "ID sinistro non valido"}), 400

    documenti = data.get("documenti", [])

    perizia_doc = {
        "sinistro_id": s_id,
        "perito_id": id_perito,
        "data_perizia": data.get("data_perizia"),
        "ora_perizia": data.get("ora_perizia"),
        "note_tecniche": data.get("note_tecniche"),
        "documenti": documenti,
        "stato": "aperta",
        "data_inserimento": datetime.utcnow()
    }

    result = col_perizie.insert_one(perizia_doc)
    perizia_id = result.inserted_id

    # Avanzamento stato del sinistro su MongoDB
    col_sinistri.update_one(
        {"_id": s_id},
        {"$set": {
            "stato": "in_perizia",
            "perito_id": id_perito,
            "perizia_id": str(perizia_id),
            "data_aggiornamento": datetime.utcnow()
        }}
    )

    return jsonify({
        "status": "Pratica creata",
        "id_perizia": str(perizia_id),
        "documenti_caricati": len(documenti)
    }), 201

# UPDATE: Registrazione esito rimborso e stima danno
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/rimborso', methods=['POST'])
def registra_rimborso(id_sinistro, id_perito, id_perizia):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON mancante"}), 400

    try:
        s_id = ObjectId(id_sinistro)
        p_id = ObjectId(id_perizia)
    except:
        return jsonify({"error": "Formato ID non valido"}), 400

    res = col_perizie.update_one(
        {"_id": p_id},
        {"$set": {
            "stima_danno": data.get("stima_danno"),
            "esito": data.get("esito"),
            "stato": "rimborso_inserito",
            "data_aggiornamento": datetime.utcnow()
        }}
    )

    if res.matched_count == 0:
        return jsonify({"error": "Perizia non trovata"}), 404

    col_sinistri.update_one(
        {"_id": s_id},
        {"$set": {
            "stato": "rimborso_proposto",
            "data_aggiornamento": datetime.utcnow()
        }}
    )

    return jsonify({"status": "Rimborso salvato"}), 200

# UPDATE: Assegnazione officina e avvio fase di riparazione
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/intervento', methods=['POST'])
def assegna_intervento(id_sinistro, id_perito, id_perizia):
    data = request.get_json()
    id_officina = data.get("id_officina")

    if not id_officina:
        return jsonify({"error": "ID officina mancante"}), 400

    # Verifica esistenza Officina su MySQL
    conn = get_mysql()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Officina WHERE id = %s", (id_officina,))
    officina_esiste = cursor.fetchone()
    cursor.close()
    conn.close()

    if not officina_esiste:
        return jsonify({"error": "Officina non trovata"}), 404

    try:
        s_id = ObjectId(id_sinistro)
        p_id = ObjectId(id_perizia)
    except:
        return jsonify({"error": "Formato ID non valido"}), 400

    # Aggiornamento incrociato Sinistro e Perizia
    col_sinistri.update_one(
        {"_id": s_id},
        {"$set": {
            "id_officina": id_officina,
            "stato": "in_riparazione",
            "data_inizio_lavori": data.get("data_inizio_lavori"),
            "data_aggiornamento": datetime.utcnow()
        }}
    )

    col_perizie.update_one(
        {"_id": p_id},
        {"$set": {
            "stato": "inviata_officina",
            "id_officina": id_officina
        }}
    )

    return jsonify({
        "status": "Successo",
        "nuovo_stato": "in_riparazione"
    }), 200

if __name__ == "__main__":
    # Avvio del server sulla porta 8000
    app.run(host="0.0.0.0", port=8000, debug=True)