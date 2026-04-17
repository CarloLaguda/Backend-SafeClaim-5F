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


# --- PERIZIE ---

@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["GET"])
def get_pratica(sinistro_id, perito_id):
    try:
        pratica = col_perizie.find_one({"sinistro_id": sinistro_id, "perito_id": perito_id})
        if not pratica:
            return jsonify({"error": "Pratica non trovata"}), 404
        pratica["_id"] = str(pratica["_id"])
        return jsonify(pratica), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["PUT"])
def update_pratica(sinistro_id, perito_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dati mancanti"}), 400
    query = {"sinistro_id": sinistro_id, "perito_id": perito_id}
    update_data = {"$set": {
        "titolo": data.get("titolo"), "tipo_danno": data.get("tipo_danno"),
        "stima_danno": data.get("stima_danno"), "parti_danneggiate": data.get("parti_danneggiate", []),
        "descrizione": data.get("descrizione"), "conclusione": data.get("conclusione"),
        "veicolo": data.get("veicolo"), "claim_code": data.get("claim_code"),
        "stato": data.get("stato", "Bozza"), "note_perito": data.get("note_perito"),
        "sinistro_id": sinistro_id, "perito_id": perito_id,
        "data_aggiornamento": datetime.utcnow()
    }}
    col_perizie.update_one(query, update_data, upsert=True)
    return jsonify({"status": "success"}), 200


@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica', methods=['POST'])
def crea_pratica_completa(id_sinistro, id_perito):
    data = request.get_json()
    try:
        conn = get_mysql()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Perito WHERE id = %s", (id_perito,))
        perito_esiste = cursor.fetchone()
        cursor.close(); conn.close()
    except Exception:
        perito_esiste = True
    if not perito_esiste:
        return jsonify({"error": "Perito non trovato"}), 404
    perizia_doc = {
        "sinistro_id": id_sinistro, "perito_id": id_perito,
        "titolo": data.get("titolo"), "tipo_danno": data.get("tipo_danno"),
        "stima_danno": data.get("stima_danno"), "parti_danneggiate": data.get("parti_danneggiate", []),
        "descrizione": data.get("descrizione"), "conclusione": data.get("conclusione"),
        "veicolo": data.get("veicolo"), "claim_code": data.get("claim_code"),
        "stato": data.get("stato", "Bozza"), "note_tecniche": data.get("note_tecniche"),
        "documenti": data.get("documenti", []), "data_inserimento": datetime.now(UTC)
    }
    result = col_perizie.insert_one(perizia_doc)
    perizia_id = result.inserted_id
    try:
        col_sinistri.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {"stato": "in_perizia", "perito_id": id_perito,
                      "perizia_id": str(perizia_id), "data_aggiornamento": datetime.now(UTC)}}
        )
    except Exception:
        pass
    return jsonify({"status": "Pratica creata", "id_perizia": str(perizia_id)}), 201


@app.route('/perito/<perito_id>/perizie', methods=['GET'])
def get_perizie_perito(perito_id):
    try:
        docs = list(col_perizie.find({"perito_id": perito_id}))
        for d in docs:
            d['_id'] = str(d['_id'])
            if isinstance(d.get('sinistro_id'), ObjectId):
                d['sinistro_id'] = str(d['sinistro_id'])
            if isinstance(d.get('data_inserimento'), datetime):
                d['data_inserimento'] = d['data_inserimento'].isoformat()
            if isinstance(d.get('data_aggiornamento'), datetime):
                d['data_aggiornamento'] = d['data_aggiornamento'].isoformat()
        return jsonify(docs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/perizia/<perizia_id>', methods=['DELETE'])
def elimina_perizia(perizia_id):
    try:
        result = col_perizie.delete_one({"_id": ObjectId(perizia_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Perizia non trovata"}), 404
        return jsonify({"status": "eliminata"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7000)
