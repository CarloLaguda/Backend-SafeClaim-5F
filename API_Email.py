import pymongo  # Importa la libreria per interagire con MongoDB
import mysql.connector  # Importa il connettore per MySQL
from flask import Flask, request, jsonify  # Importa componenti essenziali di Flask per creare l'API
from flask_cors import CORS  # Importa CORS per gestire le richieste cross-origin
from datetime import datetime  # Importa la classe datetime per gestire date e orari
from bson.objectid import ObjectId  # Importa ObjectId per gestire ID MongoDB
import smtplib  # Importa la libreria per inviare email via SMTP
import threading  # Importa threading per eseguire operazioni in background
import urllib.parse  # Importa urllib.parse per codificare URL e password
from email.mime.text import MIMEText  # Importa MIMEText per creare messaggi email testuali
from email.mime.multipart import MIMEMultipart  # Importa MIMEMultipart per creare email multipart

# --- INIZIALIZZAZIONE ---
app = Flask(__name__)  # Crea un'istanza dell'applicazione Flask
CORS(app)  # Abilita CORS per l'app Flask

# --- CONFIGURAZIONE ---
EMAIL_CONFIG = {  # Dizionario contenente la configurazione per l'invio delle email
    "sender": "safeclaimservice@gmail.com",  # Indirizzo email del mittente
    "display_name": "SafeClaim Support",  # Nome visualizzato del mittente
    "password": "mhwpbnllgkzgruer",  # Password dell'account email (app password per Gmail)
    "smtp_server": "smtp.gmail.com",  # Server SMTP di Gmail
    "port": 465  # Porta per SMTP SSL
}

# Gestione caratteri speciali nella password MongoDB
_pw = urllib.parse.quote_plus("xxx123##")  # Codifica la password MongoDB per gestire caratteri speciali
MONGO_URI = f"mongodb+srv://dbFakeClaim:{_pw}@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"  # URI di connessione a MongoDB Atlas

MYSQL_CONFIG = {  # Dizionario contenente la configurazione per MySQL
    "host": "localhost",  # Host del database MySQL
    "user": "pythonuser",  # Nome utente per MySQL
    "password": "password123",  # Password per MySQL
    "database": "gestione_assicurazioni"  # Nome del database MySQL
}

