# LIBRERIE DATABASE
import pymongo                             # Driver MongoDB per database NoSQL
import mysql.connector                     # Driver MySQL/MariaDB per connessione SQL
from mysql.connector import Error          # Classe eccezione errori MySQL

# LIBRERIE WEB
from flask import Flask, request, jsonify  # Server web Flask e utilità JSON/http
from flask_cors import CORS                # Abilita richieste Cross-Origin dal frontend

# LIBRERIE DATA/TEMPO
from datetime import datetime              # Gestione date e timestamp
from bson.objectid import ObjectId         # Gestione ObjectId MongoDB 

# LIBRERIE EMAIL
import smtplib                             # Interfaccia SMTP per inviare email
import urllib.parse                        # Codifica URL per password speciali
from email.mime.text import MIMEText       # Corpo email HTML in MIME
from email.mime.multipart import MIMEMultipart # Messaggi email con più parti

# LIBRERIE THREADING
import threading                           # Esecuzione di attività in background

# SEZIONE 1: INIZIALIZZAZIONE
app = Flask(__name__)                      # Crea applicazione Flask
CORS(app)                                  # Abilita CORS per chiamate da browser

# SEZIONE 2: CONFIGURAZIONE EMAIL SMTP
EMAIL_CONFIG = {
    "sender": "safeclaimservice@gmail.com",  # Mittente email
    "display_name": "SafeClaim Support",     # Nome visualizzato nel campo From
    "password": "mhwpbnllgkzgruer",          # Password SMTP Gmail 
    "smtp_server": "smtp.gmail.com",         # Server SMTP Gmail
    "port": 465                               # Porta SSL/TLS per Gmail
}

# SEZIONE 3: CONFIGURAZIONE MONGODB ATLAS
_pw = urllib.parse.quote_plus("xxx123##")     # Codifica la password in URL-safe
MONGO_URI = f"mongodb+srv://dbFakeClaim:{_pw}@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"  # URI di connessione MongoDB

# SEZIONE 4: CONFIGURAZIONE MARIADB / MYSQL
MYSQL_CONFIG = {
    "host": "127.0.0.1",                   # Host MySQL locale (IP consigliato)
    "user": "pythonuser",                  # Utente MySQL
    "password": "password123",             # Password MySQL
    "database": "gestione_assicurazioni",  # Database usato per i dati assicurativi
    "port": 3306                             # Porta MySQL standard
}

# SEZIONE 5: TEMPLATE EMAIL
class SafeClaimTemplates:
    # Oggetto email inviato all'automobilista
    NEW_CLAIM_SUBJECT = "Segnalazione Nuovo Sinistro: Pratica avviata"

    # Corpo HTML email per l'automobilista
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

    # Oggetto email inviato agli assicuratori
    ADMIN_NOTIFY_SUBJECT = " Avviso: Nuova segnalazione sinistro"

    # Corpo HTML email per gli assicuratori
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

# SEZIONE 6: CONNESSIONE MONGODB
try:
    # Crea il client MongoDB usando l'URI configurato
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client["FakeClaim"]               # Seleziona il database FakeClaim
    sinistri_col = db['sinistri']                # Seleziona la collezione sinistri
    mongo_client.server_info()                    # Forza un controllo immediato di connessione
    print(" MongoDB Atlas Connesso!")            # Log di successo
except Exception as e:
    print(f" Errore MongoDB: {e}")              # Log errore di connessione MongoDB
    sinistri_col = None                           # Setta a None se non disponibile

# Funzione helper per aprire una connessione MySQL/MariaDB
def get_mysql_conn():
    """Ritorna una nuova connessione MySQL usando MYSQL_CONFIG"""
    return mysql.connector.connect(**MYSQL_CONFIG)  # Usa la configurazione definita sopra

