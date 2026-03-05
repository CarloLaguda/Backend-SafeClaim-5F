import mysql.connector
from flask import Flask, request, jsonify
from flask_cors import CORS

# Inizializzazione dell'app Flask
app = Flask(__name__)
# CORS permette al frontend (es. React o Vue) di comunicare con questa API anche se girano su porte diverse
CORS(app)

# --- CONFIGURAZIONE CREDENZIALI LOCALI ---
# Qui definiamo i parametri per connetterci al tuo MariaDB locale
db_config = {
    'host': 'localhost',
    'user': 'pythonuser',
    'password': 'password123',
    'database': 'mydatabase'
}

def setup_database():
    """
    Funzione di inizializzazione: crea il database e la tabella Veicolo 
    automaticamente all'avvio del programma se non sono già presenti.
    """
    try:
        # Prima connessione generica al server (senza specificare il database)
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = conn.cursor()
        
        # Crea fisicamente il database 'mydatabase'
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['database']}")
        # Seleziona il database su cui lavorare
        cursor.execute(f"USE {db_config['database']}")
        
        # Query SQL per creare la tabella Veicolo con i vincoli richiesti (targa e telaio unici)
        query_tabella = """
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
        """
        cursor.execute(query_tabella)
        conn.commit() # Salva i cambiamenti nel database
        cursor.close()
        conn.close()
        print("✅ Database e Tabella pronti!")
    except mysql.connector.Error as err:
        print(f"❌ Errore Setup: {err}")

def get_db_connection():
    """Funzione helper per aprire una connessione al DB velocemente dentro gli endpoint."""
    return mysql.connector.connect(**db_config)

# --- ENDPOINTS API ---

@app.route('/veicoli', methods=['GET'])
def get_all_veicoli():
    """Endpoint per leggere tutti i veicoli salvati nel sistema."""
    try:
        conn = get_db_connection()
        # dictionary=True trasforma i risultati SQL in oggetti Python (chiave: valore)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Veicolo")
        veicoli = cursor.fetchall() # Recupera tutte le righe
        cursor.close()
        conn.close()
        return jsonify(veicoli), 200 # Restituisce la lista in formato JSON
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/veicoli', methods=['POST'])
def add_veicolo():
    """Endpoint per inserire un nuovo veicolo tramite JSON (POST)."""
    data = request.json # Legge i dati inviati nel corpo della richiesta
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query parametrizzata (%s) per prevenire SQL Injection
        query = """
            INSERT INTO Veicolo 
            (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id, azienda_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        # Estrazione sicura dei dati dal JSON
        values = (
            data.get('targa'),
            data.get('n_telaio'),
            data.get('marca'),
            data.get('modello'),
            data.get('anno_immatricolazione'),
            data.get('automobilista_id'),
            data.get('azienda_id')
        )
        
        cursor.execute(query, values)
        conn.commit() # Rende permanente l'inserimento
        new_id = cursor.lastrowid # Ottiene l'ID appena generato dall'auto_increment
        
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "id": new_id}), 201
    except mysql.connector.Error as err:
        # Se la targa è già presente, restituirà un errore 400 (Duplicate Entry)
        return jsonify({"error": "Errore inserimento", "details": str(err)}), 400

@app.route('/veicoli/<int:id>', methods=['GET'])
def get_veicolo(id):
    """Endpoint per cercare un veicolo specifico conoscendo il suo ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # La virgola dopo (id,) è necessaria per creare una tupla
        cursor.execute("SELECT * FROM Veicolo WHERE id = %s", (id,))
        veicolo = cursor.fetchone() # Recupera un solo risultato
        cursor.close()
        conn.close()
        if veicolo:
            return jsonify(veicolo), 200
        return jsonify({"error": "Non trovato"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 1. Prepariamo il database
    setup_database() 
    print("🚀 API SafeClaim Local attiva su http://127.0.0.1:5000")
    # 2. Avviamo Flask in modalità debug (si riavvia da solo se modifichi il codice)
    app.run(debug=True, port=5000)