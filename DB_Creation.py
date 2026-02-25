import mysql.connector
from pymongo import MongoClient
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================================
# CONFIGURAZIONE EMAIL (GMAIL SMTP)
# ============================================================
EMAIL_CONFIG = {
    "sender": "mattioni.tommaso@iisgalvanimi.edu.it",
    # IMPORTANTE: La "Password per le app" va scritta SENZA SPAZI.
    # Google la mostra come "elcg kjhb vqjk lost", ma qui deve essere "elcgkjhbvqjklost"
    "password": "elcgkjhbvqjklost", 
    "smtp_server": "smtp.gmail.com",
    "port": 465 # Utilizziamo la porta 465 per una connessione SSL sicura
}

# ============================================================
# CONFIGURAZIONE DATABASE (MySQL & MongoDB)
# ============================================================
MYSQL_CONFIG = {
    "host": "mysql-safeclaim.aevorastudios.com",
    "port": 3306,
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db"
}

MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
MONGO_DB_NAME = "safeclaim_mongo"

# ============================================================
# FUNZIONE PER INVIO EMAIL (Task 9.2 - Implementazione Mihali)
# ============================================================
def invia_email(destinatario, oggetto, corpo):
    """
    Gestisce l'autenticazione SMTP e l'invio fisico dell'email.
    """
    try:
        # Creazione del contenitore MIME per il messaggio
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG["sender"]
        msg['To'] = destinatario
        msg['Subject'] = oggetto
        msg.attach(MIMEText(corpo, 'plain'))

        # Apertura connessione sicura con il server Gmail
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:
            # Login: qui il server verifica mittente e password per le app
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            # Invio effettivo del messaggio
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())
        
        print(f"📧 Email inviata con successo a {destinatario}")
        return True
    except Exception as e:
        # Se ricevi l'errore 535, la password è sbagliata o contiene spazi
        print(f"❌ Errore durante l'invio dell'email: {e}")
        return False

# ============================================================
# LOGICA DI ESECUZIONE (Test Sistema)
# ============================================================
mydb = None
mongo_client = None

try:
    print("--- 🔍 Inizio Test Sistema SafeClaim ---")

    # --- Test Connessione MySQL ---
    try:
        mydb = mysql.connector.connect(**MYSQL_CONFIG)
        print("✅ MySQL: Connesso")
    except:
        # Gestiamo il fallimento del DB per procedere con il test SMTP
        print("⚠️ MySQL: Connessione fallita (Saltato)")

    # --- Test Connessione MongoDB ---
    try:
        mongo_client = MongoClient(MONGO_URI)
        mongo_client.admin.command('ping')
        print("✅ MongoDB: Connesso")
    except:
        print("⚠️ MongoDB: Connessione fallita (Saltato)")

    # --- ESECUZIONE TASK 9.2: INVIO MAIL ---
    print("\n🚀 Avvio invio notifica automatica...")
    
    # Eseguiamo il test finale dell'integrazione SMTP
    successo = invia_email(
        destinatario="mihali.sebastian@iisgalvanimi.edu.it",
        oggetto="SafeClaim - Task 9.2 Completato",
        corpo="Integrazione server SMTP riuscita. Il sistema di notifiche è operativo."
    )

    if successo:
        print("\n🏆 TEST FINALE: Integrazione SMTP verificata con successo!")
    else:
        print("\n⚠️ TEST FINALE: Errore")

except Exception as e:
    print(f"❌ Errore imprevisto: {e}")

finally:
    # Chiusura sicura delle risorse per evitare sprechi di memoria
    if mydb and mydb.is_connected(): mydb.close()
    if mongo_client: mongo_client.close()
    print("\n🔒 Test terminato. Risorse chiuse.")