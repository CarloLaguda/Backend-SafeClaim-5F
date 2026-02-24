from flask import Flask, request, jsonify
import mysql.connector
import re
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import urllib.parse

app = Flask(__name__)

# --- CONFIGURAZIONI DATABASE ---

# Configurazione MySQL
db_config = {
    "host": "mysql-safeclaim.aevorastudios.com",
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db",
    "port": 3306
}

# Configurazione MongoDB
MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client['safeclaim_mongo']
sinistri_col = mongo_db['Sinistro']

def get_mysql_connection():
    return mysql.connector.connect(**db_config)

# REGISTRAZIONE
def valida_password(password):
    """Verifica che la password abbia 8 caratteri, lettere e numeri."""
    if len(password) < 8:
        return False, "La password deve essere lunga almeno 8 caratteri."
    if not re.search(r"[a-zA-Z]", password):
        return False, "La password deve contenere almeno una lettera."
    if not re.search(r"\d", password):
        return False, "La password deve contenere almeno un numero."
    return True, None

def valida_dati_utente(data):
    """Esegue tutti i controlli di robustezza sui dati ricevuti."""
    pattern_nomi = r"^[a-zA-Zàáâäãåèéêëìíîïòóôöùúûüç \s']+$"
    
    if not re.match(pattern_nomi, data.get('nome', '')):
        return False, "Il nome non è valido o contiene numeri."
    
    if not re.match(pattern_nomi, data.get('cognome', '')):
        return False, "Il cognome non è valido o contiene numeri."
    
    if not re.match(r'^[A-Z0-9]{16}$', data.get('cf', '').upper()):
        return False, "Il CF deve essere di esattamente 16 caratteri alfanumerici."
    
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data.get('email', '')):
        return False, "Formato email non valido."
    
    # Validazione password
    valida_psw, err_psw = valida_password(data.get('psw', ''))
    if not valida_psw:
        return False, err_psw
        
    return True, None

