import mysql.connector
from pymongo import MongoClient
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =========================
# CONFIGURAZIONE EMAIL (GMAIL SMTP)
# =========================
EMAIL_CONFIG = {
    "sender": "mattioni.tommaso@iisgalvanimi.edu.it",
    "password": "elcg kjhb vqjk lost", # Quella generata nel video
    "smtp_server": "smtp.gmail.com",
    "port": 465 # Usiamo SSL per sicurezza
}

# =========================
# CONFIGURAZIONE MYSQL & MONGO (Invariate)
# =========================
MYSQL_CONFIG = {
    "host": "mysql-safeclaim.aevorastudios.com",
    "port": 3306,
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db"
}

MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
MONGO_DB_NAME = "safeclaim_mongo"

# =========================
# FUNZIONE PER INVIO EMAIL
# =========================
def invia_email(destinatario, oggetto, corpo):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG["sender"]
        msg['To'] = destinatario
        msg['Subject'] = oggetto

        msg.attach(MIMEText(corpo, 'plain'))

        # Connessione sicura tramite SSL
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())
        
        print(f"📧 Email inviata con successo a {destinatario}")
        return True
    except Exception as e:
        print(f"❌ Errore invio email: {e}")
        return False

# =========================
# LOGICA PRINCIPALE
# =========================
try:
    # --- Connessione MySQL ---
    mydb = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = mydb.cursor()
    print("✅ MySQL: Connesso")

    # --- Connessione MongoDB ---
    mongo_client = MongoClient(MONGO_URI)
    mongo_db = mongo_client[MONGO_DB_NAME]
    mongo_client.admin.command('ping')
    print("✅ MongoDB: Connesso")

    # --- Esempio di utilizzo integrato ---
    # Supponiamo di inserire un record e voler notificare l'utente
    test_doc = {"tipo": "polizza_pdf", "descrizione": "Documento di test", "data": "2026-02-11"}
    inserted = mongo_db["polizze_documenti"].insert_one(test_doc)
    
    if inserted.inserted_id:
        print(f"📄 Documento salvato: {inserted.inserted_id}")
        
        # INVIO EMAIL DI CONFERMA
        invia_email(
            destinatario="destinatario-test@esempio.com",
            oggetto="Nuova Polizza Caricata - SafeClaim",
            corpo=f"Ciao! Abbiamo ricevuto il tuo documento.\nID Pratica: {inserted.inserted_id}"
        )

except Exception as e:
    print(f"❌ Errore: {e}")

finally:
    if 'cursor' in locals(): cursor.close()
    if 'mydb' in locals() and mydb.is_connected(): mydb.close()
    if 'mongo_client' in locals(): mongo_client.close()
    print("🔒 Risorse chiuse.")