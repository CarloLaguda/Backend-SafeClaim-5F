"""
endpoint_5F_log_reg.py — Branch 5F
Gestione sinistri, soccorso e veicoli.
Le immagini vengono salvate su Cloudinary tramite Storage.py,
poi analizzate in modo asincrono da Joy-Caption (HuggingFace).
"""

from flask import Flask, request, jsonify
from datetime import datetime, UTC
import mysql.connector
import pymongo
from bson.objectid import ObjectId
from flask_cors import CORS
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

def get_db_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

# MongoDB Atlas
MONGO_URI = "mongodb+srv://dbFakeClaim:xxx123%23%23@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client["FakeClaim"]
    sinistri_col = mongo_db["Sinistro"]
    soccorso_col = mongo_db["Soccorso"]

    mongo_client.admin.command('ping')
    print("Connessione a MongoDB Atlas riuscita!")
except Exception as e:
    print(f"Errore connessione MongoDB: {e}")

# --- CONFIGURAZIONE JOY-CAPTION ---

HF_TOKEN = "il_tuo_token_qui"  # <-- Sostituisci con il tuo token HuggingFace

PROMPT_PERITO = (
    "Agisci come un perito assicurativo esperto. Analizza l'immagine e descrivi l'incidente "
    "identificando: 1. Punto d'impatto principale. 2. Componenti danneggiati (es. paraurti, "
    "gruppi ottici, cristalli). 3. Entità del danno (graffio, ammaccatura, deformazione strutturale). "
    "Usa un linguaggio tecnico."
)


def analizza_immagine_ai(sinistro_id: str, image_url: str):
    """
    Eseguita in background da un thread separato.
    Passa l'URL Cloudinary direttamente a Joy-Caption
    e salva il risultato su MongoDB.
    """
    try:
        print(f"[AI] Avvio analisi per sinistro {sinistro_id}...")

        # Joy-Caption accetta URL direttamente tramite handle_file
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

        sinistri_col.update_one(
            {"_id": ObjectId(sinistro_id)},
            {
                "$set": {
                    "analisi_ai": {
                        "testo": risultato_ai,
                        "modello": "joy-caption-beta-one",
                        "data_analisi": datetime.now(UTC),
                        "stato": "completata"
                    }
                }
            }
        )
        print(f"[AI] Risultato salvato su MongoDB per sinistro {sinistro_id}")

    except Exception as e:
        print(f"[AI] Errore analisi sinistro {sinistro_id}: {e}")
        try:
            sinistri_col.update_one(
                {"_id": ObjectId(sinistro_id)},
                {
                    "$set": {
                        "analisi_ai": {
                            "stato": "errore",
                            "errore": str(e),
                            "data_analisi": datetime.now(UTC)
                        }
                    }
                }
            )
        except Exception:
            pass


# --- ROTTE SINISTRI (MongoDB) ---

# CREATE: Apertura nuovo sinistro
@app.route('/sinistro', methods=['POST'])
def apri_sinistro():
    data = request.json
    required = ['automobilista_id', 'targa', 'data_evento', 'descrizione']

    if not all(k in data for k in required):
        return jsonify({"error": "Campi obbligatori mancanti"}), 400

    try:
        nuovo_sinistro = {
            "automobilista_id": data['automobilista_id'],
            "targa": data['targa'],
            "data_evento": data['data_evento'],
            "descrizione": data['descrizione'],
            "stato": "APERTO",
            "data_inserimento": datetime.now(UTC),
            "immagini": [],      # Lista di { url, public_id } Cloudinary
            "analisi_ai": None
        }
        result = sinistri_col.insert_one(nuovo_sinistro)
        return jsonify({"status": "success", "mongo_id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# READ: Visualizza tutti i sinistri
@app.route('/sinistri', methods=['GET'])
def get_tutti_sinistri():
    try:
        sinistri = list(sinistri_col.find())
        for s in sinistri:
            s['_id'] = str(s['_id'])
        return jsonify(sinistri), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# UPDATE: Upload immagine su Cloudinary + analisi AI asincrona
@app.route('/sinistro/ultimo/immagini', methods=['POST'])
def aggiungi_immagine_ultimo():
    """
    1. Riceve l'immagine in base64
    2. La carica su Cloudinary tramite Storage.py
    3. Salva l'URL nel documento MongoDB del sinistro
    4. Lancia in background l'analisi Joy-Caption
    5. Risponde subito con 202 Accepted
    """
    data = request.json
    if not data or 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        ultimo = sinistri_col.find_one(sort=[("data_inserimento", -1)])
        if not ultimo:
            return jsonify({"error": "Nessun sinistro trovato"}), 404

        sinistro_id = str(ultimo["_id"])

        # 1. Carica su Cloudinary tramite Storage.py
        print(f"☁️  Caricamento immagine su Cloudinary per sinistro {sinistro_id}...")
        info_cloudinary = carica_immagine(data['immagine_base64'], sinistro_id)
        print(f"Immagine caricata: {info_cloudinary['secure_url']}")

        # 2. Salva URL Cloudinary su MongoDB + segna analisi in elaborazione
        sinistri_col.update_one(
            {"_id": ultimo["_id"]},
            {
                "$push": {
                    "immagini": {
                        "url":       info_cloudinary["secure_url"],
                        "public_id": info_cloudinary["public_id"]
                    }
                },
                "$set": {
                    "analisi_ai": {
                        "stato": "in_elaborazione",
                        "data_avvio": datetime.now(UTC)
                    }
                }
            }
        )

        # 3. Lancia analisi AI in background passando l'URL Cloudinary
        thread = threading.Thread(
            target=analizza_immagine_ai,
            args=(sinistro_id, info_cloudinary["secure_url"]),
            daemon=True
        )
        thread.start()

        # 4. Risponde subito senza aspettare l'AI
        return jsonify({
            "status": "accepted",
            "id_sinistro": sinistro_id,
            "immagine_url": info_cloudinary["secure_url"],
            "messaggio": "Immagine salvata su Cloudinary. Analisi AI avviata in background.",
            "analisi_ai_stato": "in_elaborazione"
        }), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# READ: Polling stato analisi AI
@app.route('/sinistro/<sinistro_id>/analisi', methods=['GET'])
def get_analisi_ai(sinistro_id):
    """
    Il frontend chiama questo endpoint periodicamente per sapere
    se l'analisi AI è completata, in elaborazione o in errore.
    """
    if not ObjectId.is_valid(sinistro_id):
        return jsonify({"error": "ID non valido"}), 400

    try:
        sinistro = sinistri_col.find_one(
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


# --- ROTTE SOCCORSO E VEICOLI ---

@app.route('/soccorso', methods=['POST'])
def crea_richiesta_soccorso():
    data = request.json
    targa = data.get('targa')
    if not targa:
        return jsonify({"error": "Targa obbligatoria"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM Veicolo WHERE targa = %s", (targa,))
        veicolo = cursor.fetchone()

        if not veicolo:
            return jsonify({"error": "Veicolo non trovato in MySQL"}), 404

        nuovo_soccorso = {
            "veicolo_id": veicolo['id'],
            "targa": targa,
            "posizione": {"lat": data.get('lat'), "lon": data.get('lon')},
            "stato": "Richiesto",
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


@app.route('/veicoli/<int:id>', methods=['GET'])
def get_veicoli(id=None):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if id:
            cursor.execute("SELECT * FROM Veicolo WHERE id = %s", (id,))
            res = cursor.fetchone()
        else:
            cursor.execute("SELECT * FROM Veicolo")
            res = cursor.fetchall()
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7000)