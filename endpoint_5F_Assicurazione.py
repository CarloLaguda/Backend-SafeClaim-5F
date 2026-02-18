from flask import Flask, request, jsonify
import mysql.connector
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAZIONI DATABASE ---

# Configurazione MySQL
db_config = {
    "host": "mysql-safeclaim.aevorastudios.com",
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db",
    "port": 3306
}

# Configurazione MongoDB
MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client['safeclaim_mongo']
sinistri_col = mongo_db['Sinistro']

def get_mysql_connection():
    return mysql.connector.connect(**db_config)

# --- ENDPOINT POLIZZE (MySQL) ---

@app.route('/polizze', methods=['POST'])
def crea_polizza():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Formato non valido, serve JSON"}), 415
    
    conn = get_mysql_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO Polizza (n_polizza, compagnia_assicurativa, data_inizio, 
        data_scadenza, massimale, tipo_copertura, veicolo_id, assicuratore_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        data['n_polizza'], 
        data.get('compagnia_assicurativa'), 
        data['data_inizio'],
        data['data_scadenza'], 
        data.get('massimale'), 
        data.get('tipo_copertura', 'RCA'), 
        data['veicolo_id'], 
        data['assicuratore_id']
    )
    
    try:
        cursor.execute(query, values)
        conn.commit()
        return jsonify({"message": "Polizza inserita!", "id": cursor.lastrowid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/polizze', methods=['GET'])
def leggi_polizze():
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Polizza")
    risultati = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(risultati), 200

@app.route('/polizze/<int:id>', methods=['PUT'])
def modifica_polizza(id):
    data = request.get_json()
    conn = get_mysql_connection()
    cursor = conn.cursor()
    
    try:
        query = "UPDATE Polizza SET n_polizza=%s, data_scadenza=%s WHERE id=%s"
        cursor.execute(query, (data['n_polizza'], data['data_scadenza'], id))
        conn.commit()
        return jsonify({"message": "Polizza aggiornata"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/polizze/<int:id>', methods=['DELETE'])
def elimina_polizza(id):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Polizza WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Polizza eliminata"}), 200

# --- ENDPOINT SINISTRI (MongoDB) ---

@app.route('/sinistro/<id_sinistro>/perito', methods=['PUT'])
def assegna_perito(id_sinistro):
    try:
        data = request.get_json()
        id_perito = data.get('id_perito')
        
        if id_perito is None:
            return jsonify({"error": "Campo 'id_perito' mancante"}), 400

        result = sinistri_col.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {
                "perito_id": id_perito,
                "stato": "assegnato_a_perito",
                "data_assegnazione": datetime.now()
            }}
        )

        if result.matched_count > 0:
            return jsonify({
                "status": "success",
                "message": f"Il perito {id_perito} è stato assegnato al sinistro {id_sinistro}"
            }), 200
        else:
            return jsonify({"error": "Sinistro non trovato"}), 404

    except Exception as e:
        return jsonify({"error": "ID non valido o errore server", "details": str(e)}), 400

# --- AVVIO APP ---

if __name__ == '__main__':
    # Ho impostato la porta 5000 come default
    app.run(host='0.0.0.0', port=5000, debug=True)