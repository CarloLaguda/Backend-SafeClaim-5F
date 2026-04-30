import pymongo
import mysql.connector
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from bson.objectid import ObjectId
import smtplib
import threading
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- INIZIALIZZAZIONE ---
app = Flask(__name__)
CORS(app)

# --- CONFIGURAZIONE ---
EMAIL_CONFIG = {
    "sender": "safeclaimservice@gmail.com",
    "display_name": "SafeClaim Support",
    "password": "mhwpbnllgkzgruer", 
    "smtp_server": "smtp.gmail.com",
    "port": 465
}

# Gestione sicura dei caratteri speciali nella password MongoDB (es. ##)
_pw = urllib.parse.quote_plus("xxx123##")
MONGO_URI = f"mongodb+srv://dbFakeClaim:{_pw}@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "pythonuser",
    "password": "password123",
    "database": "gestione_assicurazioni"
}

# --- CLASSE TEMPLATE (Mockup Grafici) ---
class SafeClaimTemplates:
    """Template grafici per le email del servizio SafeClaim"""
    
    # Template per l'Automobilista (Arancione)
    NEW_CLAIM_SUBJECT = "Segnalazione Nuovo Sinistro: Pratica avviata con successo"
    NEW_CLAIM_HTML = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #f39c12; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">SafeClaim - Nuovo Sinistro</h1>
            </div>
            <div style="padding: 20px;">
                <h2>Ciao {user_name},</h2>
                <p>La segnalazione del tuo nuovo sinistro è stata registrata correttamente.</p>
                <div style="background-color: #fff9f0; border-left: 4px solid #f39c12; padding: 15px; margin: 20px 0;">
                    <p><strong>Targa:</strong> {targa}</p>
                    <p><strong>Data:</strong> {incident_date}</p>
                </div>
                <p><strong>ID Pratica:</strong> #{claim_id}</p>
                <p>I nostri periti analizzeranno i dati al più presto.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Template per gli Assicuratori (Blu Scuro)
    ADMIN_NOTIFY_SUBJECT = "⚠️ Avviso: Nuova segnalazione sinistro ricevuta"
    ADMIN_NOTIFY_HTML = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #2c3e50; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">SafeClaim Admin</h1>
            </div>
            <div style="padding: 20px;">
                <h2>Nuova Pratica in Attesa</h2>
                <p>Un utente ha inviato una nuova segnalazione di sinistro nel sistema.</p>
                <div style="background-color: #f1f3f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>ID Pratica (Mongo):</strong> {claim_id}</p>
                    <p><strong>Targa:</strong> {targa}</p>
                    <p><strong>Descrizione:</strong> {descrizione}</p>
                </div>
                <p>Accedi al gestionale per assegnare un perito.</p>
            </div>
        </div>
    </body>
    </html>
    """

# --- CONNESSIONE DATABASES ---
try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client["FakeClaim"]
    sinistri_col = db['sinistri']
    mongo_client.server_info()
    print("✅ MongoDB Atlas Connesso!")
except Exception as e:
    print(f"❌ Errore MongoDB: {e}")
    sinistri_col = None

def get_mysql_conn():
    return mysql.connector.connect(**MYSQL_CONFIG)

# --- FUNZIONE CORE INVIO EMAIL ---
def invia_mail_fisica(destinatario, oggetto, corpo_html):
    """Gestisce la spedizione reale tramite SMTP"""
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
        print(f"❌ SMTP Error per {destinatario}: {e}")
        return False

# --- LOGICA NOTIFICHE IN BACKGROUND ---
def gestisci_notifiche_sinistro(sinistro_id, data):
    """Thread per recuperare email dal DB e spedire i template"""
    conn = None
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(dictionary=True)

        # 1. Email all'Automobilista
        cursor.execute("SELECT nome, email FROM Automobilista WHERE id = %s", (data['automobilista_id'],))
        user = cursor.fetchone()
        if user and user['email']:
            html_u = SafeClaimTemplates.NEW_CLAIM_HTML.format(
                user_name=user['nome'],
                targa=data['targa'],
                incident_date=data['data_evento'],
                claim_id=sinistro_id
            )
            invia_mail_fisica(user['email'], SafeClaimTemplates.NEW_CLAIM_SUBJECT, html_u)
            print(f"📧 Mail inviata all'utente: {user['email']}")

        # 2. Email a tutti gli Assicuratori
        cursor.execute("SELECT email FROM Assicuratore")
        for ass in cursor.fetchall():
            if ass['email']:
                html_a = SafeClaimTemplates.ADMIN_NOTIFY_HTML.format(
                    claim_id=sinistro_id,
                    targa=data['targa'],
                    descrizione=data['descrizione']
                )
                invia_mail_fisica(ass['email'], SafeClaimTemplates.ADMIN_NOTIFY_SUBJECT, html_a)
                print(f"📧 Notifica inviata all'assicuratore: {ass['email']}")

    except Exception as e:
        print(f"❌ Errore Thread Notifiche: {e}")
    finally:
        if conn: conn.close()

# --- ROTTE API ---

# 1. Creazione Sinistro (Salva e scatena email automatiche)
@app.route('/sinistro', methods=['POST'])
def crea_sinistro():
    if not sinistri_col:
        return jsonify({"error": "DB non disponibile"}), 500
        
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

        # Spediamo le email in un thread separato per non far aspettare Postman
        threading.Thread(target=gestisci_notifiche_sinistro, args=(s_id, data)).start()

        return jsonify({"status": "success", "id_mongo": s_id, "message": "Sinistro registrato e notifiche avviate"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 2. Invio Manuale (Solo per Test)
@app.route('/invia-email-diretta', methods=['POST'])
def invia_email_diretta():
    data = request.json
    destinatario = data.get('destinatario')
    oggetto = data.get('oggetto', "Test SafeClaim")
    messaggio = data.get('messaggio', "Questo è un test manuale.")

    if not destinatario:
        return jsonify({"error": "Destinatario mancante"}), 400

    html_test = f"<h2>SafeClaim Test System</h2><p>{messaggio}</p>"
    successo = invia_mail_fisica(destinatario, oggetto, html_test)
    
    if successo:
        return jsonify({"status": "success", "message": f"Email inviata a {destinatario}"}), 200
    else:
        return jsonify({"status": "error", "message": "Invio fallito"}), 500

# AVVIO
if __name__ == '__main__':
    # Ricordati: pip install mysql-connector-python pymongo flask flask-cors
    app.run(host='0.0.0.0', port=5000, debug=True)