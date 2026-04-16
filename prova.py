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
    "host": "mysql-safeclaim.aevorastudios.com",
    "port": 3306,
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db"
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
    col_sinistri = mongo_db["Sinistro"]
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7000)