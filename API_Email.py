
# SEZIONE IMPORTAZIONI LIBRERIE


# LIBRERIE DATABASE
import pymongo                             # consente connessione a database NoSQL MongoDB
import mysql.connector                     # MySQL/MariaDB - gestisce connessioni ai database SQL relazionali
from mysql.connector import Error          # Classe per gestire eccezioni specifiche di MySQL

# LIBRERIE WEB E SERVER
from flask import Flask, request, jsonify  # Flask: microframework per creare server web; request gestisce HTTP; jsonify converte Python dict in JSON
from flask_cors import CORS                # CORS: abilita richieste HTTP cross-origin permettendo al frontend di chiamare questo backend

# LIBRERIE PER DATA/TEMPO E OGGETTI
from datetime import datetime              # Gestisce data e ora corrente per timestamp degli inserimenti database
from bson.objectid import ObjectId         # Converte ObjectId MongoDB in formato leggibile e viceversa

# LIBRERIE PER GESTIONE EMAIL
import smtplib                             # Protocollo SMTP per inviare email tramite server
import urllib.parse                        # Codifica speciale per URL (converte caratteri speciali della password in formato URL-safe)
from email.mime.text import MIMEText       # Crea corpo email in formato HTML MIME (Multipurpose Internet Mail Extensions)
from email.mime.multipart import MIMEMultipart # Crea messaggi email multipart con intestazioni, testo e allegati

# LIBRERIE PER THREADING E PROCESSI
import threading                           # Consente esecuzione di funzioni in background su thread separati (non blocca il server), 
                                        #il threading serve per inviare email senza ritardare la risposta HTTP al client

# SEZIONE 1: INIZIALIZZAZIONE APPLICAZIONE FLASK
app = Flask(__name__)                      # Crea applicazione Flask 
CORS(app)                                  # Abilita CORS per permettere richieste dai browser (elimina blocchi Same-Origin)

# SEZIONE 2: CONFIGURAZIONE EMAIL SMTP (Credenziali Mittente)
EMAIL_CONFIG = {
    # Indirizzo email che funge da mittente di tutte le email inviate dal sistema
    "sender": "safeclaimservice@gmail.com",
    
    # Nome visualizzato nel campo "From" dell'email ricevuta dal destinatario
    "display_name": "SafeClaim Support",
    
    # Password speciale generata da Gmail per app esterne (non la password account principale)
    "password": "mhwpbnllgkzgruer",
    
    # Indirizzo del server SMTP di Google che gestisce l'invio email
    "smtp_server": "smtp.gmail.com",
    
    # Porta 465 = connessione SMTP con crittografia SSL/TLS (più sicura della 587)
    "port": 465
}


# SEZIONE 3: CONFIGURAZIONE MONGODB ATLAS 

# Decodifica la password speciale in formato URI-safe (caratteri speciali diventano %xx) 
_pw = urllib.parse.quote_plus("xxx123##")

# URI completa connessione a MongoDB Atlas 
# Formato: mongodb+srv://username:password@cluster.mongodb.net/?appName=name
# Contiene: utente (dbFakeClaim), password codificata, cluster identificativo, nomefile app
MONGO_URI = f"mongodb+srv://dbFakeClaim:{_pw}@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"


# SEZIONE 4: CONFIGURAZIONE MARIADB / MYSQL (Database SQL Relazionale Locale), 
# che conterrà dati automobilisti e assicuratori, usato per recuperare email e nomi da inserire nelle notifiche email

MYSQL_CONFIG = {
    # Indirizzo host MySQL: 127.0.0.1 è localhost 
    "host": "127.0.0.1",
    
    # Username per autenticazione al database MySQL
    "user": "pythonuser",
    
    # Password corrispondente all'utente (necessaria per login)
    "password": "password123",
    
    # Nome del database specifico da utilizzare per le query
    "database": "gestione_assicurazioni",
    
    # Porta 3306 è l'impostazione predefinita standard per MySQL/MariaDB
    "port": 3306
}


# SEZIONE 5: TEMPLATE EMAIL HTML (Modelli Corpo Email)

