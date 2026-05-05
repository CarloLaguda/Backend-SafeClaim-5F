from flask import Flask, request, jsonify
import mysql.connector
import re
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from flask_cors import CORS
from dotenv import load_dotenv
import os

app = Flask(__name__)
CORS(app)

# ── Configurazione MySQL ────────────────────────────────────────────────────
load_dotenv()

MYSQL_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
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
    return mysql.connector.connect(**MYSQL_CONFIG)

TABELLA_PER_RUOLO = {
    "automobilista": "Automobilista",
    "perito":        "Perito",
    "assicuratore":  "Assicuratore",
}

# ── Helper ───────────────────────────────────────────────────────────────────
def serializza_utente(user):
    """Converte i tipi non serializzabili in JSON (es. set MySQL → str)."""
    if user and isinstance(user.get('ruolo'), set):
        user['ruolo'] = ','.join(user['ruolo'])
    return user

# ── Validazioni ─────────────────────────────────────────────────────────────
def valida_password(password):
    if len(password) < 8:
        return False, "La password deve essere lunga almeno 8 caratteri."
    if not re.search(r"[a-zA-Z]", password):
        return False, "La password deve contenere almeno una lettera."
    if not re.search(r"\d", password):
        return False, "La password deve contenere almeno un numero."
    return True, None

def valida_cf(cf):
    cf = cf.strip().upper()
    if len(cf) != 16:
        return False, "Il codice fiscale deve essere di esattamente 16 caratteri."
    if not re.match(r'^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$', cf):
        return False, "Il codice fiscale non è nel formato corretto."
    return True, None

def valida_email(email):
    email = email.strip()
    if '@' not in email:
        return False, "L'email deve contenere il simbolo @."
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False, "Formato email non valido."
    return True, None

def valida_dati_utente(data):
    pattern_nomi = r"^[a-zA-Zàáâäãåèéêëìíîïòóôöùúûüç \s']+$"
    if not re.match(pattern_nomi, data.get('nome', '')):
        return False, "Il nome non è valido."
    if not re.match(pattern_nomi, data.get('cognome', '')):
        return False, "Il cognome non è valido."
    cf_valido, cf_err = valida_cf(data.get('cf', ''))
    if not cf_valido:
        return False, cf_err
    email_valida, email_err = valida_email(data.get('email', ''))
    if not email_valida:
        return False, email_err
    valida_psw, err_psw = valida_password(data.get('password_hash', ''))
    if not valida_psw:
        return False, err_psw
    return True, None

def valida_dati_aggiornamento(data):
    pattern_nomi = r"^[a-zA-Zàáâäãåèéêëìíîïòóôöùúûüç \s']+$"
    if 'nome' in data and not re.match(pattern_nomi, data.get('nome', '')):
        return False, "Il nome non è valido."
    if 'cognome' in data and not re.match(pattern_nomi, data.get('cognome', '')):
        return False, "Il cognome non è valido."
    if 'email' in data:
        email_valida, email_err = valida_email(data.get('email', ''))
        if not email_valida:
            return False, email_err
    return True, None

# ── Registrazione ────────────────────────────────────────────────────────────
# Aperta solo agli automobilisti. Periti, assicuratori e altri ruoli
# vengono creati dall'admin tramite endpoint dedicati.
@app.route('/registrazione', methods=['POST'])
def registrazione():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    ruolo = data.get('ruolo', 'automobilista').lower()
    if ruolo != 'automobilista':
        return jsonify({"error": "La registrazione pubblica è riservata agli automobilisti. Contatta l'amministratore."}), 403

    is_valid, error_message = valida_dati_utente(data)
    if not is_valid:
        return jsonify({"error": error_message}), 400

    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO Utente (nome, cognome, email, telefono, password_hash, ruolo) VALUES (%s,%s,%s,%s,%s,%s)",
            (
                data['nome'].strip().title(),
                data['cognome'].strip().title(),
                data['email'].strip().lower(),
                data.get('telefono'),
                data['password_hash'],
                'automobilista',
            )
        )
        utente_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO Automobilista (nome, cognome, cf, id_utente) VALUES (%s,%s,%s,%s)",
            (
                data['nome'].strip().title(),
                data['cognome'].strip().title(),
                data['cf'].strip().upper(),
                utente_id,
            )
        )

        conn.commit()
        return jsonify({"status": "success", "id_utente": utente_id}), 201

    except mysql.connector.IntegrityError:
        if conn:
            conn.rollback()
        return jsonify({"error": "Email o CF già registrati"}), 409
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# ── Login ────────────────────────────────────────────────────────────────────
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email_in = data.get('email')
    psw_in   = data.get('password_hash')
    if not email_in or not psw_in:
        return jsonify({"error": "Credenziali mancanti"}), 400

    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, nome, cognome, email, telefono, ruolo FROM Utente WHERE email = %s AND password_hash = %s",
            (email_in.strip().lower(), psw_in)
        )
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Credenziali non valide"}), 401
        return jsonify({"status": "success", "user": serializza_utente(user)}), 200
    finally:
        if conn:
            conn.close()

# ── Aggiornamento profilo ────────────────────────────────────────────────────
@app.route('/utente/<int:user_id>', methods=['PUT'])
def aggiorna_utente(user_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    campi_utente   = {'nome', 'cognome', 'email', 'telefono'}
    payload_utente = {k: v for k, v in data.items() if k in campi_utente and v is not None}

    if not payload_utente:
        return jsonify({"error": "Nessun campo valido da aggiornare"}), 400

    is_valid, err = valida_dati_aggiornamento(payload_utente)
    if not is_valid:
        return jsonify({"error": err}), 400

    if 'nome'    in payload_utente: payload_utente['nome']    = payload_utente['nome'].strip().title()
    if 'cognome' in payload_utente: payload_utente['cognome'] = payload_utente['cognome'].strip().title()
    if 'email'   in payload_utente: payload_utente['email']   = payload_utente['email'].strip().lower()

    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        set_clause = ", ".join([f"{col} = %s" for col in payload_utente.keys()])
        values = list(payload_utente.values()) + [user_id]
        cursor.execute(f"UPDATE Utente SET {set_clause} WHERE id = %s", values)

        if cursor.rowcount == 0:
            return jsonify({"error": "Utente non trovato"}), 404

        conn.commit()

        cursor.execute(
            "SELECT id, nome, cognome, email, telefono, ruolo FROM Utente WHERE id = %s",
            (user_id,)
        )
        user_updated = cursor.fetchone()
        return jsonify({"status": "success", "user": serializza_utente(user_updated)}), 200

    except mysql.connector.IntegrityError:
        return jsonify({"error": "Email già in uso da un altro utente"}), 409
    except mysql.connector.Error as e:
        return jsonify({"error": f"Errore database: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)