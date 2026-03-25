from flask import Flask, request, jsonify
import mysql.connector
import re
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

# --- CONFIGURAZIONI DATABASE ---

# Configurazione MySQL
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "pythonuser",
    "password": "password123",
    "database": "gestione_assicurazioni" # Database aggiornato
}

# --- NUOVA CONFIGURAZIONE MONGODB ATLAS ---
# Stringa aggiornata con il nuovo cluster Atlas
MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123%23%23@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Database rinominato in 'FakeClaim' come da tua configurazione Atlas
    mongo_db = mongo_client['FakeClaim']
    sinistri_col = mongo_db['Sinistro']
    
    # Verifica immediata della connessione
    mongo_client.admin.command('ping')
    print("Connessione a MongoDB Atlas (FakeClaim) riuscita!")
except Exception as e:
    print(f"Errore critico connessione MongoDB: {e}")

def get_mysql_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)


#CRUD delle polizze
@app.route('/polizze', methods=['POST'])
def crea_polizza():
    data = request.get_json()
    conn = get_mysql_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO Polizza (n_polizza, compagnia_assicurativa, data_inizio, 
        data_scadenza, massimale, tipo_copertura, veicolo_id, assicuratore_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (data['n_polizza'], data.get('compagnia_assicurativa'), data['data_inizio'],
              data['data_scadenza'], data.get('massimale'), data.get('tipo_copertura', 'RCA'), 
              data['veicolo_id'], data['assicuratore_id'])
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
    query = "UPDATE Polizza SET n_polizza=%s, data_scadenza=%s WHERE id=%s"
    cursor.execute(query, (data['n_polizza'], data['data_scadenza'], id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Polizza aggiornata"}), 200

@app.route('/polizze/<int:id>', methods=['DELETE'])
def elimina_polizza(id):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Polizza WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Polizza eliminata"}), 200

if __name__ == '__main__':
    # Mantenuta porta 6000 come da tua ultima riga
    app.run(host='0.0.0.0', port=9000, debug=True)