class SafeClaimTemplates:
    """
    Classe contenente template email in HTML con placeholder per personalizzazione.
    I placeholder {variabile} verranno sostituiti con dati reali (nome, targa, etc.)
    """
    
    # ---- TEMPLATE 1: EMAIL AL CLIENTE/AUTOMOBILISTA ----
    # Oggetto email: titolo che appare nella casella postale del cliente
    NEW_CLAIM_SUBJECT = "Segnalazione Nuovo Sinistro: Pratica avviata"

    # Corpo email in HTML con stile CSS incorporato - inviato all'automobilista regolare
    NEW_CLAIM_HTML = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <!-- Intestazione arancione con logo/titolo -->
            <div style="background-color: #f39c12; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">SafeClaim - Nuovo Sinistro</h1>
            </div>
            <!-- Corpo messaggio con dati sinistro -->
            <div style="padding: 20px;">
                <h2>Ciao {user_name},</h2>
                <p>La segnalazione è stata registrata correttamente.</p>
                <!-- Dati dettagliati del sinistro inseriti via .format() -->
                <p><strong>Targa:</strong> {targa}<br><strong>Data:</strong> {incident_date}</p>
                <p><strong>ID Pratica:</strong> #{claim_id}</p>
            </div>
        </div>
    </body>
    </html>
    """

    # ---- TEMPLATE 2: EMAIL AGLI ASSICURATORI/ADMIN ----
    # Oggetto email: notifica administrators/assicuratori su nuovo sinistro
    ADMIN_NOTIFY_SUBJECT = " Avviso: Nuova segnalazione sinistro"

    # Corpo email in HTML per notificare gli assicuratori - design in colori scuri professionali
    ADMIN_NOTIFY_HTML = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <!-- Intestazione blu scuro con branding admin -->
            <div style="background-color: #2c3e50; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">SafeClaim Admin</h1>
            </div>
            <!-- Dettagli completi sinistro per ufficio amministrativo -->
            <div style="padding: 20px;">
                <h2>Nuova Pratica Ricevuta</h2>
                <!-- ID MongoDB per tracciamento nel database -->
                <p><strong>ID Mongo:</strong> {claim_id}<br><strong>Targa:</strong> {targa}</p>
                <!-- Descrizione completa dell'incidente -->
                <p><strong>Descrizione:</strong> {descrizione}</p>
            </div>
        </div>
    </body>
    </html>
    """


# SEZIONE 6: CONNESSIONE E INIZIALIZZAZIONE MONGODB ATLAS

try:
    # Crea un client MongoDB usando la URI di connessione configurata all'inizio
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    
    # Seleziona il database specifico "FakeClaim" dal cluster MongoDB
    db = mongo_client["FakeClaim"]
    
    # Seleziona la collezione (tabella NoSQL) dove verranno salvati i documenti sinistri 
    sinistri_col = db['sinistri']
    
    # Forza un controllo immediato di connessione - genera errore se connessione fallisce
    mongo_client.server_info()
    
    # Log di successo - stampa quando la connessione MongoDB è riuscita
    print(" MongoDB Atlas Connesso!")
    
except Exception as e:
    # Se connessione fallisce, stampa il messaggio di errore
    print(f" Errore MongoDB: {e}")
    
    # Imposta la collezione a None così il codice sa che MongoDB non è disponibile
    sinistri_col = None

# SEZIONE 7: FUNZIONE HELPER CONNESSIONE MYSQL, 
# serve a creare una nuova connessione MySQL ogni volta che viene chiamata, evitando problemi di connessioni 

def get_mysql_conn():
    """
    Funzione helper che ritorna una nuova connessione MySQL ogni volta che viene chiamata.
    
    Returns:
        mysql.connector.MySQLConnection: oggetto connessione aperto per eseguire query
        
    Utilizza le credenziali da MYSQL_CONFIG per autenticazione e connessione.
    Ogni thread dovrebbe avere la propria connessione MySQL (non riutilizzare).
    """
    return mysql.connector.connect(**MYSQL_CONFIG)  # ** unpacking: passa host, user, password, etc. come parametri

# SEZIONE 8: FUNZIONE INVIO EMAIL VIA SMTP

def invia_mail_fisica(destinatario, oggetto, corpo_html):
    """
    Invia un'email HTML tramite SMTP Gmail a un destinatario specificato.
    
    Args:
        destinatario (str): indirizzo email del ricevente
        oggetto (str): linea subject dell'email
        corpo_html (str): corpo email in formato HTML
        
    Returns:
        bool: True se invio riuscito, False se errore
        
    La funzione usa le credenziali definite in EMAIL_CONFIG per autenticarsi a Gmail.
    """
    try:
        # Crea un messaggio MIME multipart che supporta HTML + allegati, MIME e' un formato standard per email complesse
        msg = MIMEMultipart()
        
        # Imposta il campo "From" con nome visualizzato + indirizzo email
        # Formato: "SafeClaim Support <safeclaimservice@gmail.com>"
        msg['From'] = f"{EMAIL_CONFIG['display_name']} <{EMAIL_CONFIG['sender']}>"
        
        # Imposta il campo "To" con l'indirizzo del destinatario
        msg['To'] = destinatario
        
        # Imposta il campo "Subject" che apparirà nella casella postale
        msg['Subject'] = oggetto
        
        # Aggiunge il corpo HTML al messaggio (parametro 'html' specififica il tipo MIME)
        msg.attach(MIMEText(corpo_html, 'html'))
        
        # Connessione sicura SMTP con SSL (porta 465 = SSL)
        # Usa 'with' per garantire chiusura della connessione anche in caso di errore, 
        # with serve a gestire automaticamente risorse come connessioni, file chiudendole al termine del blocco
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:
            # Esegue login SMTP con le credenziali Gmail (email + password app)
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            
            # Invia l'email: da mittente, a destinatario, con messaggio formattato
            # msg.as_string() converte l'oggetto messaggio in stringa pronta per l'invio SMTP
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())
        
        # Se raggiungiamo qui, invio è riuscito
        return True
        
    except Exception as e:
        # Stampa l'errore SMTP in caso di fallimento
        print(f" SMTP Error: {e}")
        
        # Ritorna False per indicare fallimento
        return False

