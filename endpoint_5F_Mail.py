# ==========================================
# SEZIONE IMPORTAZIONI LIBRERIE
# ==========================================

# LIBRERIE DATABASE
import pymongo                             # Connessione a database NoSQL MongoDB
import mysql.connector                     # MySQL/MariaDB - gestisce connessioni SQL
from mysql.connector import Error          # Gestione eccezioni specifiche MySQL

# LIBRERIE WEB E SERVER
from flask import Flask, request, jsonify  # Flask server, gestione HTTP e JSON
from flask_cors import CORS                # Abilita richieste cross-origin (frontend)

# LIBRERIE PER DATA/TEMPO E OGGETTI
from datetime import datetime              # Gestione timestamp
from bson.objectid import ObjectId         # Gestione ID MongoDB

# LIBRERIE PER GESTIONE EMAIL
import smtplib                             # Protocollo per invio email
import urllib.parse                        # Codifica URL-safe per password
from email.mime.text import MIMEText       # Corpo email HTML
from email.mime.multipart import MIMEMultipart # Email multipart

# LIBRERIE PER THREADING
import threading                           # Esecuzione asincrona (non blocca il server)

# ==========================================
# SEZIONE 1: INIZIALIZZAZIONE
# ==========================================
app = Flask(__name__)
CORS(app)

# ==========================================
# SEZIONE 2: CONFIGURAZIONE EMAIL SMTP
# ==========================================
EMAIL_CONFIG = {
    "sender": "safeclaimservice@gmail.com",
    "display_name": "SafeClaim Support",
    "password": "mhwpbnllgkzgruer",         # Password app Gmail
    "smtp_server": "smtp.gmail.com",
    "port": 465
}

# ==========================================
# SEZIONE 3: CONFIGURAZIONE MONGODB ATLAS
# ==========================================
_pw = urllib.parse.quote_plus("xxx123##") 
MONGO_URI = f"mongodb+srv://dbFakeClaim:{_pw}@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"

# ==========================================
# SEZIONE 4: CONFIGURAZIONE MARIADB / MYSQL
# ==========================================
MYSQL_CONFIG = {
    "host": "127.0.0.1",                  # Localhost per Codespaces
    "user": "pythonuser",
    "password": "password123",
    "database": "gestione_assicurazioni",
    "port": 3306
}

# ==========================================
# SEZIONE 5: TEMPLATE EMAIL HTML
# ==========================================
class SafeClaimTemplates:
    NEW_CLAIM_SUBJECT = "Segnalazione Nuovo Sinistro: Pratica avviata"
    NEW_CLAIM_HTML = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #f39c12; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">SafeClaim - Nuovo Sinistro</h1>
            </div>
            <div style="padding: 20px;">
                <h2>Ciao {user_name},</h2>
                <p>La segnalazione è stata registrata correttamente.</p>
                <p><strong>Targa:</strong> {targa}<br><strong>Data:</strong> {incident_date}</p>
                <p><strong>ID Pratica:</strong> #{claim_id}</p>
            </div>
        </div>
    </body>
    </html>
    """
    ADMIN_NOTIFY_SUBJECT = "⚠️ Avviso: Nuova segnalazione sinistro"
    ADMIN_NOTIFY_HTML = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #2c3e50; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">SafeClaim Admin</h1>
            </div>
            <div style="padding: 20px;">
                <h2>Nuova Pratica Ricevuta</h2>
                <p><strong>ID Mongo:</strong> {claim_id}<br><strong>Targa:</strong> {targa}</p>
                <p><strong>Descrizione:</strong> {descrizione}</p>
            </div>
        </div>
    </body>
    </html>
    """

# ==========================================
# SEZIONE 6: CONNESSIONE MONGODB
# ==========================================
try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client["FakeClaim"]
    sinistri_col = db['sinistri']
    mongo_client.server_info()
    print("✅ MongoDB Atlas Connesso!")
