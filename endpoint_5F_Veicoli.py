from flask import Flask, request, jsonify
from datetime import datetime, UTC
import mysql.connector
import pymongo
from bson.objectid import ObjectId
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- CONFIGURAZIONE DATABASE ---

# MySQL (MariaDB)
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "pythonuser",
    "password": "password123",
    "database": "gestione_assicurazioni"
}

def get_db_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

# MongoDB Atlas
MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123%23%23@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client["FakeClaim"]
    sinistri_col = mongo_db["Sinistri"]
    soccorso_col = mongo_db["Soccorso"]
    
    mongo_client.admin.command('ping')
    print("✅ Connessione a MongoDB Atlas riuscita!")
except Exception as e:
    print(f"❌ Errore connessione MongoDB: {e}")

# VEIOCLI 
# ... (i tuoi import rimangono uguali)

@app.route('/veicoli', methods=['GET'])
@app.route('/veicoli/<int:id>', methods=['GET'])
def get_veicoli(id=None):
    # Questa rotta ora gestisce TUTTI o UNO specifico per ID VEICOLO
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if id:
            cursor.execute("SELECT * FROM Veicolo WHERE id = %s", (id,))
            veicolo = cursor.fetchone()
            if not veicolo: return jsonify({"error": "Veicolo non trovato"}), 404
            return jsonify(veicolo), 200
        else:
            cursor.execute("SELECT * FROM Veicolo")
            return jsonify(cursor.fetchall()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# --- NUOVA ROTTA AGGIUNTA PER RISOLVERE IL TUO PROBLEMA ---
@app.route('/veicoli-utente/<int:user_id>', methods=['GET'])
def get_veicoli_utente(user_id):
    """Recupera tutti i veicoli appartenenti a un utente specifico"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Veicolo WHERE automobilista_id = %s", (user_id,))
        return jsonify(cursor.fetchall()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/veicolo/user/<int:user_id>', methods=['POST'])
def crea_veicolo_utente(user_id):
    data = request.get_json()
    if not data or not data.get('targa'):
        return jsonify({"error": "Campo obbligatorio mancante: targa"}), 400
    conn = None
    try:
        conn = get_db_connection() # CORRETTO: avevi get_mysql_connection() che non esiste
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM Automobilista WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Utente {user_id} non trovato"}), 404
        cursor.execute(
            "INSERT INTO Veicolo (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (data.get('targa'), data.get('n_telaio'), data.get('marca'), data.get('modello'), data.get('anno_immatricolazione'), user_id)
        )
        conn.commit()
        return jsonify({"status": "success", "veicolo_id": cursor.lastrowid}), 201
    except mysql.connector.IntegrityError:
        if conn: conn.rollback()
        return jsonify({"error": "Targa o numero telaio già esistente"}), 409
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/veicoli-utente/<int:user_id>/<string:targa>', methods=['DELETE'])
def elimina_veicolo_utente(user_id, targa):
    """Elimina un veicolo specifico di un utente basandosi sulla targa"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verifichiamo se il veicolo appartiene effettivamente all'utente
        cursor.execute("SELECT id FROM Veicolo WHERE targa = %s AND automobilista_id = %s", (targa, user_id))
        if not cursor.fetchone():
            return jsonify({"error": "Veicolo non trovato o non appartenente a questo utente"}), 404
            
        # Eliminazione fisica
        cursor.execute("DELETE FROM Veicolo WHERE targa = %s AND automobilista_id = %s", (targa, user_id))
        conn.commit()
        
        return jsonify({"status": "success", "message": f"Veicolo {targa} rimosso con successo"}), 200
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    # Mantenuta porta 6000 come da tua ultima riga
    app.run(host='0.0.0.0', port=10000, debug=True)
