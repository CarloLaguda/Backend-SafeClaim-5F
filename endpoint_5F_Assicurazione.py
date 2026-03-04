from flask import Flask, request, jsonify
import mysql.connector
import re
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

# --- CONFIGURAZIONI DATABASE ---

# Configurazione MySQL
db_config = {
    "host": "mysql-safeclaim.aevorastudios.com",
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db",
    "port": 3306
}

# --- NUOVA CONFIGURAZIONE MONGODB ATLAS ---
# Stringa aggiornata con il nuovo cluster Atlas
MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123%23%23@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Database rinominato in 'FakeClaim' come da tua configurazione Atlas
    mongo_db = mongo_client['FakeClaim']
    sinistri_col = mongo_db['Sinistro']
    
    # Verifica immediata della connessione
    mongo_client.admin.command('ping')
    print("Connessione a MongoDB Atlas (FakeClaim) riuscita!")
except Exception as e:
    print(f"Errore critico connessione MongoDB: {e}")

def get_mysql_connection():
    return mysql.connector.connect(**db_config)

# --- UTILITY VALIDAZIONE ---

def valida_password(password):
    if len(password) < 8:
        return False, "La password deve essere lunga almeno 8 caratteri."
    if not re.search(r"[a-zA-Z]", password):
        return False, "La password deve contenere almeno una lettera."
    if not re.search(r"\d", password):
        return False, "La password deve contenere almeno un numero."
    return True, None

def valida_dati_utente(data):
    pattern_nomi = r"^[a-zA-Zàáâäãåèéêëìíîïòóôöùúûüç \s']+$"
    if not re.match(pattern_nomi, data.get('nome', '')):
        return False, "Il nome non è valido."
    if not re.match(pattern_nomi, data.get('cognome', '')):
        return False, "Il cognome non è valido."
    if not re.match(r'^[A-Z0-9]{16}$', data.get('cf', '').upper()):
        return False, "Il CF deve essere di 16 caratteri alfanumerici."
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data.get('email', '')):
        return False, "Formato email non valido."
    
    valida_psw, err_psw = valida_password(data.get('psw', ''))
    if not valida_psw:
        return False, err_psw
    return True, None

# --- CRUD POLIZZE (MySQL) ---

@app.route('/polizze', methods=['POST'])
def crea_polizza():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO Polizza (n_polizza, compagnia_assicurativa, data_inizio, 
        data_scadenza, massimale, tipo_copertura, veicolo_id, assicuratore_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (data['n_polizza'], data.get('compagnia_assicurativa'), data['data_inizio'],
              data['data_scadenza'], data.get('massimale'), data.get('tipo_copertura', 'RCA'), 
              data['veicolo_id'], data['assicuratore_id'])
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
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Polizza")
    risultati = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(risultati), 200

@app.route('/polizze/<int:id>', methods=['PUT'])
def modifica_polizza(id):
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "UPDATE Polizza SET n_polizza=%s, data_scadenza=%s WHERE id=%s"
    cursor.execute(query, (data['n_polizza'], data['data_scadenza'], id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Polizza aggiornata"}), 200

@app.route('/polizze/<int:id>', methods=['DELETE'])
def elimina_polizza(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Polizza WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Polizza eliminata"}), 200

# --- ENDPOINT SINISTRI (GET) ---

@app.route('/sinistri', defaults={'id_sinistro': None}, methods=['GET'])
@app.route('/sinistri/<id_sinistro>', methods=['GET'])
def ottieni_sinistri(id_sinistro):
    try:
        if id_sinistro:
            if not ObjectId.is_valid(id_sinistro):
                return jsonify({"error": "Formato ID non valido"}), 400
            
            sinistro = sinistri_col.find_one({"_id": ObjectId(id_sinistro)})
            if not sinistro:
                return jsonify({"error": "Sinistro non trovato"}), 404

            sinistro['_id'] = str(sinistro['_id'])
            return jsonify(sinistro), 200
        else:
            cursor = sinistri_col.find()
            lista = []
            for s in cursor:
                s['_id'] = str(s['_id'])
                lista.append(s)
            return jsonify({"count": len(lista), "data": lista}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- REGISTRAZIONE & LOGIN (MySQL) ---

@app.route('/registrazione', methods=['POST'])
def registrazione():
    data = request.get_json()
    if not data: return jsonify({"error": "Nessun dato ricevuto"}), 400

    is_valid, error_message = valida_dati_utente(data)
    if not is_valid: return jsonify({"error": error_message}), 400

    connection = None
    try:
        connection = get_mysql_connection()
        cursor = connection.cursor()
        query = "INSERT INTO Automobilista (nome, cognome, cf, email, psw) VALUES (%s, %s, %s, %s, %s)"
        values = (data['nome'].strip().title(), data['cognome'].strip().title(), 
                  data['cf'].strip().upper(), data['email'].strip().lower(), data['psw'])
        cursor.execute(query, values)
        connection.commit()
        return jsonify({"status": "success", "id": cursor.lastrowid}), 201
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Email o CF già registrati"}), 409
    finally:
        if connection: connection.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email_in, psw_in = data.get('email'), data.get('psw')
    if not email_in or not psw_in: return jsonify({"error": "Credenziali mancanti"}), 400

    db = get_mysql_connection()
    cursor = db.cursor(dictionary=True)
    tabelle = ["Assicuratore", "Automobilista", "Perito"]
    user_found, ruolo = None, ""

    for tabella in tabelle:
        query = f"SELECT id, nome, cognome, email FROM {tabella} WHERE email = %s AND psw = %s"
        cursor.execute(query, (email_in, psw_in))
        user_found = cursor.fetchone()
        if user_found:
            ruolo = tabella.lower()
            break
    
    db.close()
    if user_found:
        user_found['ruolo'] = ruolo
        return jsonify({"status": "success", "user": user_found}), 200
    return jsonify({"error": "Credenziali non valide"}), 401

# --- GESTIONE SINISTRI (PUT - MongoDB Atlas) ---

@app.route('/sinistro/<id_sinistro>/perito', methods=['PUT'])
def assegna_perito(id_sinistro):
    try:
        data = request.get_json()
        id_perito = data.get('id_perito')
        if id_perito is None: return jsonify({"error": "id_perito mancante"}), 400

        result = sinistri_col.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {"perito_id": id_perito, "stato": "assegnato_a_perito", "data_assegnazione": datetime.now()}}
        )
        if result.matched_count > 0:
            return jsonify({"status": "success", "message": "Perito assegnato"}), 200
        return jsonify({"error": "Sinistro non trovato"}), 404
    except Exception as e:
        return jsonify({"error": "ID malformato o errore server"}), 400

@app.route('/sinistro/<id>', methods=['PUT'])
def aggiorna_sinistro(id):
    data = request.json
    campi_ammessi = ['stato', 'descrizione', 'perizia_id', 'officina_id', 'documenti_allegati']
    update_query = {k: v for k, v in data.items() if k in campi_ammessi}
    
    if not update_query: return jsonify({"error": "Dati non validi"}), 400

    try:
        if not ObjectId.is_valid(id): return jsonify({"error": "ID malformato"}), 400
        
        result = sinistri_col.update_one({"_id": ObjectId(id)}, {"$set": update_query})
        if result.matched_count == 0: return jsonify({"error": "Sinistro non trovato"}), 404

        return jsonify({"messaggio": "Aggiornato su Atlas", "campi": list(update_query.keys())}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Mantenuta porta 6000 come da tua ultima riga
    app.run(host='0.0.0.0', port=6000, debug=True)