# SEZIONE 9: THREAD NOTIFICHE - INVIO EMAIL IN BACKGROUND

def gestisci_notifiche_sinistro(sinistro_id, data):
    """
    Funzione eseguita in thread separato per inviare email di notifica senza bloccare il server.
    
    Args:
        sinistro_id (str): ID MongoDB del sinistro appena creato
        data (dict): dizionario con dati sinistro (automobilista_id, targa, descrizione, etc.)
        
    Questa funzione:
    1. Apre connessione MySQL
    2. Recupera dati automobilista e invia email di conferma
    3. Recupera lista assicuratori e invia notifiche a tutti
    4. Chiude connessione
    
    Errori non bloccano il server perché eseguita su thread background.
    """
    
    # Variabile per tracciare connessione MySQL - inizialmente None
    conn = None
    
    try:
        # Crea una NUOVA connessione MySQL per questo thread 
        conn = get_mysql_conn()
        
        # Crea cursore che ritorna risultati come dizionari 
        # Questo facilita lettura dati rispetto agli indici numerici, 
        cursor = conn.cursor(dictionary=True)

        #  EMAIL UTENTE AUTOMOBILISTA 
        # Query SQL per recuperare nome ed email dell'automobilista che ha segnalato il sinistro, 
        # %s è placeholder per parametro, (data['automobilista_id'],) è tupla con ID da sostituire,
        cursor.execute("SELECT nome, email FROM Automobilista WHERE id = %s", (data['automobilista_id'],))
        
        # Prende il primo risultato della query come dizionario, fecthone() ritorna None se non trova righe, altrimenti un dizionario con chiavi 'nome' e 'email' e lo mette in user
        user = cursor.fetchone()
        
        # Controlla se l'utente esiste nel database e ha un indirizzo email
        if user and user['email']:
            # Formatta il template HTML dell'email del cliente inserendo i dati reali
            html_u = SafeClaimTemplates.NEW_CLAIM_HTML.format(
                user_name=user['nome'],                    # Nome dell'automobilista
                targa=data['targa'],                       # Targa del veicolo incidentato
                incident_date=data['data_evento'],         # Data/ora dell'incidente
                claim_id=sinistro_id                       # ID MongoDB della pratica
            )
            
            # Invia l'email formattata all'indirizzo email dell'automobilista
            # new_claim_subject è l'oggetto dell'email, html_u è il corpo HTML formattato con i dati del sinistro
            invia_mail_fisica(user['email'], SafeClaimTemplates.NEW_CLAIM_SUBJECT, html_u)
            
            # Log di successo con indirizzo email per debugging
            print(f" Mail inviata all'utente: {user['email']}")

        #  EMAIL ASSICURATORI
        # Query SQL per recuperare TUTTI gli indirizzi email dei dipendenti Assicuratore
        cursor.execute("SELECT email FROM Assicuratore")
        
        # Ripete su ogni riga che viene ritornata dalla query 
        for ass in cursor.fetchall():
            # Controlla che l'assicuratore abbia un indirizzo email 
            if ass['email']:
                # Formatta il template admin HTML con i dati del sinistro
                html_a = SafeClaimTemplates.ADMIN_NOTIFY_HTML.format(
                    claim_id=sinistro_id,                  # ID MongoDB per tracciamento
                    targa=data['targa'],                   # Targa veicolo
                    descrizione=data['descrizione']        # Descrizione completa sinistro
                )
                
                # Invia email di notifica all'indirizzo email dell'assicuratore
                invia_mail_fisica(ass['email'], SafeClaimTemplates.ADMIN_NOTIFY_SUBJECT, html_a)
                
                # Log di successo con email per debugging e audit trail
                print(f" Notifica inviata all'assicuratore: {ass['email']}")

    except Exception as e:
        # Se errore non previsto, stampa con emoji di errore per visibilità log
        print(f" Errore Database/Notifiche: {e}")
        
    finally:
        #  Chiudere la connessione MySQL in tutti i casi 
        # 'finally' garantisce esecuzione anche se eccezione
        
        # Controlla se connessione esiste ed è ancora aperta al database
        if conn and conn.is_connected():
            # Chiude la connessione MySQL per liberare risorse database
            conn.close()



