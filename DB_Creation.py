import mysql.connector  # Importa libreria per connessione MySQL
from pymongo import MongoClient  # Importa client MongoDB
import smtplib  # Libreria per invio email via SMTP
from email.mime.text import MIMEText  # Per creare corpo email testo
from email.mime.multipart import MIMEMultipart  # Per email multipart (testo, allegati)

# ============================================================
# CONFIGURAZIONE EMAIL (GMAIL SMTP)
# ============================================================
EMAIL_CONFIG = {  # Dizionario configurazione email Gmail
    "sender": "mattioni.tommaso@iisgalvanimi.edu.it",  # Mittente email
    # IMPORTANTE: La "Password per le app" va scritta SENZA SPAZI.
    # Google la mostra come "elcg kjhb vqjk lost", ma qui deve essere "elcgkjhbvqjklost"
    "password": "elcgkjhbvqjklost",  # Password app Gmail (senza spazi)
    "smtp_server": "smtp.gmail.com",  # Server SMTP Gmail
    "port": 465  # Porta SSL per connessione sicura
}

# ============================================================
# CONFIGURAZIONE DATABASE (MySQL & MongoDB)
# ============================================================
MYSQL_CONFIG = {  # Configurazione connessione MySQL
    "host": "mysql-safeclaim.aevorastudios.com",  # Host server MySQL
    "port": 3306,  # Porta MySQL standard
    "user": "safeclaim",  # Username database
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",  # Password database
    "database": "safeclaim_db"  # Nome database
}

MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"  # URI connessione MongoDB (include credenziali)
MONGO_DB_NAME = "safeclaim_mongo"  # Nome database MongoDB

# ============================================================
# FUNZIONE PER INVIO EMAIL (Task 9.2 - Implementazione Mihali)
# ============================================================
def invia_email(destinatario, oggetto, corpo):  # Funzione per inviare email
    """
    Gestisce l'autenticazione SMTP e l'invio fisico dell'email.
    """
    try:  # Blocco try per gestire errori invio
        # Creazione del contenitore MIME per il messaggio
        msg = MIMEMultipart()  # Crea messaggio multipart
        msg['From'] = EMAIL_CONFIG["sender"]  # Imposta mittente
        msg['To'] = destinatario  # Imposta destinatario
        msg['Subject'] = oggetto  # Imposta oggetto
        msg.attach(MIMEText(corpo, 'plain'))  # Allega corpo testo
        
        # Apertura connessione sicura con il server Gmail
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:  # Connessione SSL
            # Login: qui il server verifica mittente e password per le app
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])  # Autenticazione
            # Invio effettivo del messaggio
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())  # Invia email (dati vanno al server SMTP Gmail)
        
        print(f"📧 Email inviata con successo a {destinatario}")  # Successo (stampa console)
        return True  # Ritorna successo
    except Exception as e:  # Cattura errori
        # Se ricevi l'errore 535, la password è sbagliata o contiene spazi
        print(f"❌ Errore durante l'invio dell'email: {e}")  # Errore (stampa console)
        return False  # Ritorna fallimento

# ============================================================
# LOGICA DI ESECUZIONE (Test Sistema)
# ============================================================
mydb = None  # Inizializza connessione MySQL a None
mongo_client = None  # Inizializza client MongoDB a None

try:  # Blocco try principale per test sistema
    print("--- 🔍 Inizio Test Sistema SafeClaim ---")  # Messaggio inizio (stampa console)
    
    # --- Test Connessione MySQL ---
    try:  # Prova connessione MySQL
        mydb = mysql.connector.connect(**MYSQL_CONFIG)  # Connette a MySQL (dati configurazione usati per connessione)
        print("✅ MySQL: Connesso")  # Successo (stampa console)
    except:  # Errore connessione
        # Gestiamo il fallimento del DB per procedere con il test SMTP
        print("⚠️ MySQL: Connessione fallita (Saltato)")  # Avviso (stampa console)
    
    # --- Test Connessione MongoDB ---
    try:  # Prova connessione MongoDB
        mongo_client = MongoClient(MONGO_URI)  # Crea client MongoDB
        mongo_client.admin.command('ping')  # Ping per test connessione
        print("✅ MongoDB: Connesso")  # Successo (stampa console)
    except:  # Errore connessione
        print("⚠️ MongoDB: Connessione fallita (Saltato)")  # Avviso (stampa console)
    
    # --- ESECUZIONE TASK 9.2: INVIO MAIL ---
    print("\n🚀 Avvio invio notifica automatica...")  # Messaggio avvio invio (stampa console)
    
    # Eseguiamo il test finale dell'integrazione SMTP
    successo = invia_email(  # Chiama funzione invio email
        destinatario="mihali.sebastian@iisgalvanimi.edu.it",  # Destinatario
        oggetto="SafeClaim - Task 9.2 Completato",  # Oggetto email
        corpo="Integrazione server SMTP riuscita. Il sistema di notifiche è operativo."  # Corpo email
    )
    
    if successo:  # Se invio riuscito
        print("\n🏆 TEST FINALE: Integrazione SMTP verificata con successo!")  # Successo finale (stampa console)
    else:  # Se fallito
        print("\n⚠️ TEST FINALE: Errore")  # Errore finale (stampa console)

except Exception as e:  # Cattura errori imprevisti
    print(f"❌ Errore imprevisto: {e}")  # Errore (stampa console)

finally:  # Sempre eseguito alla fine
    # Chiusura sicura delle risorse per evitare sprechi di memoria
    if mydb and mydb.is_connected(): mydb.close()  # Chiude connessione MySQL se aperta
    if mongo_client: mongo_client.close()  # Chiude client MongoDB se creato
    print("\n🔒 Test terminato. Risorse chiuse.")  # Messaggio fine (stampa console)