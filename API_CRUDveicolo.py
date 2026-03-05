import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_FILE = "safeclaim_test.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row 
    return conn

# --- CRUD AUTOMOBILISTA (Necessario per creare l'ID proprietario) ---
@app.route('/automobilisti', methods=['POST'])
def crea_automobilista():
    data = request.json
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Automobilista (nome, cognome, cf, email, psw) VALUES (?, ?, ?, ?, ?)",
            (data['nome'], data['cognome'], data['cf'], data['email'], data['psw'])
        )
        conn.commit()
        return jsonify({"message": "Automobilista creato!", "id": cur.lastrowid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()

# --- CRUD VEICOLO (Collegato all'utente) ---

@app.route('/veicoli', methods=['POST'])
def crea_veicolo_via_cf():
    data = request.json
    
    # Verifichiamo che ci sia il CF invece dell'ID
    if 'cf' not in data:
        return jsonify({"error": "Codice Fiscale ('cf') mancante"}), 400
        
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # 1. Trova l'ID dell'automobilista usando il CF
        cf_upper = data['cf'].upper()
        utente = cur.execute("SELECT id FROM Automobilista WHERE cf = ?", (cf_upper,)).fetchone()
        
        if not utente:
            return jsonify({"error": f"Nessun automobilista trovato con CF: {cf_upper}"}), 404
        
        automobilista_id = utente['id']

        # 2. Inserisci il veicolo usando l'ID trovato
        query = """INSERT INTO Veicolo (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id) 
                   VALUES (?, ?, ?, ?, ?, ?)"""
        cur.execute(query, (
            data['targa'], 
            data.get('n_telaio'), 
            data.get('marca'), 
            data.get('modello'), 
            data.get('anno_immatricolazione'), 
            automobilista_id
        ))
        
        conn.commit()
        return jsonify({
            "message": "Veicolo collegato con successo!",
            "id_veicolo": cur.lastrowid,
            "collegato_a_id": automobilista_id
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Questa targa è già registrata"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# Recupera i veicoli partendo dal Codice Fiscale dell'automobilista
@app.route('/automobilisti/cf/<string:codice_fiscale>/veicoli', methods=['GET'])
def leggi_veicoli_da_cf(codice_fiscale):
    conn = get_db_connection()
    try:
        # Trasformiamo il CF in maiuscolo per evitare errori di battitura
        cf_upper = codice_fiscale.upper()
        
        # Facciamo una JOIN per trovare i veicoli collegati a quel CF
        query = """
            SELECT v.* FROM Veicolo v
            JOIN Automobilista a ON v.automobilista_id = a.id
            WHERE a.cf = ?
        """
        veicoli = conn.execute(query, (cf_upper,)).fetchall()
        
        if not veicoli:
            # Verifichiamo se l'utente esiste ma non ha auto, o se non esiste proprio
            utente = conn.execute("SELECT id FROM Automobilista WHERE cf = ?", (cf_upper,)).fetchone()
            if not utente:
                return jsonify({"error": "Nessun automobilista trovato con questo Codice Fiscale"}), 404
            return jsonify([]), 200
            
        return jsonify([dict(row) for row in veicoli]), 200
    finally:
        conn.close()

# DELETE: Rimuove un veicolo specifico
@app.route('/veicoli/<int:id>', methods=['DELETE'])
def elimina_veicolo(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM Veicolo WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Veicolo rimosso"}), 200

if __name__ == '__main__':
    app.run(port=5002, debug=True)