from flask import Flask, request, jsonify
from pymongo import MongoClient
import mysql.connector

app = Flask(__name__)

# --- CONNESSIONI ---

# MongoDB (Pratiche)
mongo_client = MongoClient("mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/")
db_mongo = mongo_client['safeclaim_mongo']
col_pratiche = db_mongo['pratiche']

# MySQL (Dati strutturati)
def get_mysql():
    return mysql.connector.connect(
        host="mysql-safeclaim.aevorastudios.com",
        user="safeclaim",
        password="0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
        database="safeclaim_db"
    )

# --- ENDPOINTS ---

@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["GET"])
def get_pratica(sinistro_id, perito_id):
    query = {"sinistro_id": sinistro_id, "perito_id": perito_id}
    pratica = col_pratiche.find_one(query)
    
    if pratica:
        pratica["_id"] = str(pratica["_id"])  # Converte l'ID di Mongo in stringa
        return jsonify(pratica), 200
    
    return jsonify({"error": "Pratica non trovata"}), 404

@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["PUT"])
def update_pratica(sinistro_id, perito_id):
    # Recupera i dati dal corpo della richiesta JSON
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Dati mancanti"}), 400

    query = {"sinistro_id": sinistro_id, "perito_id": perito_id}
    
    # Prepara i dati per l'aggiornamento
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
    # Avvio del server Flask sulla porta 8000
    app.run(host="0.0.0.0", port=8000, debug=True)