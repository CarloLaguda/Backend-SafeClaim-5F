from flask import Flask, request, jsonify
from flask_cors import CORS  # 1. Importa CORS
import mysql.connector

app = Flask(__name__)

# 2. Configura CORS
# 'CORS(app)' abilita l'accesso da qualsiasi dominio (per sviluppo è perfetto)
CORS(app) 

# Credenziali fornite per MySQL
db_config = {
    "host": "mysql-safeclaim.aevorastudios.com",
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db",
    "port": 3306
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- CRUD POLIZZE ---

# CREATE: Inserimento nuova polizza
@app.route('/polizze', methods=['POST'])
def crea_polizza():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Formato non valido, serve JSON"}), 415
        
    conn = get_db_connection()
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

# READ: Elenco polizze
@app.route('/polizze', methods=['GET'])
def leggi_polizze():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Polizza")
    risultati = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(risultati), 200

# UPDATE: Modifica polizza
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

# DELETE: Elimina polizza
@app.route('/polizze/<int:id>', methods=['DELETE'])
def elimina_polizza(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Polizza WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Polizza eliminata"}), 200

if __name__ == '__main__':
    # Ricorda di installare con: pip install flask-cors
    app.run(port=5000, debug=True)