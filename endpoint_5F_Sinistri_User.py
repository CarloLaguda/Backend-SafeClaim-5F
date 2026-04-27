"""
endpoint_5F_Sinistri_User.py — Branch main
Gestione sinistri, soccorso e veicoli.
Le immagini vengono salvate su Cloudinary tramite Storage.py,
poi analizzate in modo asincrono da Joy-Caption (HuggingFace).
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import mysql.connector
from bson import ObjectId
from datetime import datetime, UTC
import urllib.parse
import threading
from gradio_client import Client, handle_file

# Modulo storage Cloudinary
from Storage import carica_immagine

app = Flask(__name__)
CORS(app)

# --- CONFIGURAZIONE DATABASE ---

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "pythonuser",
    "password": "password123",
    "database": "gestione_assicurazioni"
}

def get_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)

# MongoDB Atlas
_pw = urllib.parse.quote_plus("xxx123##")
MONGO_URI = f"mongodb+srv://dbFakeClaim:{_pw}@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db     = mongo_client["FakeClaim"]
    col_pratiche = mongo_db["Pratica"]
    col_perizie  = mongo_db["Perizia"]
    col_sinistri = mongo_db["Sinistri"]
    soccorso_col = mongo_db["Soccorso"]
    mongo_client.admin.command('ping')
    print("✅ Connessione a MongoDB Atlas (FakeClaim) riuscita!")
except Exception as e:
    print(f"❌ Errore connessione MongoDB: {e}")

# --- CONFIGURAZIONE JOY-CAPTION ---

HF_TOKEN = "IL_TUO_TOKEN_QUI"  # <-- Metti il tuo token HuggingFace

PROMPT_PERITO = (
    "Agisci come un perito assicurativo esperto. Analizza l'immagine e descrivi l'incidente "
    "identificando: 1. Punto d'impatto principale. 2. Componenti danneggiati (es. paraurti, "
    "gruppi ottici, cristalli). 3. Entità del danno (graffio, ammaccatura, deformazione strutturale). "
    "Usa un linguaggio tecnico."
)

def analizza_immagine_ai(sinistro_id: str, image_url: str):
    """
    Eseguita in background da un thread separato.
    Passa l'URL Cloudinary a Joy-Caption e salva il risultato su MongoDB.
    """
    try:
        print(f"[AI] Avvio analisi per sinistro {sinistro_id}...")
        client = Client("fancyfeast/joy-caption-beta-one", token=HF_TOKEN)
        risultato_ai = client.predict(
            input_image=handle_file(image_url),
            prompt=PROMPT_PERITO,
            temperature=0.5,
            top_p=0.9,
            max_new_tokens=512,
            log_prompt=True,
            api_name="/chat_joycaption"
        )
        print(f"✅ [AI] Analisi completata per sinistro {sinistro_id}")
        col_sinistri.update_one(
            {"_id": ObjectId(sinistro_id)},
            {"$set": {
                "analisi_ai": {
                    "testo": risultato_ai,
                    "modello": "joy-caption-beta-one",
                    "data_analisi": datetime.now(UTC),
                    "stato": "completata"
                }
            }}
        )
    except Exception as e:
        print(f"[AI] Errore analisi sinistro {sinistro_id}: {e}")
        try:
            col_sinistri.update_one(
                {"_id": ObjectId(sinistro_id)},
                {"$set": {
                    "analisi_ai": {
                        "stato": "errore",
                        "errore": str(e),
                        "data_analisi": datetime.now(UTC)
                    }
                }}
            )
        except Exception:
            pass


# --- ROTTE SINISTRI ---

@app.route('/sinistro', methods=['POST'])
def apri_sinistro():
    data = request.json
    required = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    if not all(k in data for k in required):
        return jsonify({"error": "Campi obbligatori mancanti"}), 400
    try:
        nuovo_sinistro = {
            "automobilista_id": data['automobilista_id'],
            "targa":            data['targa'],
            "data_evento":      data['data_evento'],
            "descrizione":      data['descrizione'],
            "stato":            "APERTO",
            "data_inserimento": datetime.now(UTC),
            "immagini":         [],
            "analisi_ai":       None
        }
        result = col_sinistri.insert_one(nuovo_sinistro)
        return jsonify({"status": "success", "mongo_id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/sinistri', methods=['GET'])
def get_tutti_sinistri():
    try:
        sinistri = list(col_sinistri.find())
        for s in sinistri:
            s['_id'] = str(s['_id'])
        return jsonify(sinistri), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- UPLOAD IMMAGINE + ANALISI AI ---

@app.route('/sinistro/<sinistro_id>/immagini', methods=['POST'])
def aggiungi_immagine(sinistro_id):
    """
    1. Riceve immagine base64
    2. La carica su Cloudinary
    3. Salva URL su MongoDB
    4. Avvia analisi AI in background
    5. Risponde subito con 202
    """
    if not ObjectId.is_valid(sinistro_id):
        return jsonify({"error": "ID sinistro non valido"}), 400

    data = request.json
    if not data or 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        # Verifica che il sinistro esista
        sinistro = col_sinistri.find_one({"_id": ObjectId(sinistro_id)})
        if not sinistro:
            return jsonify({"error": "Sinistro non trovato"}), 404

        # 1. Carica su Cloudinary
        print(f"☁️  Caricamento immagine su Cloudinary per sinistro {sinistro_id}...")
        info_cloudinary = carica_immagine(data['immagine_base64'], sinistro_id)
        print(f"✅ Immagine caricata: {info_cloudinary['secure_url']}")

        # 2. Salva URL su MongoDB + segna analisi in elaborazione
        col_sinistri.update_one(
            {"_id": ObjectId(sinistro_id)},
            {
                "$push": {"immagini": {
                    "url":       info_cloudinary["secure_url"],
                    "public_id": info_cloudinary["public_id"]
                }},
                "$set": {"analisi_ai": {
                    "stato":      "in_elaborazione",
                    "data_avvio": datetime.now(UTC)
                }}
            }
        )

        # 3. Avvia analisi AI in background
        thread = threading.Thread(
            target=analizza_immagine_ai,
            args=(sinistro_id, info_cloudinary["secure_url"]),
            daemon=True
        )
        thread.start()

        # 4. Risponde subito
        return jsonify({
            "status":           "accepted",
            "id_sinistro":      sinistro_id,
            "immagine_url":     info_cloudinary["secure_url"],
            "messaggio":        "Immagine salvata. Analisi AI avviata in background.",
            "analisi_ai_stato": "in_elaborazione"
        }), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/sinistro/<sinistro_id>', methods=['DELETE'])
def elimina_sinistro(sinistro_id):
    if not ObjectId.is_valid(sinistro_id):
        return jsonify({"error": "ID sinistro non valido"}), 400
    try:
        result = col_sinistri.delete_one({"_id": ObjectId(sinistro_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404

        # Cancella anche le perizie collegate
        perizie_eliminate = col_perizie.delete_many({"sinistro_id": sinistro_id})

        return jsonify({
            "status": "eliminato",
            "id": sinistro_id,
            "perizie_eliminate": perizie_eliminate.deleted_count
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POLLING STATO ANALISI AI ---
@app.route('/sinistro/<sinistro_id>/analisi', methods=['GET'])
def get_analisi_ai(sinistro_id):
    if not ObjectId.is_valid(sinistro_id):
        return jsonify({"error": "ID non valido"}), 400
    try:
        sinistro = col_sinistri.find_one(
            {"_id": ObjectId(sinistro_id)},
            {"analisi_ai": 1}
        )
        if not sinistro:
            return jsonify({"error": "Sinistro non trovato"}), 404
        analisi = sinistro.get("analisi_ai")
        if not analisi:
            return jsonify({"stato": "non_avviata"}), 200
        return jsonify(analisi), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- SOCCORSO ---

@app.route('/soccorso', methods=['POST'])
def crea_richiesta_soccorso():
    data = request.json
    targa = data.get('targa')
    if not targa:
        return jsonify({"error": "Targa obbligatoria"}), 400
    conn = None
    try:
        conn = get_mysql()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM Veicolo WHERE targa = %s", (targa,))
        veicolo = cursor.fetchone()
        if not veicolo:
            return jsonify({"error": "Veicolo non trovato"}), 404
        nuovo_soccorso = {
            "veicolo_id":     veicolo['id'],
            "targa":          targa,
            "posizione":      {"lat": data.get('lat'), "lon": data.get('lon')},
            "stato":          "Richiesto",
            "data_richiesta": datetime.now(UTC)
        }
        res = soccorso_col.insert_one(nuovo_soccorso)
        sql = "INSERT INTO Documenti_Anagrafica (entita_tipo, entita_id, mongo_doc_id, tipo_documento) VALUES ('soccorso', %s, %s, 'intervento')"
        cursor.execute(sql, (veicolo['id'], str(res.inserted_id)))
        conn.commit()
        return jsonify({"intervento_id": str(res.inserted_id), "stato": "In attesa"}), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


# --- VEICOLI ---

@app.route('/veicoli-utente/<int:user_id>', methods=['GET'])
def get_veicoli_utente(user_id):
    conn = None
    try:
        conn = get_mysql()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT v.id, v.targa, v.marca, v.modello, v.anno_immatricolazione,
                   a.nome AS nome_proprietario, a.cognome AS cognome_proprietario,
                   az.ragione_sociale AS azienda_proprietaria
            FROM Veicolo v
            LEFT JOIN Automobilista a ON v.automobilista_id = a.id
            LEFT JOIN Azienda az ON v.azienda_id = az.id
            WHERE v.automobilista_id = %s OR v.azienda_id = %s
        """
        cursor.execute(query, (user_id, user_id))
        return jsonify(cursor.fetchall()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/veicolo/user/<int:user_id>', methods=['POST'])
def crea_veicolo_utente(user_id):
    data = request.get_json()

    # Campi obbligatori
    required = ['targa']
    if not all(k in data for k in required):
        return jsonify({"error": "Campo obbligatorio mancante: targa"}), 400

    conn = None
    try:
        conn = get_mysql()
        cursor = conn.cursor(dictionary=True)

        # Verifica che l'automobilista esista
        cursor.execute("SELECT id FROM Automobilista WHERE id = %s", (user_id,))
        utente = cursor.fetchone()
        if not utente:
            return jsonify({"error": f"Utente con id {user_id} non trovato"}), 404

        # Inserisce il veicolo
        query = """
            INSERT INTO Veicolo (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data.get('targa'),
            data.get('n_telaio'),
            data.get('marca'),
            data.get('modello'),
            data.get('anno_immatricolazione'),
            user_id
        ))
        conn.commit()
        nuovo_id = cursor.lastrowid

        return jsonify({
            "status": "success",
            "message": "Veicolo creato con successo",
            "veicolo_id": nuovo_id,
            "automobilista_id": user_id
        }), 201

    except mysql.connector.IntegrityError as e:
        if conn: conn.rollback()
        # Targa o n_telaio duplicati
        return jsonify({"error": "Targa o numero telaio già esistente"}), 409
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# --- PERIZIE ---
@app.route('/sinistro/<sinistro_id>', methods=['GET'])
def get_sinistro_by_id(sinistro_id):
    """
    Restituisce tutti i campi di un sinistro, incluso l'array 'immagini'
    con gli URL Cloudinary e il blocco 'analisi_ai' completo.
    Usato dal pannello di dettaglio del perito.
    """
    if not ObjectId.is_valid(sinistro_id):
        return jsonify({"error": "ID sinistro non valido"}), 400
    try:
        s = col_sinistri.find_one({"_id": ObjectId(sinistro_id)})
        if not s:
            return jsonify({"error": "Sinistro non trovato"}), 404

        s['_id'] = str(s['_id'])

        # Serializza datetime
        if isinstance(s.get('data_evento'), datetime):
            s['data_evento'] = s['data_evento'].isoformat()
        if isinstance(s.get('data_inserimento'), datetime):
            s['data_inserimento'] = s['data_inserimento'].isoformat()

        # Serializza datetime dentro analisi_ai
        analisi = s.get('analisi_ai')
        if analisi and isinstance(analisi.get('data_analisi'), datetime):
            analisi['data_analisi'] = analisi['data_analisi'].isoformat()

        # Assicura che analisi_ai abbia sempre il campo 'stato'
        if not analisi:
            s['analisi_ai'] = {'stato': 'non_avviata'}

        # Assicura che immagini sia sempre una lista
        if 'immagini' not in s or s['immagini'] is None:
            s['immagini'] = []

        return jsonify(s), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7000)
