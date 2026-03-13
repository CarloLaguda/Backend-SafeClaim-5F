import mysql.connector # Carica la libreria per far parlare Python con il database MySQL/MariaDB
from flask import Flask, request, jsonify # Carica i pezzi di Flask necessari per creare il sito e gestire dati JSON
from flask_cors import CORS # Carica il modulo per permettere a pagine web esterne di chiamare questa API

# Creiamo l'applicazione Flask, che è il motore del nostro server
app = Flask(__name__)
#CORS serve a evitare blocchi di sicurezza quando il frontend chiama il backend
CORS(app)

# DATI PER ACCEDERE AL DATABASE
# Qui scriviamo l'indirizzo, l'utente e la password per entrare nel database locale
db_config = {
    'host': 'localhost', # Il database si trova sullo stesso computer del codice
    'user': 'pythonuser', # Nome dell'utente creato su MariaDB
    'password': 'password123', # Password dell'utente
    'database': 'mydatabase' # Nome del database che vogliamo usare
}

def setup_database():
    """ Questa funzione prepara tutto il database all'inizio del programma """
    try:
        # Apre una prima connessione generale per vedere se il server è acceso
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = conn.cursor() # Crea un 'cursore', ovvero l'oggetto che scrive i comandi SQL
                               # Con questo cursore possiamo dire al database cosa fare, come se fosse una tastiera che scrive comandi
                               # Il nome cursor è uno standard in quasi tutti i linguaggi di programmazione che parlano con i database SQL.
                               # conn: È il tunnel (la connessione) che collega il nostro programma al database. Senza questa connessione, non possiamo comunicare con il database.
                               # cursor: È lo strumento (il cursore) che usiamo per inviare comandi SQL attraverso la connessione.
                               # () È il comando "Attiva/Crea"

        # Crea il database col nome scelto se non esiste già
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['database']}")
        # Dice a Python: 'D'ora in poi lavora dentro questo database'
        cursor.execute(f"USE {db_config['database']}")
        
        # Scrive le istruzioni per creare la tabella dei veicoli
        query_tabella = """
        CREATE TABLE IF NOT EXISTS Veicolo (
            id INT PRIMARY KEY AUTO_INCREMENT, # ID numerico che cresce da solo (1, 2, 3...)
            targa VARCHAR(10) UNIQUE NOT NULL, # La targa deve esserci sempre e non può essere doppia
            n_telaio VARCHAR(50) UNIQUE, # Il numero di telaio deve essere unico
            marca VARCHAR(50), # Colonna per la marca dell'auto
            modello VARCHAR(50), # Colonna per il modello
            anno_immatricolazione INT, # Colonna per l'anno (numero intero)
            automobilista_id INT DEFAULT NULL, # Collegamento opzionale a un guidatore
            azienda_id INT DEFAULT NULL # Collegamento opzionale a un'azienda
        ) ENGINE=InnoDB; # Usa il motore InnoDB che è standard e sicuro
        """
        cursor.execute(query_tabella) # Esegue il comando di creazione tabella
        conn.commit() # Salva definitivamente le modifiche fatte
        cursor.close() # Chiude il cursore
        conn.close() # Chiude la connessione temporanea
        print(" Database e Tabella pronti!")
    except mysql.connector.Error as err:
        print(f" Errore Setup: {err}") # Se qualcosa va storto, stampa l'errore

def get_db_connection():
    """ Questa funzione serve solo ad aprire velocemente la connessione quando serve """
    return mysql.connector.connect(**db_config) # Restituisce una connessione pronta all'uso

# FUNZIONI PER GESTIRE LE RICHIESTE (ENDPOINTS) 

#ROTTA PER PRENDERE TUTTI I VEICOLI (GET)

@app.route('/veicoli', methods=['GET']) # Se l'utente va all'indirizzo /veicoli con metodo GET
def get_all_veicoli():
    """ Restituisce l'elenco di tutte le auto """
    try:
        conn = get_db_connection() # Si connette al DB
        # dictionary=True serve per ricevere i dati come {'targa': 'AA123BB'} come un dizionario 
        cursor = conn.cursor(dictionary=True) 
        cursor.execute("SELECT * FROM Veicolo") # Chiede al DB tutte le righe della tabella
        veicoli = cursor.fetchall() # Scarica tutti i risultati trovati
        cursor.close() # Chiude il cursore
        conn.close() # Chiude la connessione
        return jsonify(veicoli), 200 # Trasforma i dati in JSON e li invia all'utente con codice OK (200)
    except Exception as e:
        return jsonify({"error": str(e)}), 500 # Se c'è un errore, risponde col codice 500


