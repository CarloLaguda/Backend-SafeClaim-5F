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

# Credenziali MySQL fornite
db_config = {
    "host": "localhost",
    "user": "pythonuser",
    "password": "password123",
    "database": "gestione_assicurazioni"
}

# Configurazione MongoDB Atlas
MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123%23%23@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client['FakeClaim']
    sinistri_col = mongo_db['Sinistro']
    mongo_client.admin.command('ping')
    print("✅ Connessione a MongoDB Atlas riuscita!")
except Exception as e:
    print(f"❌ Errore critico connessione MongoDB: {e}")

def get_mysql_connection():
    """Ritorna la connessione al database locale gestione_assicurazioni"""
    return mysql.connector.connect(**db_config)

# --- UTILITY VALIDAZIONE ---
def valida_password(password):
    if len(password) < 8: return False, "La password deve essere lunga almeno 8 caratteri."
    if not re.search(r"[a-zA-Z]", password): return False, "La password deve contenere almeno una lettera."
    if not re.search(r"\d", password): return False, "La password deve contenere almeno un numero."
    return True, None

def valida_dati_utente(data):
    pattern_nomi = r"^[a-zA-Zàáâäãåèéêëìíîïòóôöùúûüç \s']+$"
    if not re.match(pattern_nomi, data.get('nome', '')): return False, "Il nome non è valido."
    if not re.match(pattern_nomi, data.get('cognome', '')): return False, "Il cognome non è valido."
    if not re.match(r'^[A-Z0-9]{16}$', data.get('cf', '').upper()): return False, "Il CF deve essere di 16 caratteri alfanumerici."
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data.get('email', '')): return False, "Formato email non valido."
    valida_psw, err_psw = valida_password(data.get('psw', ''))
    if not valida_psw: return False, err_psw
    return True, None

# --- REGISTRAZIONE & LOGIN ---

@app.route('/registrazione', methods=['POST'])
def registrazione():
    data = request.get_json()
    if not data: return jsonify({"error": "Nessun dato ricevuto"}), 400
    is_valid, error_message = valida_dati_utente(data)
    if not is_valid: return jsonify({"error": error_message}), 400
    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        query = "INSERT INTO Automobilista (nome, cognome, cf, email, psw) VALUES (%s, %s, %s, %s, %s)"
        values = (data['nome'].strip().title(), data['cognome'].strip().title(), 
                  data['cf'].strip().upper(), data['email'].strip().lower(), data['psw'])
        cursor.execute(query, values)
        conn.commit()
        return jsonify({"status": "success", "id": cursor.lastrowid}), 201
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Email o CF già registrati"}), 409
    finally:
        if conn: conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email_in, psw_in = data.get('email'), data.get('psw')
    if not email_in or not psw_in: return jsonify({"error": "Credenziali mancanti"}), 400
    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        tabelle = ["Assicuratore", "Automobilista", "Perito"]
        for tabella in tabelle:
            cursor.execute(f"SELECT id, nome, cognome, email FROM {tabella} WHERE email = %s AND psw = %s", (email_in, psw_in))
            user_found = cursor.fetchone()
            if user_found:
                user_found['ruolo'] = tabella.lower()
                return jsonify({"status": "success", "user": user_found}), 200
        return jsonify({"error": "Credenziali non valide"}), 401
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)