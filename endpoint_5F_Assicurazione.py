from flask import Flask, request, jsonify
import mysql.connector
import re
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from flask_cors import CORS
from dotenv import load_dotenv
app = Flask(__name__)
CORS(app)
import os

# --- CONFIGURAZIONI DATABASE ---

# Configurazione MySQL
load_dotenv()

MYSQL_CONFIG = {
    "host":     os.getenv("MYSQL_HOST"),
    "port":     int(os.getenv("MYSQL_PORT", 3306)),
    "user":     os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
}

MONGO_URI = os.getenv("MONGO_URI")

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Database rinominato in 'FakeClaim' come da tua configurazione Atlas
    mongo_db = mongo_client['FakeClaim']
    sinistri_col = mongo_db['Sinistri']
    
    # Verifica immediata della connessione
    mongo_client.admin.command('ping')
    print("Connessione a MongoDB Atlas (FakeClaim) riuscita!")
except Exception as e:
    print(f"Errore critico connessione MongoDB: {e}")

def get_mysql_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

# endpoint_5F_Assicurazione.py - modifiche principali
@app.route('/pratiche_assicurazione', methods=['GET'])
def get_pratiche_assicurazione():
    try:
        # ... (logica già presente in Periti, resa coerente)
        pratiche = list(col_pratiche.find())
        for p in pratiche:
            p['_id'] = str(p['_id'])
            # Embed sinistro + immagini + perizia
            if sin_id := p.get('sinistro_id'):
                sinistro = col_sinistri.find_one({"_id": ObjectId(sin_id)})
                if sinistro:
                    sinistro['_id'] = str(sinistro['_id'])
                    p['sinistro'] = {
                        **{k: v for k, v in sinistro.items() if k in ['targa', 'marca', 'modello', 'descrizione', 'luogo', 'data_evento', 'stato']},
                        'immagini': sinistro.get('immagini', []),
                        'analisi_ai': sinistro.get('analisi_ai', {})
                    }
        return jsonify({"totale": len(pratiche), "pratiche": pratiche}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

@app.route('/veicoli-utente/<int:user_id>', methods=['GET'])
def get_veicoli_utente(user_id):
    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        # Questa query va a cercare nel tuo MySQL i veicoli di quell'utente
        # user_id = Utente.id → join su Automobilista.id_utente
        query = """
            SELECT v.* FROM Veicolo v
            JOIN Automobilista a ON v.automobilista_id = a.id
            WHERE a.id_utente = %s
        """
        cursor.execute(query, (user_id,))
        veicoli = cursor.fetchall()
        return jsonify(veicoli), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


TIPI_COPERTURA = {'RCA', 'Kasko', 'Furto_Incendio', 'Full'}

@app.route('/registrazione-completa', methods=['POST'])
def registrazione_completa():
    """
    Registrazione completa fatta dall'assicuratore in 3 step (frontend):
      Step 1 – dati utente (nome, cognome, email, telefono, password_hash, cf)
      Step 2 – dati veicolo (targa, n_telaio, marca, modello, anno_immatricolazione)
      Step 3 – dati polizza (n_polizza, compagnia_assicurativa, data_inizio,
                             data_scadenza, massimale, tipo_copertura,
                             assicuratore_utente_id)

    Tutto viene salvato in un'unica transazione atomica.

    Body JSON atteso:
    {
        "utente":  { "nome", "cognome", "email", "telefono", "password_hash", "cf" },
        "veicolo": { "targa", "n_telaio", "marca", "modello", "anno_immatricolazione" },
        "polizza": { "n_polizza", "compagnia_assicurativa", "data_inizio",
                     "data_scadenza", "massimale", "tipo_copertura",
                     "assicuratore_utente_id" }
    }
    """
    import re

    data = request.get_json()
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    dati_utente  = data.get('utente',  {})
    dati_veicolo = data.get('veicolo', {})
    dati_polizza = data.get('polizza', {})

    # ── Validazioni campi obbligatori ───────────────────────────────────────
    for campo in ['nome', 'cognome', 'email', 'password_hash', 'cf']:
        if not dati_utente.get(campo):
            return jsonify({"error": f"Campo utente mancante: {campo}"}), 400
    for campo in ['targa']:
        if not dati_veicolo.get(campo):
            return jsonify({"error": f"Campo veicolo mancante: {campo}"}), 400
    for campo in ['n_polizza', 'data_inizio', 'data_scadenza']:
        if not dati_polizza.get(campo):
            return jsonify({"error": f"Campo polizza mancante: {campo}"}), 400

    tipo_copertura = dati_polizza.get('tipo_copertura', 'RCA')
    if tipo_copertura not in TIPI_COPERTURA:
        return jsonify({"error": f"tipo_copertura non valido. Ammessi: {TIPI_COPERTURA}"}), 400

    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        # ── 1. Crea Utente ──────────────────────────────────────────────────
        cursor.execute(
            """INSERT INTO Utente (nome, cognome, email, telefono, password_hash, ruolo)
               VALUES (%s, %s, %s, %s, %s, 'automobilista')""",
            (
                dati_utente['nome'].strip().title(),
                dati_utente['cognome'].strip().title(),
                dati_utente['email'].strip().lower(),
                dati_utente.get('telefono'),
                dati_utente['password_hash'],
            )
        )
        utente_id = cursor.lastrowid

        # ── 2. Crea Automobilista (con n_polizza già assegnato) ─────────────
        n_polizza = dati_polizza.get('n_polizza')
        cursor.execute(
            """INSERT INTO Automobilista (nome, cognome, cf, id_utente, n_polizza)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                dati_utente['nome'].strip().title(),
                dati_utente['cognome'].strip().title(),
                dati_utente['cf'].strip().upper(),
                utente_id,
                n_polizza,
            )
        )
        automobilista_id = cursor.lastrowid

        # ── 3. Crea Veicolo legato all'Automobilista ────────────────────────
        cursor.execute(
            """INSERT INTO Veicolo (targa, n_telaio, marca, modello,
                                    anno_immatricolazione, automobilista_id)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                dati_veicolo.get('targa'),
                dati_veicolo.get('n_telaio'),
                dati_veicolo.get('marca'),
                dati_veicolo.get('modello'),
                dati_veicolo.get('anno_immatricolazione'),
                automobilista_id,
            )
        )
        veicolo_id = cursor.lastrowid

        # ── 4. Risolve assicuratore_id dall'id_utente dell'assicuratore ─────
        assicuratore_id = None
        ass_utente_id = dati_polizza.get('assicuratore_utente_id')
        if ass_utente_id:
            cursor.execute(
                "SELECT id FROM Assicuratore WHERE id_utente = %s", (ass_utente_id,)
            )
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                return jsonify({"error": f"Assicuratore con id_utente={ass_utente_id} non trovato"}), 404
            assicuratore_id = row['id']

        # ── 5. Crea Polizza ─────────────────────────────────────────────────
        cursor.execute(
            """INSERT INTO Polizza (n_polizza, compagnia_assicurativa, data_inizio,
                                    data_scadenza, massimale, tipo_copertura,
                                    veicolo_id, assicuratore_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                n_polizza,
                dati_polizza.get('compagnia_assicurativa'),
                dati_polizza['data_inizio'],
                dati_polizza['data_scadenza'],
                dati_polizza.get('massimale'),
                tipo_copertura,
                veicolo_id,
                assicuratore_id,
            )
        )
        polizza_id = cursor.lastrowid

        conn.commit()

        return jsonify({
            "status":           "success",
            "message":          "Registrazione completa effettuata",
            "utente_id":        utente_id,
            "automobilista_id": automobilista_id,
            "veicolo_id":       veicolo_id,
            "polizza_id":       polizza_id,
            "n_polizza":        n_polizza,
        }), 201

    except mysql.connector.IntegrityError as e:
        if conn:
            conn.rollback()
        msg = str(e)
        if 'email' in msg.lower() or 'cf' in msg.lower():
            return jsonify({"error": "Email o Codice Fiscale già registrati"}), 409
        if 'targa' in msg.lower() or 'n_telaio' in msg.lower():
            return jsonify({"error": "Targa o numero telaio già esistente"}), 409
        if 'n_polizza' in msg.lower():
            return jsonify({"error": "Numero polizza già esistente"}), 409
        return jsonify({"error": f"Violazione integrità DB: {msg}"}), 409
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()



@app.route('/veicolo/user/<int:user_id>', methods=['POST'])
def crea_veicolo_utente(user_id):
    data = request.get_json()
    if not data or not data.get('targa'):
        return jsonify({"error": "Campo obbligatorio mancante: targa"}), 400
    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM Automobilista WHERE id_utente = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Utente {user_id} non trovato"}), 404
        cursor.execute(
            "INSERT INTO Veicolo (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (data.get('targa'), data.get('n_telaio'), data.get('marca'), data.get('modello'), data.get('anno_immatricolazione'), user_id)
        )
        conn.commit()
        return jsonify({"status": "success", "veicolo_id": cursor.lastrowid}), 201
    except mysql.connector.IntegrityError:
        if conn: conn.rollback()
        return jsonify({"error": "Targa o numero telaio già esistente"}), 409
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

        
if __name__ == '__main__':
    # Mantenuta porta 6000 come da tua ultima riga
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)