# SEZIONE 7: FUNZIONE INVIO EMAIL
def invia_mail_fisica(destinatario, oggetto, corpo_html):
    """Invia un'email HTML tramite SMTP e ritorna True/False."""
    try:
        msg = MIMEMultipart()                                                      # Crea messaggio MIME multipart
        msg['From'] = f"{EMAIL_CONFIG['display_name']} <{EMAIL_CONFIG['sender']}>"  # Imposta mittente
        msg['To'] = destinatario                                                   # Imposta destinatario
        msg['Subject'] = oggetto                                                   # Imposta oggetto email
        msg.attach(MIMEText(corpo_html, 'html'))                                  # Aggiunge il corpo HTML
        
        # Connessione sicura SMTP con SSL
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])       # Login SMTP
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())  # Invia email
        return True                                                                # Invio riuscito
    except Exception as e:
        print(f" SMTP Error: {e}")                                            # Log errore SMTP
        return False                                                               # Invio fallito

# SEZIONE 8: THREAD NOTIFICHE
def gestisci_notifiche_sinistro(sinistro_id, data):
    """Esegue l'invio delle email in background usando una connessione MySQL separata."""
    conn = None                                                                 # Connessione MySQL inizio nulla
    try:
        conn = get_mysql_conn()                                                  # Apre connessione MySQL
        cursor = conn.cursor(dictionary=True)                                   # Cursore con risultati come dizionari perche usiamo nomi di colonna

        # Email Utente
        cursor.execute("SELECT nome, email FROM Automobilista WHERE id = %s", (data['automobilista_id'],))  # Query utente
        user = cursor.fetchone()                                                 # Prende il primo risultato
        if user and user['email']:                                               # Se utente valido e ha email
            html_u = SafeClaimTemplates.NEW_CLAIM_HTML.format(
                user_name=user['nome'],                                          # Nome utente
                targa=data['targa'],                                             # Targa del veicolo
                incident_date=data['data_evento'],                              # Data evento
                claim_id=sinistro_id                                           # ID sinistro MongoDB
            )
            invia_mail_fisica(user['email'], SafeClaimTemplates.NEW_CLAIM_SUBJECT, html_u)  # Invia email cliente
            print(f" Mail inviata all'utente: {user['email']}")              # Log invio utente

        # Email Assicuratori
        cursor.execute("SELECT email FROM Assicuratore")                       # Query email assicuratori
        for ass in cursor.fetchall():                                           # Itera su ogni riga di risultato
            if ass['email']:                                                     # Se l'assicuratore ha email
                html_a = SafeClaimTemplates.ADMIN_NOTIFY_HTML.format(
                    claim_id=sinistro_id,                                      # ID pratica
                    targa=data['targa'],                                       # Targa
                    descrizione=data['descrizione']                            # Descrizione del sinistro
                )
                invia_mail_fisica(ass['email'], SafeClaimTemplates.ADMIN_NOTIFY_SUBJECT, html_a)  # Invia email agli assicuratori
                print(f" Notifica inviata all'assicuratore: {ass['email']}")  # Log invio assicuratore

    except Exception as e:
        print(f"❌ Errore Database/Notifiche: {e}")                            # Log errore thread notifiche
    finally:
        if conn and conn.is_connected():                                        # Se connessione ancora aperta
            conn.close()                                                       # Chiudi connessione MySQL

# SEZIONE 9: ENDPOINTS
@app.route('/sinistro', methods=['POST'])
def crea_sinistro():
    # Controlla che MongoDB sia connesso prima di proseguire
    if sinistri_col is None:
        return jsonify({"error": "Database MongoDB non connesso"}), 500
    
    data = request.json  # Estrae il JSON inviato dal client
    try:
        nuovo_doc = {
            "automobilista_id": data['automobilista_id'],  # ID dell'automobilista
            "targa": data['targa'],                        # Targa del veicolo
            "data_evento": data['data_evento'],            # Data dell'incidente
            "descrizione": data['descrizione'],            # Dettagli sinistro
            "stato": "APERTO",                             # Stato iniziale pratica
            "data_inserimento": datetime.now()             # Timestamp della creazione
        }
        res = sinistri_col.insert_one(nuovo_doc)           # Salva il documento su MongoDB
        s_id = str(res.inserted_id)                        # Converte ObjectId in stringa

        # Avvia un thread in background per inviare le email senza bloccare la risposta
        threading.Thread(target=gestisci_notifiche_sinistro, args=(s_id, data)).start()

        return jsonify({
            "status": "success",
            "id_mongo": s_id,
            "message": "Sinistro registrato e notifiche avviate"
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Avvio dell'applicazione solo se il file è eseguito direttamente
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # Avvia server Flask sulla porta 5000