# SEZIONE 10: ENDPOINTS FLASK 


# Definisce una route HTTP POST all'indirizzo /sinistro
# Accetta richieste POST contenenti dati JSON con informazioni sul sinistro
@app.route('/sinistro', methods=['POST'])
def crea_sinistro():
    """
    Endpoint per creare un nuovo sinistro (incidente).
    
    Richiesta POST:
    {
        "automobilista_id": <int>,      # ID dell'automobilista da database MySQL
        "targa": "<string>",            # Targa del veicolo (es. "AB123CD")
        "data_evento": "<string>",      # Data/ora incidente (formato ISO)
        "descrizione": "<string>"       # Descrizione dettagliata sinistro
    }
    
    Risposta 201 (Successo):
    {
        "status": "success",
        "id_mongo": "<string>",         # ID MongoDB della pratica creata
        "message": "Sinistro registrato e notifiche avviate"
    }
    
    Risposta 500 (Errore):
    {
        "status": "error",
        "message": "<descrizione errore>"
    }
    """
    
    # Controlla che MongoDB sia disponibile prima di eseguire l'inserimento
    # Se None, significa che la connessione ao MongoDB è fallita durante init
    if sinistri_col is None:
        # Ritorna errore 500 (Internal Server Error) se database non disponibile
        return jsonify({"error": "Database MongoDB non connesso"}), 500
    
    # Estrae il JSON dal corpo della richiesta HTTP e lo converte in dizionario Python
    data = request.json
    
    try:
        # Crea un dizionario con i campi del nuovo documento sinistro che serve a MongoDB per inserire un nuovo record nella collezione 'sinistri'
        nuovo_doc = {
            # ID dell'automobilista: permette di linkare il sinistro al cliente, data sta per ID numerico da MySQL, non MongoDB
            "automobilista_id": data['automobilista_id'],
            
            # Targa del veicolo coinvolto nell'incidente
            "targa": data['targa'],
            
            # Data e ora dell'evento incidente
            "data_evento": data['data_evento'],
            
            # Descrizione dettagliata di cosa è successo
            "descrizione": data['descrizione'],
            
            # Stato iniziale della pratica: APERTO significa pratica nuova in elaborazione
            "stato": "APERTO",
            
            # Timestamp di quando il sinistro è stato inserito nel database
            "data_inserimento": datetime.now()
        }
        
        # Inserisce il documento nella collezione MongoDB 'sinistri'
        # insert_one() ritorna un oggetto con inserted_id (l'ID MongoDB generato)
        # res sta per "risultato" dell'inserimento, contiene informazioni sull'operazione di inserimento
        res = sinistri_col.insert_one(nuovo_doc)
        
        # Converte l'ObjectId MongoDB in stringa leggibile per HTTP response
        # in res ci sono informazioni sull'inserimento, res.inserted_id è l'ID del documento appena creato, che è un ObjectId, lo convertiamo in stringa per usarlo come ID della pratica
        # inserted_id serve a tracciare la pratica nel database e a inviare notifiche con riferimento a questo ID
        # s_id è l'ID univoco del sinistro appena creato, usato per tracking e notifiche, 
        # mettiamo tutto in s_id perche e' piu' chiaro che rappresenta l'ID del sinistro, non confondere con altri ID (es. automobilista_id)
        s_id = str(res.inserted_id)

        # Crea un nuovo thread per inviare le email senza bloccare la risposta HTTP
        # Questo permette al client di ricevere risposta subito, emails inviate in background
        # args=(s_id, data)e' un metodo che passa gli argomenti alla funzione gestisci_notifiche_sinistro, 
        # .start() avvia il thread (il codice continua senza aspettare)
        threading.Thread(target=gestisci_notifiche_sinistro, args=(s_id, data)).start() 

        # Ritorna risposta di successo HTTP 201 (Created) con dati della pratica
        return jsonify({
            "status": "success",
            # ID MongoDB della pratica per tracking futuro
            "id_mongo": s_id,
            "message": "Sinistro registrato e notifiche avviate"
        }), 201
        
    except Exception as e:
        # Se errore durante inserimento, ritorna 500 con descrizione errore
        # str(e) converte l'eccezione Exception in stringa leggibile
        return jsonify({"status": "error", "message": str(e)}), 500


# SEZIONE 11: AVVIO APPLICAZIONE FLASK


#
if __name__ == '__main__':
    
    # host='0.0.0.0': accetta connessioni da qualsiasi indirizzo IP (non solo localhost)
    # port=5000: il server ascolta sulla porta 5000 (es. http://localhost:5000)
    app.run(host='0.0.0.0', port=5000, debug=True)