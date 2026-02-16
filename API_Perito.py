from flask import Flask, request, jsonify
import mysql.connector
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

app = Flask(__name__)

# Configurazione DB
MYSQL_CONFIG = {
    "host": "mysql-safeclaim.aevorastudios.com",
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db"
}
mongo_client = MongoClient("mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/")
mongo_db = mongo_client["safeclaim_mongo"]

@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica', methods=['POST'])
def crea_pratica(id_sinistro, id_perito):
    data = request.get_json()
    
    # 1. Verifica Perito su MySQL
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Perito WHERE id = %s", (id_perito,))
    perito_esiste = cursor.fetchone()
    cursor.close()
    conn.close()

    if not perito_esiste:
        return jsonify({"error": "Perito non trovato"}), 404

    # 2. Operazioni MongoDB
    s_id = ObjectId(id_sinistro)

    # Creazione documento Perizia
    doc_perizia = {
        "sinistro_id": s_id,
        "perito_id": id_perito,
        "data_perizia": data.get("data_perizia"),
        "ora_perizia": data.get("ora_perizia"),
        "note_tecniche": data.get("note_tecniche"),
        "stato": "aperta",
        "data_inserimento": datetime.now()
    }
    
    res = mongo_db.perizie.insert_one(doc_perizia)
    perizia_id = res.inserted_id

    # Aggiornamento Sinistro
    update_data = {
        "$set": {
            "stato": "in_perizia",
            "perito_id": id_perito,
            "perizia_id": perizia_id,
            "data_aggiornamento": datetime.now()
        }
    }
    
    mongo_db.sinistri.update_one({"_id": s_id}, update_data)

    return jsonify({
        "status": "Pratica creata",
        "id_perizia": str(perizia_id)
    }), 201

if __name__ == '__main__':
    app.run(debug=True)