@app.route('/registrazione', methods=['POST'])
def registrazione():
    # Ricezione dei dati JSON
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    # 1. Validazione Robustezza (quella che abbiamo testato in console)
    is_valid, error_message = valida_dati_utente(data)
    if not is_valid:
        return jsonify({"error": error_message}), 400

    # 2. Inserimento nel Database
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        query = """
        INSERT INTO Automobilista (nome, cognome, cf, email, psw) 
        VALUES (%s, %s, %s, %s, %s)
        """
        
        # Pulizia e formattazione finale
        values = (
            data['nome'].strip().title(), 
            data['cognome'].strip().title(), 
            data['cf'].strip().upper(), 
            data['email'].strip().lower(), 
            data['psw'] # Salvata in chiaro come richiesto
        )

        cursor.execute(query, values)
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Automobilista registrato con successo",
            "id": cursor.lastrowid
        }), 201

    except mysql.connector.IntegrityError:
        return jsonify({"error": "Email o Codice Fiscale già registrati."}), 409
    except Error as e:
        return jsonify({"error": f"Errore del database: {str(e)}"}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
# LOGIN MOMENTANEA
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email_in = data.get('email')
        psw_in = data.get('psw')

        if not email_in or not psw_in:
            return jsonify({"error": "Email e password obbligatorie"}), 400

        db = get_mysql_connection()
        cursor = db.cursor(dictionary=True)
        
        # Lista delle tabelle in cui cercare l'utente
        tabelle = ["Assicuratore", "Automobilista", "Perito"]
        user_found = None
        ruolo_scoperto = ""

        for tabella in tabelle:
            # Cerchiamo nelle tabelle usando i nomi colonne corretti: email e psw
            query = f"SELECT id, nome, cognome, email FROM {tabella} WHERE email = %s AND psw = %s"
            cursor.execute(query, (email_in, psw_in))
            user_found = cursor.fetchone()
            
            if user_found:
                ruolo_scoperto = tabella.lower()
                break

        cursor.close()
        db.close()

        if user_found:
            # Aggiungiamo il ruolo al risultato per il frontend
            user_found['ruolo'] = ruolo_scoperto
            return jsonify({
                "status": "success",
                "message": f"Bentornato {user_found['nome']}",
                "user": user_found
            }), 200
        else:
            return jsonify({"status": "error", "message": "Credenziali non valide"}), 401

    except Exception as e:
        return jsonify({"error": "Errore server", "details": str(e)}), 500
# --- ENDPOINT POLIZZE (MySQL) ---


@app.route('/polizze', methods=['POST'])
def crea_polizza():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Formato non valido, serve JSON"}), 415
    
    conn = get_mysql_connection()
    cursor = conn.cursor()
    
    query = """
        INSERT INTO Polizza (n_polizza, compagnia_assicurativa, data_inizio, 
        data_scadenza, massimale, tipo_copertura, veicolo_id, assicuratore_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        data['n_polizza'], 
        data.get('compagnia_assicurativa'), 
        data['data_inizio'],
        data['data_scadenza'], 
        data.get('massimale'), 
        data.get('tipo_copertura', 'RCA'), 
        data['veicolo_id'], 
        data['assicuratore_id']
    )
    
    try:
        cursor.execute(query, values)
        conn.commit()
        return jsonify({"message": "Polizza inserita!", "id": cursor.lastrowid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/polizze', methods=['GET'])
def leggi_polizze():
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Polizza")
    risultati = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(risultati), 200

@app.route('/polizze/<int:id>', methods=['PUT'])
def modifica_polizza(id):
    data = request.get_json()
    conn = get_mysql_connection()
    cursor = conn.cursor()
    
    try:
        query = "UPDATE Polizza SET n_polizza=%s, data_scadenza=%s WHERE id=%s"
        cursor.execute(query, (data['n_polizza'], data['data_scadenza'], id))
        conn.commit()
        return jsonify({"message": "Polizza aggiornata"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/polizze/<int:id>', methods=['DELETE'])
def elimina_polizza(id):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Polizza WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Polizza eliminata"}), 200

# --- ENDPOINT SINISTRI (MongoDB) ---

@app.route('/sinistro/<id_sinistro>/perito', methods=['PUT'])
def assegna_perito(id_sinistro):
    try:
        data = request.get_json()
        id_perito = data.get('id_perito')
        
        if id_perito is None:
            return jsonify({"error": "Campo 'id_perito' mancante"}), 400

        result = sinistri_col.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {
                "perito_id": id_perito,
                "stato": "assegnato_a_perito",
                "data_assegnazione": datetime.now()
            }}
        )

        if result.matched_count > 0:
            return jsonify({
                "status": "success",
                "message": f"Il perito {id_perito} è stato assegnato al sinistro {id_sinistro}"
            }), 200
        else:
            return jsonify({"error": "Sinistro non trovato"}), 404

    except Exception as e:
        return jsonify({"error": "ID non valido o errore server", "details": str(e)}), 400

# MODIFICA DI DATI DI UN SISNISTRO, PRESA IN CARICO DA PARTE DELL'ASSICURAZIONE
@app.route('/sinistro/<id>', methods=['PUT'])
def aggiorna_sinistro(id):
    """
    Endpoint per aggiornare lo stato e i dettagli di un sinistro esistente.
    Permette l'avanzamento della pratica come richiesto dalla WBS.
    """
    data = request.json
    
    # Campi che la WBS permette di aggiornare durante la gestione della pratica
    campi_ammessi = [
        'stato',                # Es: "IN_PERIZIA", "CHIUSO", "IN_RIPARAZIONE"
        'descrizione',          # Aggiornamenti testuali sulla dinamica
        'perizia_id',           # Collegamento al documento Perizia su MongoDB
        'officina_id',          # ID dell'officina scelta (da MySQL)
        'documenti_allegati'    # Array di ID riferiti a Documenti_Anagrafica
    ]
    
    # Filtro dei dati in input: accettiamo solo i campi definiti sopra
    update_query = {k: v for k, v in data.items() if k in campi_ammessi}
    
    if not update_query:
        return jsonify({"error": "Nessun dato valido fornito per l'aggiornamento"}), 400

    try:
        # Esecuzione dell'aggiornamento su MongoDB tramite ObjectId
        result = sinistri_col.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_query}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato o ID non valido"}), 404

        return jsonify({
            "messaggio": "Sinistro aggiornato con successo",
            "stato_aggiornamento": "OK",
            "campi_modificati": list(update_query.keys())
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante l'aggiornamento: {str(e)}"}), 500

# --- AVVIO APP ---

if __name__ == '__main__':
    # Ho impostato la porta 5000 come default
    app.run(host='0.0.0.0', port=6000, debug=True)