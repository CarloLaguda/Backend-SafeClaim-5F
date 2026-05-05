from flask import Flask, request, jsonify
import mysql.connector
import re
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── Configurazione MySQL ────────────────────────────────────────────────────
MYSQL_CONFIG = {
    "host":     "db.giobra.com",
    "port":     3306,
    "user":     "user",
    "password": "xxx123##",
    "database": "Prototipo_SafeClaim",
}

MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123%23%23@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db     = mongo_client['FakeClaim']
    sinistri_col = mongo_db['Sinistri']
    mongo_client.admin.command('ping')
    print("✅ Connessione a MongoDB Atlas (FakeClaim) riuscita!")
except Exception as e:
    print(f"❌ Errore connessione MongoDB: {e}")

def get_mysql_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

# Valori ammessi per tipo_copertura (aggiornati con Furto_Incendio e Full)
TIPI_COPERTURA = {'RCA', 'Kasko', 'Furto_Incendio', 'Full'}
# Valori ammessi per tipo_documento di Polizza_Documenti
TIPI_DOCUMENTO_POLIZZA = {'polizza_pdf', 'quietanza', 'appendice', 'attestato_rischio'}

# ── CRUD Polizze ─────────────────────────────────────────────────────────────

@app.route('/polizze', methods=['POST'])
def crea_polizza():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    tipo_copertura = data.get('tipo_copertura', 'RCA')
    if tipo_copertura not in TIPI_COPERTURA:
        return jsonify({"error": f"tipo_copertura non valido. Valori ammessi: {TIPI_COPERTURA}"}), 400

    conn = get_mysql_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO Polizza (n_polizza, compagnia_assicurativa, data_inizio,
        data_scadenza, massimale, tipo_copertura, veicolo_id, assicuratore_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        data['n_polizza'], data.get('compagnia_assicurativa'),
        data['data_inizio'], data['data_scadenza'],
        data.get('massimale'), tipo_copertura,
        data['veicolo_id'], data.get('assicuratore_id'),
    )
    try:
        cursor.execute(query, values)
        conn.commit()
        return jsonify({"message": "Polizza inserita!", "id": cursor.lastrowid}), 201
    except mysql.connector.IntegrityError as e:
        return jsonify({"error": f"Vincolo violato: {str(e)}"}), 409
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
    # Conversione date per la serializzazione JSON
    for r in risultati:
        for campo in ('data_inizio', 'data_scadenza'):
            if r.get(campo) and hasattr(r[campo], 'isoformat'):
                r[campo] = r[campo].isoformat()
    cursor.close()
    conn.close()
    return jsonify(risultati), 200

@app.route('/polizze/<int:id>', methods=['GET'])
def leggi_polizza(id):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Polizza WHERE id = %s", (id,))
    polizza = cursor.fetchone()
    cursor.close()
    conn.close()
    if not polizza:
        return jsonify({"error": "Polizza non trovata"}), 404
    for campo in ('data_inizio', 'data_scadenza'):
        if polizza.get(campo) and hasattr(polizza[campo], 'isoformat'):
            polizza[campo] = polizza[campo].isoformat()
    return jsonify(polizza), 200

@app.route('/polizze/<int:id>', methods=['PUT'])
def modifica_polizza(id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Nessun dato fornito"}), 400

    if 'tipo_copertura' in data and data['tipo_copertura'] not in TIPI_COPERTURA:
        return jsonify({"error": f"tipo_copertura non valido. Valori ammessi: {TIPI_COPERTURA}"}), 400

    conn = get_mysql_connection()
    cursor = conn.cursor()
    query = """
        UPDATE Polizza
        SET n_polizza=%s, compagnia_assicurativa=%s, data_inizio=%s,
            data_scadenza=%s, massimale=%s, tipo_copertura=%s
        WHERE id=%s
    """
    values = (
        data.get('n_polizza'), data.get('compagnia_assicurativa'),
        data.get('data_inizio'), data.get('data_scadenza'),
        data.get('massimale'), data.get('tipo_copertura'), id,
    )
    try:
        cursor.execute(query, values)
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Polizza non trovata"}), 404
        return jsonify({"message": "Polizza aggiornata con successo"}), 200
    except Exception as e:
        print(f"Errore DB: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/polizze/<int:id>', methods=['DELETE'])
def elimina_polizza(id):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Polizza WHERE id=%s", (id,))
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()
    if affected == 0:
        return jsonify({"error": "Polizza non trovata"}), 404
    return jsonify({"message": "Polizza eliminata"}), 200

# ── Documenti polizza (Polizza_Documenti) ────────────────────────────────────
# Nota: tipo_documento ora accetta anche 'appendice' e 'attestato_rischio'

@app.route('/polizze/<int:polizza_id>/documenti', methods=['POST'])
def aggiungi_documento_polizza(polizza_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    tipo_documento = data.get('tipo_documento')
    if tipo_documento not in TIPI_DOCUMENTO_POLIZZA:
        return jsonify({"error": f"tipo_documento non valido. Valori ammessi: {TIPI_DOCUMENTO_POLIZZA}"}), 400

    conn = get_mysql_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Polizza_Documenti (polizza_id, mongo_doc_id, tipo_documento, descrizione) VALUES (%s,%s,%s,%s)",
            (polizza_id, data['mongo_doc_id'], tipo_documento, data.get('descrizione'))
        )
        conn.commit()
        return jsonify({"message": "Documento aggiunto", "id": cursor.lastrowid}), 201
    except mysql.connector.IntegrityError as e:
        return jsonify({"error": f"Polizza non trovata o vincolo violato: {str(e)}"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/polizze/<int:polizza_id>/documenti', methods=['GET'])
def leggi_documenti_polizza(polizza_id):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Polizza_Documenti WHERE polizza_id = %s", (polizza_id,))
    risultati = cursor.fetchall()
    for r in risultati:
        if r.get('data_inserimento') and hasattr(r['data_inserimento'], 'isoformat'):
            r['data_inserimento'] = r['data_inserimento'].isoformat()
    cursor.close()
    conn.close()
    return jsonify(risultati), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)
