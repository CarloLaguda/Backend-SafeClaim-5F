from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
import pymongo
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import urllib.parse

app = Flask(__name__)

# --- 1. CONFIGURAZIONE E CONNESSIONI ---

# Parametri di connessione per il Database Relazionale (MySQL)
mysql_config = {
    'host': 'localhost',
    'user': 'pythonuser',
    'password': 'password123',
    'database': 'Locale_DB'
}

# Credenziali e stringa di connessione per il Database NoSQL (MongoDB Atlas)
user = "dbFakeClaim"
password = "xxx123##"
# Il password encoding serve per gestire caratteri speciali nella URL di connessione
encoded_password = urllib.parse.quote_plus(password)
CONNECTION_STRING = f"mongodb+srv://{user}:{encoded_password}@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
DB_NAME = "FakeClaim"

try:
    # Inizializzazione del client MongoDB con timeout di 5 secondi
    mongo_client = MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    db = mongo_client[DB_NAME]
    # Il comando 'ping' verifica se il server è effettivamente raggiungibile
    mongo_client.admin.command('ping')
    print("✅ MongoDB Connesso!")
except Exception as e:
    print(f"❌ Errore MongoDB: {e}")

def get_mysql_connection():
    """Ritorna un oggetto di connessione MySQL attivo."""
    return mysql.connector.connect(**mysql_config)

# --- 2. ROTTE API CON INTEGRAZIONE MYSQL ---

# A. APERTURA PRATICA
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica', methods=['POST'])
def crea_pratica(id_sinistro, id_perito):
    """
    Endpoint per l'apertura di una nuova pratica di perizia.
    Esegue un controllo incrociato: valida il Perito su MySQL prima di scrivere su MongoDB.
    """
    conn = None
    try:
        # Estrazione del corpo della richiesta (Request Body) in formato JSON
        data = request.get_json()
        if not data: return jsonify({"error": "Dati mancanti"}), 400

        # --- VALIDAZIONE MYSQL ---
        # Apertura connessione al DB Relazionale
        conn = get_mysql_connection()
        cursor = conn.cursor()
        # Query con segnaposto (%s) per prevenire attacchi di SQL Injection
        cursor.execute("SELECT id FROM Perito WHERE id = %s", (id_perito,))
        perito = cursor.fetchone()
        
        # Se il cursore non restituisce righe, il perito non esiste nel sistema centrale
        if not perito:
            return jsonify({"error": f"Perito con ID {id_perito} non trovato nel database relazionale"}), 404

        # --- OPERAZIONE MONGODB ---
        # Conversione della stringa id_sinistro in un oggetto ObjectId per le query NoSQL
        s_id = ObjectId(id_sinistro)
        
        # Definizione del Documento (Dictionary Python) da inserire nella collezione 'perizie'
        doc_perizia = {
            "sinistro_id": s_id,
            "perito_id": int(id_perito), # Cast esplicito a intero per uniformità con MySQL
            "data_perizia": data.get("data_perizia"),
            "ora_perizia": data.get("ora_perizia"),
            "note_tecniche": data.get("note_tecniche"),
            "documenti": data.get("documenti", []),
            "stato": "aperta",
            "data_inserimento": datetime.now() # Timestamp di creazione gestito dal server
        }

        # Esecuzione del comando di inserimento (Create)
        res = db.perizie.insert_one(doc_perizia)
        perizia_id = res.inserted_id

        # Aggiornamento dello stato del sinistro (Update) utilizzando l'operatore atomico $set
        db.sinistri.update_one(
            {"_id": s_id},
            {"$set": {
                "stato": "in_perizia",
                "perito_id": int(id_perito),
                "perizia_id": perizia_id,
                "data_aggiornamento": datetime.now()
            }}
        )

        # Ritorna il codice HTTP 201 (Created) con l'ID del nuovo documento creato
        return jsonify({
            "status": "Pratica creata e Perito verificato", 
            "id_perizia": str(perizia_id)
        }), 201

    except Exception as e:
        # Gestione generica degli errori con ritorno del codice 500 (Server Error)
        return jsonify({"error": str(e)}), 500
    finally:
        # Pattern fondamentale: rilascio delle risorse (connessione e cursore) in ogni caso
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# B. REGISTRAZIONE RIMBORSO
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/rimborso', methods=['POST'])
def registra_rimborso(id_sinistro, id_perito, id_perizia):
    """
    Aggiorna i documenti su MongoDB per riflettere l'esito della perizia e la proposta di rimborso.
    Non richiede MySQL perché opera su dati documentali già validati in precedenza.
    """
    try:
        data = request.get_json()
        
        # Aggiornamento della singola perizia: inserisce stima economica ed esito finale
        db.perizie.update_one(
            {"_id": ObjectId(id_perizia)},
            {"$set": {
                "stima_danno": data.get("stima_danno"),
                "esito": data.get("esito"),
                "stato": "rimborso_inserito",
                "data_aggiornamento": datetime.now()
            }}
        )
        
        # Aggiornamento dello stato globale del sinistro per la dashboard dell'utente
        db.sinistri.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {
                "stato": "rimborso_proposto", 
                "data_aggiornamento": datetime.now()
            }}
        )
        return jsonify({"status": "Rimborso salvato correttamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# C. ASSEGNAZIONE INTERVENTO
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/intervento', methods=['POST'])
def assegna_intervento(id_sinistro, id_perito, id_perizia):
    """
    Assegna il sinistro a un'officina convenzionata.
    Valida l'esistenza dell'Officina su MySQL prima di procedere con l'aggiornamento su MongoDB.
    """
    conn = None
    try:
        data = request.get_json()
        id_officina = data.get("id_officina")

        # --- VALIDAZIONE MYSQL ---
        # Interrogazione del DB Relazionale per garantire la coerenza tra i sistemi
        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Officina WHERE id = %s", (id_officina,))
        officina = cursor.fetchone()

        # Controllo di esistenza dell'officina
        if not officina:
            return jsonify({"error": f"Officina con ID {id_officina} non esistente"}), 404

        # --- OPERAZIONE MONGODB ---
        # Aggiorna il sinistro impostando l'ID dell'officina esterna e cambiando lo stato in riparazione
        db.sinistri.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {
                "id_officina": id_officina,
                "stato": "in_riparazione",
                "data_inizio_lavori": data.get("data_inizio_lavori"),
                "data_aggiornamento": datetime.now()
            }}
        )
        
        # Sincronizza lo stato della perizia per chiudere il flusso del perito
        db.perizie.update_one(
            {"_id": ObjectId(id_perizia)},
            {"$set": {
                "stato": "inviata_officina", 
                "id_officina": id_officina
            }}
        )
        return jsonify({"status": "Intervento assegnato e Officina verificata"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Chiusura sicura della connessione al database MySQL
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    # Avvio del server Flask in modalità debug per facilitare lo sviluppo (Hot Reload)
    app.run(host='0.0.0.0', port=5000, debug=True)