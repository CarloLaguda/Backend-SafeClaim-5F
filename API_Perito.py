from flask import Flask, request, jsonify
import mysql.connector
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAZIONE DATABASE ---
# Connessione a MySQL per la gestione dell'anagrafica (Periti, Officine)
MYSQL_CONFIG = {
    "host": "mysql-safeclaim.aevorastudios.com",
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db"
}

# Connessione a MongoDB per la gestione dei documenti dinamici (Sinistri, Perizie)
mongo_client = MongoClient("mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/")
mongo_db = mongo_client["safeclaim_mongo"]

# --- 1. APERTURA PRATICA ---
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica', methods=['POST'])
def crea_pratica(id_sinistro, id_perito):
    """
    Inizializza la pratica verificando il perito su MySQL e salvando 
    i riferimenti ai documenti (foto/file) su MongoDB.
    """
    data = request.get_json()
    
    # 1. Verifica Perito su MySQL per integrità dati
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Perito WHERE id = %s", (id_perito,))
    perito_esiste = cursor.fetchone()
    cursor.close()
    conn.close()

    if not perito_esiste:
        return jsonify({"error": "Perito non trovato"}), 404

    s_id = ObjectId(id_sinistro)

    # 2. Creazione documento Perizia con array 'documenti'
    # Riceve dal JSON una lista di oggetti (es. nome file, URL, tipo documento)
    documenti_perizia = data.get("documenti", []) 

    doc_perizia = {
        "sinistro_id": s_id,
        "perito_id": id_perito,
        "data_perizia": data.get("data_perizia"),
        "ora_perizia": data.get("ora_perizia"),
        "note_tecniche": data.get("note_tecniche"),
        "documenti": documenti_perizia, # Array di file/foto caricati
        "stato": "aperta",
        "data_inserimento": datetime.now()
    }
    
    res = mongo_db.perizie.insert_one(doc_perizia)
    perizia_id = res.inserted_id

    # 3. Aggiornamento Sinistro con i nuovi riferimenti
    update_data = {
        "$set": {
            "stato": "in_perizia",
            "perito_id": id_perito,
            "perizia_id": perizia_id,
            "data_aggiornamento": datetime.now()
        }
    }
    
    mongo_db.sinistri.update_one({"_id": s_id}, update_data)

    return jsonify({
        "status": "Pratica creata con documenti",
        "id_perizia": str(perizia_id),
        "documenti_caricati": len(documenti_perizia)
    }), 201

# --- 2. REGISTRAZIONE RIMBORSO ---
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/rimborso', methods=['POST'], strict_slashes=False)
def registra_rimborso(id_sinistro, id_perito, id_perizia):
    """
    Registra i costi stimati dal perito e aggiorna la pratica per la fase di liquidazione.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON mancante"}), 400

    try:
        s_id = ObjectId(id_sinistro)
        p_id = ObjectId(id_perizia)
    except:
        return jsonify({"error": "Uno degli ID MongoDB non è nel formato corretto"}), 400

    # Aggiornamento della perizia con i dettagli economici (stima danni e ricambi)
    res_perizia = mongo_db.perizie.update_one(
        {"_id": p_id},
        {"$set": {
            "stima_danno": data.get("stima_danno"),
            "esito": data.get("esito"),
            "stato": "rimborso_inserito",
            "data_aggiornamento": datetime.now()
        }}
    )

    if res_perizia.matched_count == 0:
        return jsonify({"error": "Perizia non trovata su MongoDB"}), 404

    # Avanzamento dello stato del sinistro verso la proposta di rimborso
    mongo_db.sinistri.update_one(
        {"_id": s_id},
        {"$set": {
            "stato": "rimborso_proposto",
            "data_aggiornamento": datetime.now()
        }}
    )

    return jsonify({"status": "Successo", "message": "Rimborso salvato correttamente"}), 200

# --- 3. ASSEGNAZIONE INTERVENTO ---
@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/intervento', methods=['GET', 'POST'])
def assegna_intervento(id_sinistro, id_perito, id_perizia):
    """
    Assegna il veicolo a un'officina convenzionata verificata su MySQL.
    """
    if request.method == 'GET':
        return jsonify({"error": "Usa il metodo POST su Postman"}), 405

    data = request.get_json()
    id_officina = data.get("id_officina")

    # Verifica validità dell'officina tramite database relazionale
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Officina WHERE id = %s", (id_officina,))
    officina_esiste = cursor.fetchone()
    cursor.close()
    conn.close()

    if not officina_esiste:
        return jsonify({"error": "Officina non trovata nel database MySQL"}), 404

    try:
        s_id = ObjectId(id_sinistro)
        p_id = ObjectId(id_perizia)
    except:
        return jsonify({"error": "Formato ID MongoDB non valido"}), 400

    # Aggiornamento Sinistro: collegamento con l'officina e avvio fase riparazione
    mongo_db.sinistri.update_one(
        {"_id": s_id},
        {"$set": {
            "id_officina": id_officina,
            "stato": "in_riparazione",
            "data_inizio_lavori": data.get("data_inizio_lavori"),
            "data_aggiornamento": datetime.now()
        }}
    )

    # Allineamento stato della perizia per chiusura workflow tecnico
    mongo_db.perizie.update_one(
        {"_id": p_id},
        {"$set": {"stato": "inviata_officina", "id_officina": id_officina}}
    )

    return jsonify({
        "status": "Successo", 
        "message": "Intervento assegnato all'officina correttamente",
        "nuovo_stato": "in_riparazione"
    }), 200

if __name__ == '__main__':
    # Avvio del server Flask in modalità debug per lo sviluppo
    app.run(debug=True)