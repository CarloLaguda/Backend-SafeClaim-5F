# IMPORTAZIONI 
import pymongo  # Libreria per connettersi a MongoDB
import requests  # Libreria per fare richieste HTTP (non usata in questo file)
from flask import Flask, request, jsonify  # Framework web Flask per creare l'API REST
from flask_cors import CORS  # Abilita CORS (Cross-Origin Resource Sharing) per richieste da altri domini
from datetime import datetime  # Per gestire date e ore (non usato in questo file)
from bson.objectid import ObjectId  # Per lavorare con gli ID di MongoDB (non usato direttamente)
import smtplib  # Libreria per inviare email tramite SMTP
from email.mime.text import MIMEText  # Per creare il corpo del messaggio email
from email.mime.multipart import MIMEMultipart  # Per creare email multi-parte (testo + HTML)

# INIZIALIZZAZIONE FLASK 
app = Flask(__name__)  # Crea l'applicazione Flask
CORS(app)  # Abilita le richieste CORS da altri domini

#  CONFIGURAZIONE SMTP (EMAIL) 
EMAIL_CONFIG = {
    "sender": "safeclaimservice@gmail.com",  # Email del mittente (account Gmail)
    "display_name": "SafeClaim Support",  # Nome che apparirà come mittente nell'email
    "password": "mhwpbnllgkzgruer",  # Password specifica Gmail 
    "smtp_server": "smtp.gmail.com",  # Server SMTP di Gmail
    "port": 465  # Porta per connessione SSL 
}

# CONFIGURAZIONE MONGODB 
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"  # Stringa di connessione a MongoDB Atlas
DB_NAME = "FakeClaim"  # Nome del database da utilizzare


#  CONNESSIONE A MONGODB 
try:
    # Crea il client MongoDB con timeout di 5 secondi
    client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    # Seleziona il database
    db = client[DB_NAME]
    # Seleziona la collezione 'sinistri'
    sinistri_col = db['sinistri']
    # Verifica che la connessione sia attiva facendo una query al server
    client.server_info()
    # Se tutto va bene, stampa un messaggio di successo
    print("Connessione a MongoDB Atlas riuscita!")
except Exception as e:
    # Se c'è un errore, stampa il messaggio di errore
    print(f"Errore connessione DB: {e}")
    # Imposta sinistri_col a None per indicare che la connessione è fallita
    sinistri_col = None

# ROTTA PER INVIARE EMAIL 
@app.route('/invia-email', methods=['POST'])  # Definisce un endpoint POST all'indirizzo /invia-email
def invia_email_endpoint():
    # Estrae il corpo della richiesta JSON
    data = request.json
    # Estrae l'email del destinatario dal JSON
    destinatario = data.get('destinatario')
    # Estrae l'oggetto dell'email 
    oggetto = data.get('oggetto', "Notifica SafeClaim")
    # Estrae il messaggio dell'email 
    messaggio = data.get('messaggio', "Test invio da Flask")

    # Controlla se il destinatario è stato fornito
    if not destinatario:
        # Se manca, restituisce un errore HTTP 400 (Bad Request)
        return jsonify({"error": "Manca il destinatario"}), 400

    try:
        # COSTRUZIONE DEL MESSAGGIO EMAIL 
        # Crea un oggetto MIMEMultipart per costruire un'email multi-parte
        msg = MIMEMultipart()
        # Imposta il mittente con il nome display leggibile 
        msg['From'] = f"{EMAIL_CONFIG['display_name']} <{EMAIL_CONFIG['sender']}>"
        # Imposta il destinatario
        msg['To'] = destinatario
        # Imposta l'oggetto dell'email
        msg['Subject'] = oggetto

        # CREAZIONE DEL TEMPLATE HTML PER IL CORPO DELL'EMAIL
        # Crea il corpo dell'email in formato HTML
        corpo_html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee;">
              <h2 style="color: #2e6c80;">Aggiornamento SafeClaim</h2>
              <p>Gentile utente,</p>
              <p>{messaggio}</p>
              <br>
              <hr style="border: 0; border-top: 1px solid #eee;" />
              <p style="font-size: 0.8em; color: #888;">
                Questa è una notifica automatica dal sistema SafeClaim. 
                Per favore non rispondere direttamente a questa email.
              </p>
            </div>
          </body>
        </html>
        """
        
        # Alleghiamo il corpo HTML al messaggio 
        msg.attach(MIMEText(corpo_html, 'html'))

        # INVIO DELL'EMAIL VIA SMTP 
        # Apre una connessione SSL_SMTP al server Gmail
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:
            # Effettua il login con email e password
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            # Invia l'email dal mittente al destinatario (msg.as_string() converte il messaggio in stringa)
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())

        # Se l'email è stata inviata con successo, restituisce un messaggio JSON positivo (HTTP 200)
        return jsonify({"status": "success", "message": f"Email inviata a {destinatario}"}), 200

    except smtplib.SMTPAuthenticationError:
        # Se le credenziali email sono sbagliate, restituisce un errore HTTP 500
        return jsonify({"status": "error", "message": "Credenziali email rifiutate"}), 500
    except Exception as e:
        # Se c'è un altro errore generico, restituisce il messaggio di errore (HTTP 500)
        return jsonify({"status": "error", "message": str(e)}), 500

# AVVIO DEL PROGRAMMA 
if __name__ == '__main__':
    # Avvia il server Flask 
    # Per default ascolta sulla porta 5000
    app.run()