except Exception as e:
    print(f"❌ Errore MongoDB: {e}")
    sinistri_col = None

# ==========================================
# SEZIONE 7: HELPER MYSQL
# ==========================================
def get_mysql_conn():
    return mysql.connector.connect(**MYSQL_CONFIG)

# ==========================================
# SEZIONE 8: FUNZIONE INVIO EMAIL
# ==========================================
def invia_mail_fisica(destinatario, oggetto, corpo_html):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{EMAIL_CONFIG['display_name']} <{EMAIL_CONFIG['sender']}>"
        msg['To'] = destinatario
        msg['Subject'] = oggetto
        msg.attach(MIMEText(corpo_html, 'html'))
        
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())
        return True
    except Exception as e:
        print(f"❌ SMTP Error: {e}")
        return False

# ==========================================
# SEZIONE 9: THREAD NOTIFICHE
# ==========================================
def gestisci_notifiche_sinistro(sinistro_id, data):
    conn = None
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(dictionary=True)

        # Email Utente
        cursor.execute("SELECT nome, email FROM Automobilista WHERE id = %s", (data['automobilista_id'],))
        user = cursor.fetchone()
        if user and user['email']:
            html_u = SafeClaimTemplates.NEW_CLAIM_HTML.format(
                user_name=user['nome'], targa=data['targa'],
                incident_date=data['data_evento'], claim_id=sinistro_id
            )
            invia_mail_fisica(user['email'], SafeClaimTemplates.NEW_CLAIM_SUBJECT, html_u)
            print(f"📧 Mail inviata all'utente: {user['email']}")

        # Email Assicuratori
        cursor.execute("SELECT email FROM Assicuratore")
        for ass in cursor.fetchall():
            if ass['email']:
                html_a = SafeClaimTemplates.ADMIN_NOTIFY_HTML.format(
                    claim_id=sinistro_id, targa=data['targa'], descrizione=data['descrizione']
                )
                invia_mail_fisica(ass['email'], SafeClaimTemplates.ADMIN_NOTIFY_SUBJECT, html_a)
                print(f"📧 Notifica inviata all'assicuratore: {ass['email']}")

    except Exception as e:
        print(f"❌ Errore Database/Notifiche: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()

# ==========================================
# SEZIONE 10: ENDPOINTS FLASK
# ==========================================

# 1. Endpoint Creazione Sinistro (Automatico)
@app.route('/sinistro', methods=['POST'])
def crea_sinistro():
    if sinistri_col is None: # Corretto per evitare NotImplementedError
        return jsonify({"error": "Database MongoDB non connesso"}), 500
    
    data = request.json
    try:
        nuovo_doc = {
            "automobilista_id": data['automobilista_id'],
            "targa": data['targa'],
            "data_evento": data['data_evento'],
            "descrizione": data['descrizione'],
            "stato": "APERTO",
            "data_inserimento": datetime.now()
        }
        res = sinistri_col.insert_one(nuovo_doc)
        s_id = str(res.inserted_id)

        # Avvio notifiche in background
        threading.Thread(target=gestisci_notifiche_sinistro, args=(s_id, data)).start()

        return jsonify({
            "status": "success",
            "id_mongo": s_id,
            "message": "Sinistro registrato e notifiche avviate"
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 2. Endpoint Invio Email Manuale (Richiesto)
@app.route('/invia-email', methods=['POST'])
def rotta_invia_email_manuale():
    data = request.json
    if not data or 'destinatario' not in data or 'oggetto' not in data or 'messaggio' not in data:
        return jsonify({"status": "error", "message": "Campi mancanti"}), 400

    try:
        threading.Thread(
            target=invia_mail_fisica, 
            args=(data['destinatario'], data['oggetto'], data['messaggio'])
        ).start()
        return jsonify({"status": "success", "message": f"Invio avviato verso {data['destinatario']}"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# SEZIONE 11: AVVIO
# ==========================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=11000, debug=True)