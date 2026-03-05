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
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "pythonuser",
    "password": "password123",
    "database": "gestione_assicurazioni" # Database aggiornato
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
    return mysql.connector.connect(**MYSQL_CONFIG)

# VEIOCLI 
@app.route('/veicoli', methods=['GET'])
@app.route('/veicoli/<int:id>', methods=['GET'])
def get_veicoli(id=None):
    """GET Unificata: recupera tutti i veicoli o uno specifico per ID"""
    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        if id:
            cursor.execute("SELECT * FROM Veicolo WHERE id = %s", (id,))
            veicolo = cursor.fetchone()
            if not veicolo: return jsonify({"error": "Veicolo non trovato"}), 404
            return jsonify(veicolo), 200
        else:
            cursor.execute("SELECT * FROM Veicolo")
            return jsonify(cursor.fetchall()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/veicoli', methods=['POST'])
def add_veicolo():
    """POST Separata: inserimento nuovo veicolo"""
    data = request.get_json()
    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO Veicolo 
            (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id, azienda_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (data.get('targa'), data.get('n_telaio'), data.get('marca'),
                  data.get('modello'), data.get('anno_immatricolazione'),
                  data.get('automobilista_id'), data.get('azienda_id'))
        cursor.execute(query, values)
        conn.commit()
        return jsonify({"status": "success", "id": cursor.lastrowid}), 201
    except mysql.connector.Error as err:
        return jsonify({"error": "Errore DB", "details": str(err)}), 400
    finally:
        if conn: conn.close()
# --- CRUD POLIZZE (MySQL) ---

@app.route('/polizze', methods=['POST'])
def crea_polizza():
    data = request.get_json()
    conn = get_mysql_connection()
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
    query = "UPDATE Polizza SET n_polizza=%s, data_scadenza=%s WHERE id=%s"
    cursor.execute(query, (data['n_polizza'], data['data_scadenza'], id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Polizza aggiornata"}), 200

@app.route('/polizze/<int:id>', methods=['DELETE'])
def elimina_polizza(id):
    conn = get_mysql_connection()
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
    app.run(host='0.0.0.0', port=5000, debug=True)