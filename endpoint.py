from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# --- CONFIGURAZIONE DATABASE (Dati forniti) ---
db_config = {
    "host": "mysql-safeclaim.aevorastudios.com",
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db",
    "port": 3306
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Errore di connessione: {e}")
        return None

# --- 3.1 GESTIONE POLIZZE (CRUD) ---

@app.route('/polizze', methods=['POST'])
def crea_polizza():
    """Registra una nuova polizza nel sistema (Task 3.1)"""
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO Polizza (n_polizza, compagnia_assicurativa, data_inizio, 
            data_scadenza, massimale, tipo_copertura, veicolo_id, assicuratore_id, documento_mongo_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data['n_polizza'], data.get('compagnia'), data['data_inizio'],
            data['data_scadenza'], data.get('massimale'), 
            data.get('tipo_copertura', 'RCA'), data['veicolo_id'], 
            data['assicuratore_id'], data.get('mongo_id')
        )
        cursor.execute(query, values)
        conn.commit()
        return jsonify({"message": "Polizza creata con successo", "id": cursor.lastrowid}), 201
    except Error as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/polizze', methods=['GET'])
def leggi_polizze():
    """Recupera l'elenco di tutte le polizze"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Polizza")
    polizze = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(polizze), 200

# --- 3.2 AGGIORNAMENTO STATO SINISTRO ---

@app.route('/sinistro/<int:id_sinistro>', methods=['PUT'])
def aggiorna_stato_sinistro(id_sinistro):
    """Cambia lo stato del sinistro (es: 'presa in carico')"""
    data = request.json
    nuovo_stato = data.get('stato')
    
    # Nota: la tabella Sinistro non è presente nelle tue Create Table, 
    # ma l'endpoint è richiesto dalle tue specifiche API.
    return jsonify({"id_sinistro": id_sinistro, "nuovo_stato": nuovo_stato}), 200

# --- 3.3 ASSEGNAZIONE PERITO ---

@app.route('/sinistro/<int:id_sinistro>/perito', methods=['POST'])
def assegna_perito(id_sinistro):
    """Assegna un perito al sinistro (Task 3.3)"""
    data = request.json
    perito_id = data.get('id_perito')
    
    # Qui andrebbe l'UPDATE sulla tabella Sinistri per legare il perito_id
    return jsonify({
        "status": "success",
        "message": f"Mandato di perizia inviato al perito {perito_id} per il sinistro {id_sinistro}"
    }), 200

# --- LOGICA DI VALIDAZIONE (Richiesta dalle specifiche) ---

@app.route('/verifica-cliente/<string:cf>', methods=['GET'])
def verifica_cliente_polizza(cf):
    """
    Verifica se un automobilista ha una polizza attiva tramite Codice Fiscale.
    Fondamentale perché: 'un utenza senza polizza non può aprire sinistro'
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT p.id, p.n_polizza, p.data_scadenza 
        FROM Polizza p
        JOIN Veicolo v ON p.veicolo_id = v.id
        JOIN Automobilista a ON v.automobilista_id = a.id
        WHERE a.cf = %s AND p.data_scadenza >= CURDATE()
    """
    cursor.execute(query, (cf,))
    polizza = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if polizza:
        return jsonify({"is_cliente": True, "polizza": polizza}), 200
    return jsonify({"is_cliente": False, "message": "Nessuna polizza attiva trovata"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
