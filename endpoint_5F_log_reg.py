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

db_config = {
    "host": "localhost",
    "user": "pythonuser",
    "password": "password123",
    "database": "gestione_assicurazioni"
}

MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123%23%23@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client['FakeClaim']
    mongo_client.admin.command('ping')
    print("✅ Connessione a MongoDB Atlas riuscita!")
except Exception as e:
    print(f"❌ Errore critico connessione MongoDB: {e}")

def get_mysql_connection():
    return mysql.connector.connect(**db_config)

# --- TABELLE AMMESSE PER RUOLO ---
TABELLE_PER_RUOLO = {
    "automobilista": "Automobilista",
    "perito": "Perito",
    "assicuratore": "Assicuratore",
}

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

def valida_dati_aggiornamento(data):
    """Validazione leggera per UPDATE: non richiede psw, serve solo per campi modificabili."""
    pattern_nomi = r"^[a-zA-Zàáâäãåèéêëìíîïòóôöùúûüç \s']+$"
    if 'nome' in data and not re.match(pattern_nomi, data.get('nome', '')):
        return False, "Il nome non è valido."
    if 'cognome' in data and not re.match(pattern_nomi, data.get('cognome', '')):
        return False, "Il cognome non è valido."
    if 'email' in data and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data.get('email', '')):
        return False, "Formato email non valido."
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
    if not email_in or not psw_in:
        return jsonify({"error": "Credenziali mancanti"}), 400
    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        tabelle = ["Assicuratore", "Automobilista", "Perito"]
        for tabella in tabelle:
            # 🆕 Ora la SELECT include anche cf per poterlo mostrare in sidebar
            cursor.execute(
                f"SELECT id, nome, cognome, cf, email FROM {tabella} WHERE email = %s AND psw = %s",
                (email_in, psw_in)
            )
            user_found = cursor.fetchone()
            if user_found:
                user_found['ruolo'] = tabella.lower()
                return jsonify({"status": "success", "user": user_found}), 200
        return jsonify({"error": "Credenziali non valide"}), 401
    finally:
        if conn: conn.close()

# --- 🆕 AGGIORNAMENTO PROFILO ---

@app.route('/utente/<int:user_id>', methods=['PUT'])
def aggiorna_utente(user_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    ruolo = (data.get('ruolo') or '').lower()
    if ruolo not in TABELLE_PER_RUOLO:
        return jsonify({"error": "Ruolo non valido"}), 400

    tabella = TABELLE_PER_RUOLO[ruolo]

    # Solo campi aggiornabili ammessi
    campi_ammessi = {'nome', 'cognome', 'email'}
    payload = {k: v for k, v in data.items() if k in campi_ammessi and v is not None}

    if not payload:
        return jsonify({"error": "Nessun campo valido da aggiornare"}), 400

    is_valid, err = valida_dati_aggiornamento(payload)
    if not is_valid:
        return jsonify({"error": err}), 400

    # Normalizzazione valori
    if 'nome' in payload: payload['nome'] = payload['nome'].strip().title()
    if 'cognome' in payload: payload['cognome'] = payload['cognome'].strip().title()
    if 'email' in payload: payload['email'] = payload['email'].strip().lower()

    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        # Costruzione dinamica della SET clause
        set_clause = ", ".join([f"{col} = %s" for col in payload.keys()])
        values = list(payload.values()) + [user_id]

        cursor.execute(f"UPDATE {tabella} SET {set_clause} WHERE id = %s", values)

        if cursor.rowcount == 0:
            return jsonify({"error": "Utente non trovato"}), 404

        conn.commit()

        # Ritorna l'utente aggiornato
        cursor.execute(
            f"SELECT id, nome, cognome, cf, email FROM {tabella} WHERE id = %s",
            (user_id,)
        )
        user_updated = cursor.fetchone()
        if user_updated:
            user_updated['ruolo'] = ruolo

        return jsonify({"status": "success", "user": user_updated}), 200

    except mysql.connector.IntegrityError:
        return jsonify({"error": "Email già in uso da un altro utente"}), 409
    except mysql.connector.Error as e:
        return jsonify({"error": f"Errore database: {str(e)}"}), 500
    finally:
        if conn: conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)