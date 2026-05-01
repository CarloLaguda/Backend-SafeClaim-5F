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
    sinistri_col = mongo_db['Sinistri']
    
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
    if not data:
        return jsonify({"error": "Nessun dato fornito"}), 400
    
    conn = get_mysql_connection()
    cursor = conn.cursor()
    
    # Query più completa per riflettere i campi che invii da Angular
    query = """
        UPDATE Polizza 
        SET n_polizza=%s, 
            compagnia_assicurativa=%s, 
            data_inizio=%s, 
            data_scadenza=%s, 
            massimale=%s, 
            tipo_copertura=%s 
        WHERE id=%s
    """
    
    # Usiamo .get(chiave, default) per evitare KeyError
    values = (
        data.get('n_polizza'),
        data.get('compagnia_assicurativa'),
        data.get('data_inizio'),
        data.get('data_scadenza'),
        data.get('massimale'),
        data.get('tipo_copertura'),
        id
    )
    
    try:
        cursor.execute(query, values)
        conn.commit()
        return jsonify({"message": "Polizza aggiornata con successo"}), 200
    except Exception as e:
        print(f"Errore DB: {e}")
        return jsonify({"error": str(e)}), 500
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

if __name__ == '__main__':
    # Mantenuta porta 6000 come da tua ultima riga
    app.run(host='0.0.0.0', port=9000, debug=True)
