import pymongo  # Importa la libreria per connettersi e usare il database MongoDB Atlas
import requests  # Importa la libreria per fare richieste HTTP (utile per API esterne)
from flask import Flask, request, jsonify  # Importa Flask per il server, request per leggere i dati in entrata e jsonify per rispondere in formato JSON
from flask_cors import CORS  # Importa CORS per permettere al server di accettare chiamate da siti diversi (es. da Postman o dal tuo sito)
from datetime import datetime  # Importa la gestione di date e orari
from bson.objectid import ObjectId  # Importa il convertitore per gli ID unici di MongoDB
import smtplib  # Importa la libreria standard per inviare email tramite protocollo SMTP
from email.mime.text import MIMEText  # Serve per creare il contenuto testuale della mail
from email.mime.multipart import MIMEMultipart  # Serve per costruire un messaggio email con vari pezzi (mittente, oggetto, corpo)

app = Flask(__name__)  # Crea l'oggetto principale della tua applicazione web
CORS(app)  # Attiva il modulo CORS per evitare blocchi di sicurezza durante le chiamate API

# --- CONFIGURAZIONE SMTP (EMAIL) ---
# Dizionario che contiene le "chiavi" per accedere al server email di Google
EMAIL_CONFIG = {
    "sender": "mattioni.tommaso@iisgalvanimi.edu.it",  # L'indirizzo che spedisce le mail
    "password": "faefkrzmkeoizviw", # La password specifica per le app generata da Google
    "smtp_server": "smtp.gmail.com",  # L'indirizzo del server di posta in uscita di Gmail
    "port": 465  # La porta standard per la connessione sicura (SSL)
}

# --- CONFIGURAZIONE MONGODB ---
# La stringa di connessione che contiene l'indirizzo del tuo cluster nel cloud
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
DB_NAME = "FakeClaim"  # Il nome del database che creato su Atlas

try:
    # Tenta di collegarsi a MongoDB con un tempo massimo di attesa di 5 secondi
    client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]  # Seleziona il database specifico
    sinistri_col = db['sinistri']  # Seleziona la tabella dove salvi gli incidenti
    client.server_info()  # controllo per vedere se il database risponde davvero
    print("Connessione a MongoDB Atlas riuscita!")  # Messaggio di conferma nel terminale
except Exception as e:
    # Se il database è spento o l'indirizzo è sbagliato, stampa l'errore
    print(f"Errore connessione DB: {e}")
    sinistri_col = None  # Imposta a None per evitare che il server crashi dopo

# --- NUOVA ROTTA PER INVIARE EMAIL ---
# Definisce l'URL /invia-email che accetta solo chiamate di tipo POST 
@app.route('/invia-email', methods=['POST'])
def invia_email_endpoint():
    """
    Funzione che gestisce l'invio delle mail quando viene chiamato l'indirizzo /invia-email
    """
    data = request.json  # Legge il pacchetto di dati (JSON) che arriva da Postman o dal sito
    destinatario = data.get('destinatario')  # Estrae l'email di chi deve ricevere
    oggetto = data.get('oggetto', "Notifica SafeClaim")  # Estrae l'oggetto (usa un default se manca)
    messaggio = data.get('messaggio', "Test invio da Flask")  # Estrae il testo della mail

    # Se l'utente non ha scritto l'email del destinatario, ferma tutto e dà errore 400
    if not destinatario:
        return jsonify({"error": "Manca il destinatario"}), 400

    try:
        # --- COSTRUZIONE DEL MESSAGGIO ---
        msg = MIMEMultipart()  # Crea il contenitore vuoto per la mail
        msg['From'] = EMAIL_CONFIG["sender"]  # Scrive il mittente nell'intestazione
        msg['To'] = destinatario  # Scrive il destinatario nell'intestazione
        msg['Subject'] = oggetto  # Scrive l'oggetto della mail
        msg.attach(MIMEText(messaggio, 'plain'))  # Incolla il testo del messaggio dentro la mail

        # --- INVIO REALE ---
        # Si connette al server di Google usando la porta sicura 465 (SSL)
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])  # Fa il login con le tue credenziali
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())  # Spedisce fisicamente la mail

        # Se tutto è andato bene, risponde con successo
        return jsonify({"status": "success", "message": f"Email inviata a {destinatario}"}), 200

    except smtplib.SMTPAuthenticationError:
        # Errore specifico se la password o l'email sono sbagliate
        return jsonify({"status": "error", "message": "Credenziali email rifiutate"}), 500
    except Exception as e:
        # Errore generico per qualsiasi altro problema tecnico
        return jsonify({"status": "error", "message": str(e)}), 500

# avvia il server Flask, che rimarrà in ascolto sulla porta 5000 per rispondere alle chiamate API
if __name__ == '__main__':
    app.run()  