#ROTTA PER AGGIUNGERE UN NUOVO VEICOLO (POST)

@app.route('/veicoli', methods=['POST']) # Se l'utente invia dati all'indirizzo /veicoli
def add_veicolo():
    """ Aggiunge un nuovo veicolo nel database """
    data = request.json # Prende il pacchetto di dati JSON inviato dall'utente
    try:
        conn = get_db_connection() # Si connette al DB
        cursor = conn.cursor() # Inizializza il cursore per eseguire query SQL e gestire i risultati
        
        # Query con comando per inserire i dati (usiamo i %s per sicurezza contro gli hacker)
        query = """
            INSERT INTO Veicolo 
            (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id, azienda_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        # Le percentuali servono a creare una struttura fissa della frase, 
        # lasciando dei "posti vuoti" che verranno riempiti solo all'ultimo secondo con i dati veri, 
        # rendendo il tutto sicuro, ordinato e a prova di errore.

        # Estrae i valori dal pacchetto JSON ricevuto 
        values = (
            data.get('targa'),
            data.get('n_telaio'),
            data.get('marca'),
            data.get('modello'),
            data.get('anno_immatricolazione'),
            data.get('automobilista_id'),
            data.get('azienda_id')
        )
        
        cursor.execute(query, values) # Esegue l'inserimento con i valori estratti
        conn.commit() # Salva l'inserimento nel database in modo permanente
        new_id = cursor.lastrowid # Si segna l'ID che il database ha assegnato a questa nuova riga
        
        cursor.close()  #Libera la memoria che serviva a gestire i risultati della tua domanda SQL. 
                        #Chiudere il cursore è utile per evitare di consumare risorse inutilmente,.
        conn.close()    #Chiude la connessione al database. 
                        #È importante chiudere la connessione quando hai finito di usarla per liberare risorse e permettere ad altri processi di connettersi.
        return jsonify({"status": "success", "id": new_id}), 201 # Risponde 'Creato con successo' (201)
    except mysql.connector.Error as err:
        # Se ad esempio la targa esiste già, il database darà errore e noi rispondiamo con errore 400
        return jsonify({"error": "Errore inserimento", "details": str(err)}), 400

#ROTTA PER PRENDERE UN VEICOLO SPECIFICO (GET)

@app.route('/veicoli/<int:id>', methods=['GET']) # Se l'utente cerca un ID specifico (es. /veicoli/5)
def get_veicolo(id):
    """ Cerca un solo veicolo tramite il suo numero ID """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Esegue la ricerca filtrando per ID
        cursor.execute("SELECT * FROM Veicolo WHERE id = %s", (id,)) 

        #Con WHERE id = %s, gli dici Prendi solo quella riga dove la colonna id corrisponde al valore che ti sto per dare".
        #Il %s,è il posto vuoto che verrà riempito in modo sicuro con il valore che ricevera da id
        # (id,). Questo è il valore che andrà a riempire il %s nella query. La virgola è necessaria per indicare che stiamo passando una tupla
        # In Python, per passare i valori al cursore, dobbiamo usare una "Tupla" (una lista fissa).
                                                                 
        
        veicolo = cursor.fetchone() # Prende solo il primo risultato trovato
        cursor.close()
        conn.close()
        if veicolo:
            return jsonify(veicolo), 200 # Se l'auto esiste, la invia
        return jsonify({"error": "Non trovato"}), 404 # Se non esiste, risponde 'Non trovato' (404)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# AVVIO DEL PROGRAMMA 
if __name__ == '__main__':
    setup_database() # Per prima cosa prepara il database e la tabella
    print("API SafeClaim Local attiva su http://127.0.0.1:5000")
    # Avvia il server Flask sulla porta 5000
    # debug=True significa che se cambi il codice, il server si aggiorna da solo
    app.run(debug=True, port=5000)