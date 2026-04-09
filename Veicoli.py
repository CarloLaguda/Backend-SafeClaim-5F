import mysql.connector # Carica la libreria per far parlare Python con il database MySQL/MariaDB
from flask import Flask, request, jsonify # Carica i pezzi di Flask necessari per creare il sito e gestire dati JSON
from flask_cors import CORS # Carica il modulo per permettere a pagine web esterne di chiamare questa API

app = Flask(__name__) # Creiamo l'applicazione Flask, che è il motore del nostro server
CORS(app) # CORS serve a evitare blocchi di sicurezza quando il frontend chiama il backend

db_config = { # Inizio della configurazione dei dati per il database
    'host': 'localhost', # Il database si trova sullo stesso computer del codice
    'user': 'pythonuser', # Nome dell'utente creato su MariaDB
    'password': 'password123', # Password dell'utente
    'database': 'mydatabase' # Nome del database che vogliamo usare
} # Fine configurazione database

def setup_database(): # Inizio funzione per preparare il database all'avvio
    try: # Prova a eseguire i comandi seguenti
        conn = mysql.connector.connect( # Apre una connessione generale al server MySQL
            host=db_config['host'], # Usa l'host configurato sopra
            user=db_config['user'], # Usa l'utente configurato sopra
            password=db_config['password'] # Usa la password configurata sopra
        ) # Fine comando connessione
        cursor = conn.cursor() # Crea un cursore per inviare comandi SQL

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['database']}") # Crea il database se non esiste
        cursor.execute(f"USE {db_config['database']}") # Seleziona il database su cui lavorare
        
        query_tabella_veicoli = """ 
        CREATE TABLE IF NOT EXISTS Veicolo (
            id INT PRIMARY KEY AUTO_INCREMENT,
            targa VARCHAR(10) UNIQUE NOT NULL,
            n_telaio VARCHAR(50) UNIQUE,
            marca VARCHAR(50),
            modello VARCHAR(50),
            anno_immatricolazione INT,
            automobilista_id INT DEFAULT NULL,
            azienda_id INT DEFAULT NULL
        ) ENGINE=InnoDB;
        """ # Definizione della struttura della tabella Veicolo
        cursor.execute(query_tabella_veicoli) # Esegue il comando per creare la tabella Veicolo

        query_tabella_log = """ 
        CREATE TABLE IF NOT EXISTS LogRicerca (
            id INT PRIMARY KEY AUTO_INCREMENT,
            targa_cercata VARCHAR(10) NOT NULL,
            data_ricerca TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            risultati_trovati INT
        ) ENGINE=InnoDB;
        """ # Definizione della struttura della tabella LogRicerca
        cursor.execute(query_tabella_log) # Esegue il comando per creare la tabella dei log nel database

        conn.commit() # Salva definitivamente le tabelle create nel database
        cursor.close() # Chiude il cursore per liberare risorse
        conn.close() # Chiude la connessione al database
        print(" Database e Tabelle pronti!") # Stampa un messaggio di successo nel terminale
    except mysql.connector.Error as err: # Se c'è un errore nel database
        print(f" Errore Setup: {err}") # Stampa l'errore specifico nel terminale

def get_db_connection(): # Funzione per aprire la connessione al DB velocemente
    return mysql.connector.connect(**db_config) # Restituisce una connessione pronta usando i dati db_config

@app.route('/veicoli', methods=['GET']) # Rotta per ricevere tutti i veicoli via GET
def get_all_veicoli(): # Definizione della funzione per la rotta GET
    try: # Prova a eseguire la lettura
        conn = get_db_connection() # Apre la connessione al DB
        cursor = conn.cursor(dictionary=True) # Crea un cursore che restituisce i dati come dizionari
        cursor.execute("SELECT * FROM Veicolo") # Invia il comando per prendere tutte le righe
        veicoli = cursor.fetchall() # Scarica tutti i risultati trovati
        cursor.close() # Chiude il cursore
        conn.close() # Chiude la connessione
        return jsonify(veicoli), 200 # Restituisce i dati in formato JSON all'utente
    except Exception as e: # Se c'è un errore generico
        return jsonify({"error": str(e)}), 500 # Restituisce l'errore all'utente col codice 500