# --- CLASSE TEMPLATE ---
class SafeClaimTemplates:  # Classe che contiene i template HTML per le email
    NEW_CLAIM_SUBJECT = "Segnalazione Nuovo Sinistro: Pratica avviata con successo"  # Oggetto dell'email per nuovo sinistro
    NEW_CLAIM_HTML = """  # Template HTML per l'email di conferma nuovo sinistro
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
                <p>ID Pratica: #{claim_id}</p>
            </div>
        </div>
    </body>
    </html>
    """

    ADMIN_NOTIFY_SUBJECT = "⚠️ Avviso: Nuova segnalazione sinistro ricevuta"  # Oggetto dell'email per notifica admin
    ADMIN_NOTIFY_HTML = """  # Template HTML per l'email di notifica agli amministratori
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #2c3e50; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">SafeClaim Admin</h1>
            </div>
            <div style="padding: 20px;">
                <h2>Nuova Pratica in Attesa</h2>
                <p>Un utente ha inviato una nuova segnalazione di sinistro.</p>
                <div style="background-color: #f1f3f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>ID Pratica:</strong> {claim_id}</p>
                    <p><strong>Targa:</strong> {targa}</p>
                    <p><strong>Descrizione:</strong> {descrizione}</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# --- CONNESSIONE DATABASES ---
try:  # Prova a connettersi a MongoDB
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)  # Crea il client MongoDB con timeout
    db = mongo_client["FakeClaim"]  # Seleziona il database FakeClaim
    sinistri_col = db['sinistri']  # Seleziona la collezione sinistri
    print("✅ MongoDB Connesso")  # Stampa messaggio di successo
except Exception as e:  # Cattura eventuali errori
    print(f"❌ Errore MongoDB: {e}")  # Stampa l'errore

def get_mysql_conn():  # Funzione per ottenere una connessione MySQL
    return mysql.connector.connect(**MYSQL_CONFIG)  # Ritorna una connessione MySQL usando la configurazione

# --- FUNZIONE CORE INVIO ---
def invia_mail_fisica(destinatario, oggetto, corpo_html):  # Funzione per inviare email fisicamente
    try:  # Prova a inviare l'email
        msg = MIMEMultipart()  # Crea un messaggio multipart
        msg['From'] = f"{EMAIL_CONFIG['display_name']} <{EMAIL_CONFIG['sender']}>"  # Imposta il mittente
        msg['To'] = destinatario  # Imposta il destinatario
        msg['Subject'] = oggetto  # Imposta l'oggetto
        msg.attach(MIMEText(corpo_html, 'html'))  # Allega il corpo HTML
        
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:  # Connessione SMTP SSL
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])  # Login al server SMTP
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())  # Invia l'email
        return True  # Ritorna True se inviato con successo
    except Exception as e:  # Cattura errori
        print(f"❌ Fallito invio a {destinatario}: {e}")  # Stampa errore
        return False  # Ritorna False se fallito

# --- LOGICA BACKGROUND ---
def gestisci_notifiche_sinistro(sinistro_id, data):  # Funzione per gestire le notifiche email in background
    conn = None  # Inizializza la connessione MySQL
    try:  # Prova a eseguire le operazioni
        conn = get_mysql_conn()  # Ottieni connessione MySQL
        cursor = conn.cursor(dictionary=True)  # Crea un cursore con risultati come dizionari
        # Email Utente
        cursor.execute("SELECT nome, email FROM Automobilista WHERE id = %s", (data['automobilista_id'],))  # Query per dati utente
        user = cursor.fetchone()  # Ottieni il primo risultato
        if user and user['email']:  # Se utente esiste e ha email
            html_u = SafeClaimTemplates.NEW_CLAIM_HTML.format(  # Formatta il template per l'utente
                user_name=user['nome'], targa=data['targa'], 
                incident_date=data['data_evento'], claim_id=sinistro_id
            )
            invia_mail_fisica(user['email'], SafeClaimTemplates.NEW_CLAIM_SUBJECT, html_u)  # Invia email all'utente
        # Email Assicuratori
        cursor.execute("SELECT email FROM Assicuratore")  # Query per email assicuratori
        for ass in cursor.fetchall():  # Per ogni assicuratore
            if ass['email']:  # Se ha email
                html_a = SafeClaimTemplates.ADMIN_NOTIFY_HTML.format(  # Formatta template admin
                    claim_id=sinistro_id, targa=data['targa'], descrizione=data['descrizione']
                )
                invia_mail_fisica(ass['email'], SafeClaimTemplates.ADMIN_NOTIFY_SUBJECT, html_a)  # Invia email admin
    finally:  # Sempre eseguito
        if conn: conn.close()  # Chiudi connessione MySQL

# --- ROTTE API ---

# 1. Rotta Automatica (Crea sinistro + manda email)
@app.route('/sinistro', methods=['POST'])  # Definisce la rotta POST per creare sinistro
def crea_sinistro():  # Funzione per creare un sinistro
    data = request.json  # Ottieni dati JSON dalla richiesta
    try:  # Prova a creare il sinistro
        nuovo_doc = {  # Crea documento per MongoDB
            "automobilista_id": data['automobilista_id'],
            "targa": data['targa'],
            "data_evento": data['data_evento'],
            "descrizione": data['descrizione'],
            "stato": "APERTO",
            "data_inserimento": datetime.now()
        }
        res = sinistri_col.insert_one(nuovo_doc)  # Inserisci in MongoDB
        s_id = str(res.inserted_id)  # Ottieni ID come stringa
        threading.Thread(target=gestisci_notifiche_sinistro, args=(s_id, data)).start()  # Avvia thread per notifiche
        return jsonify({"status": "success", "id": s_id}), 201  # Ritorna risposta di successo
    except Exception as e:  # Cattura errori
        return jsonify({"status": "error", "message": str(e)}), 500  # Ritorna errore

# 2. ROTTA MANUALE (Quella che mancava per i tuoi test su Postman)
@app.route('/invia-email-diretta', methods=['POST'])  # Definisce rotta POST per invio email diretta
def invia_email_diretta():  # Funzione per inviare email diretta
    data = request.json  # Ottieni dati JSON
    destinatario = data.get('destinatario')  # Ottieni destinatario
    oggetto = data.get('oggetto', "Notifica Manuale SafeClaim")  # Ottieni oggetto con default
    messaggio = data.get('messaggio', "Messaggio di test")  # Ottieni messaggio con default

    if not destinatario:  # Se manca destinatario
        return jsonify({"error": "Manca destinatario"}), 400  # Errore 400

    # Usiamo un corpo HTML semplice per il test manuale
    corpo_test = f"<h1>SafeClaim Test</h1><p>{messaggio}</p>"  # Crea corpo HTML semplice
    
    successo = invia_mail_fisica(destinatario, oggetto, corpo_test)  # Invia email
    
    if successo:  # Se successo
        return jsonify({"status": "success", "message": f"Email inviata a {destinatario}"}), 200  # Risposta successo
    else:  # Altrimenti
        return jsonify({"status": "error", "message": "Invio fallito, controlla il terminale"}), 500  # Errore

if __name__ == '__main__':  # Se il file è eseguito direttamente
    app.run(host='0.0.0.0', port=5000, debug=True)  # Avvia il server Flask