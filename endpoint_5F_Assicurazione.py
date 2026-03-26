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

# --- ENDPOINT SINISTRI (GET) ---
@app.route('/sinistri', defaults={'id_sinistro': None}, methods=['GET'])
@app.route('/sinistri/<id_sinistro>', methods=['GET'])
def ottieni_sinistri(id_sinistro):
    try:
        if id_sinistro:
            if not ObjectId.is_valid(id_sinistro):
                return jsonify({"error": "Formato ID non valido"}), 400
            
            sinistro = sinistri_col.find_one({"_id": ObjectId(id_sinistro)})
            if not sinistro:
                return jsonify({"error": "Sinistro non trovato"}), 404

            sinistro['_id'] = str(sinistro['_id'])
            return jsonify(sinistro), 200
        else:
            cursor = sinistri_col.find()
            lista = []
            for s in cursor:
                s['_id'] = str(s['_id'])
                lista.append(s)
            return jsonify({"count": len(lista), "data": lista}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GESTIONE SINISTRI (PUT - MongoDB Atlas) ---
@app.route('/sinistro/<id_sinistro>/perito', methods=['PUT'])
def assegna_perito(id_sinistro):
    try:
        data = request.get_json()
        id_perito = data.get('id_perito')
        if id_perito is None: return jsonify({"error": "id_perito mancante"}), 400

        result = sinistri_col.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {"perito_id": id_perito, "stato": "assegnato_a_perito", "data_assegnazione": datetime.now()}}
        )
        if result.matched_count > 0:
            return jsonify({"status": "success", "message": "Perito assegnato"}), 200
        return jsonify({"error": "Sinistro non trovato"}), 404
    except Exception as e:
        return jsonify({"error": "ID malformato o errore server"}), 400

@app.route('/sinistro/<id>', methods=['PUT'])
def aggiorna_sinistro(id):
    data = request.json
    campi_ammessi = ['stato', 'descrizione', 'perizia_id', 'officina_id', 'documenti_allegati']
    update_query = {k: v for k, v in data.items() if k in campi_ammessi}
    
    if not update_query: return jsonify({"error": "Dati non validi"}), 400

    try:
        if not ObjectId.is_valid(id): return jsonify({"error": "ID malformato"}), 400
        
        result = sinistri_col.update_one({"_id": ObjectId(id)}, {"$set": update_query})
        if result.matched_count == 0: return jsonify({"error": "Sinistro non trovato"}), 404

        return jsonify({"messaggio": "Aggiornato su Atlas", "campi": list(update_query.keys())}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/veicoli-utente/<int:user_id>', methods=['GET'])
def get_veicoli_utente(user_id):
    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        # Questa query va a cercare nel tuo MySQL i veicoli di quell'utente
        query = "SELECT * FROM Veicolo WHERE automobilista_id = %s"
        cursor.execute(query, (user_id,))
        veicoli = cursor.fetchall()
        return jsonify(veicoli), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    # Mantenuta porta 6000 come da tua ultima riga
    app.run(host='0.0.0.0', port=5000, debug=True)