@app.route('/veicoli', methods=['POST']) # Rotta per aggiungere un veicolo via POST
def add_veicolo(): # Definizione della funzione per la rotta POST
    data = request.json # Legge i dati inviati dall'utente in formato JSON
    try: # Prova a eseguire l'inserimento
        conn = get_db_connection() # Apre la connessione al DB
        cursor = conn.cursor() # Crea il cursore SQL
        query = """
            INSERT INTO Veicolo 
            (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id, azienda_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """ # Prepara il comando di inserimento sicuro con i segnaposto %s
        values = ( # Crea una tupla con i valori estratti dal JSON
            data.get('targa'), data.get('n_telaio'), data.get('marca'),
            data.get('modello'), data.get('anno_immatricolazione'),
            data.get('automobilista_id'), data.get('azienda_id')
        ) # Fine tupla valori
        cursor.execute(query, values) # Esegue l'inserimento nel database
        conn.commit() # Salva l'inserimento in modo permanente
        new_id = cursor.lastrowid # Recupera l'ID generato automaticamente per la nuova riga
        cursor.close() # Chiude il cursore
        conn.close() # Chiude la connessione
        return jsonify({"status": "success", "id": new_id}), 201 # Conferma il successo con ID e codice 201
    except mysql.connector.Error as err: # Se l'inserimento fallisce (es. targa doppia)
        return jsonify({"error": "Errore inserimento", "details": str(err)}), 400 # Invia l'errore all'utente

@app.route('/veicoli/ricerca', methods=['GET']) # Rotta per cercare una targa specifica
def cerca_veicolo_per_targa(): # Definizione della funzione di ricerca
    targa_da_cercare = request.args.get('valore') # Legge il parametro 'valore' dall'URL
    if not targa_da_cercare: # Se l'utente non ha scritto nulla
        return jsonify({"error": "Inserire una targa per la ricerca"}), 400 # Restituisce errore 400
    try: # Prova a eseguire la ricerca e il log
        conn = get_db_connection() # Apre la connessione al DB
        cursor = conn.cursor(dictionary=True) # Cursore in modalità dizionario
        query_auto = "SELECT * FROM Veicolo WHERE targa = %s" # Comando per cercare la targa
        cursor.execute(query_auto, (targa_da_cercare,)) # Esegue la ricerca in modo sicuro
        risultati = cursor.fetchall() # Mette i risultati nella lista 'risultati'

        query_log = "INSERT INTO LogRicerca (targa_cercata, risultati_trovati) VALUES (%s, %s)" # Comando per scrivere il log
        cursor.execute(query_log, (targa_da_cercare, len(risultati))) # Scrive nel database la targa cercata e quanti veicoli sono stati trovati
        
        conn.commit() # Salva il log nel database in modo definitivo
        cursor.close() # Chiude il cursore
        conn.close() # Chiude la connessione
        return jsonify({ # Invia la risposta JSON finale all'utente
            "status": "success", # Stato dell'operazione
            "targa_cercata": targa_da_cercare, # Conferma della targa cercata
            "veicoli_trovati": risultati # Invia i dati delle auto trovate
        }), 200 # Fine risposta con successo
    except Exception as e: 
        return jsonify({"error": str(e)}), 500 # Restituisce l'errore (ora correttamente indentato)

@app.route('/veicoli/storico/<targa>', methods=['GET']) # Nuova rotta per vedere quante volte è stata cercata una targa
def visualizza_storico_targa(targa): # Definizione della funzione storico
    try: # Prova a leggere lo storico
        conn = get_db_connection() # Connessione al DB
        cursor = conn.cursor(dictionary=True) # Cursore dizionario
        query_storico = "SELECT * FROM LogRicerca WHERE targa_cercata = %s" # Prende tutti i log per quella targa
        cursor.execute(query_storico, (targa,)) # Esegue la ricerca nello storico
        cronologia = cursor.fetchall() # Salva i log trovati in 'cronologia'
        cursor.close() # Chiude il cursore
        conn.close() # Chiude la connessione
        return jsonify({ # Risposta all'utente
            "status": "success", # Stato operazione
            "targa": targa, # Targa analizzata
            "totale_volte_cercata": len(cronologia), # Conta quante volte appare nei log
            "dettaglio_log": cronologia # Invia la lista di tutte le date di ricerca
        }), 200 # Fine risposta con successo
    except Exception as e: # Se qualcosa fallisce
        return jsonify({"error": str(e)}), 500 # Restituisce l'errore col codice 500

if __name__ == '__main__': # Se il file viene eseguito direttamente
    setup_database() # Avvia la creazione del database e delle tabelle
    print("API SafeClaim Local attiva su http://127.0.0.1:5000") # Messaggio di avvio server nel terminale
    app.run(debug=True, port=5000) # Avvia il server Flask sulla porta 5000 (assicurati di aver chiuso Sinistro.py)