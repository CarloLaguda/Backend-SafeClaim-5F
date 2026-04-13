from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import mysql.connector
from bson import ObjectId
from datetime import datetime
import urllib.parse

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

# MongoDB Atlas (FakeClaim) — funzionante
_pw = urllib.parse.quote_plus("xxx123##")
MONGO_URI = f"mongodb+srv://dbFakeClaim:{_pw}@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db     = mongo_client["FakeClaim"]

    col_pratiche = mongo_db["Pratica"]
    col_perizie  = mongo_db["Perizia"]
    col_sinistri = mongo_db["Sinistro"]

    mongo_client.admin.command('ping')
    print("✅ Connessione a MongoDB Atlas (FakeClaim) riuscita!")
except Exception as e:
    print(f"❌ Errore connessione MongoDB: {e}")


# ── GET pratica ────────────────────────────────────────────────────────────────

@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["GET"])
def get_pratica(sinistro_id, perito_id):
    try:
        query   = {"sinistro_id": sinistro_id, "perito_id": perito_id}
        pratica = col_perizie.find_one(query)
        if not pratica:
            return jsonify({"error": "Pratica non trovata"}), 404
        pratica["_id"]         = str(pratica["_id"])
        pratica["sinistro_id"] = str(pratica["sinistro_id"])
        return jsonify(pratica), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ── PUT pratica (upsert) ───────────────────────────────────────────────────────

@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["PUT"])
def update_pratica(sinistro_id, perito_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dati mancanti"}), 400

    query = {"sinistro_id": sinistro_id, "perito_id": perito_id}
    update_data = {
        "$set": {
            "titolo":             data.get("titolo"),
            "tipo_danno":         data.get("tipo_danno"),
            "stima_danno":        data.get("stima_danno"),
            "parti_danneggiate":  data.get("parti_danneggiate", []),
            "descrizione":        data.get("descrizione"),
            "conclusione":        data.get("conclusione"),
            "veicolo":            data.get("veicolo"),
            "claim_code":         data.get("claim_code"),
            "stato":              data.get("stato", "Bozza"),
            "note_perito":        data.get("note_perito"),
            "sinistro_id":        sinistro_id,
            "perito_id":          perito_id,
            "data_aggiornamento": datetime.utcnow()
        }
    }
    col_perizie.update_one(query, update_data, upsert=True)
    return jsonify({"status": "success"}), 200


# ── POST pratica (crea perizia strutturata) ────────────────────────────────────

@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica', methods=['POST'])
def crea_pratica_completa(id_sinistro, id_perito):
    data = request.get_json()

    # Verifica esistenza Perito su MySQL
    try:
        conn   = get_mysql()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Perito WHERE id = %s", (id_perito,))
        perito_esiste = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        # Se MySQL non è raggiungibile, procediamo comunque con MongoDB
        perito_esiste = True

    if not perito_esiste:
        return jsonify({"error": "Perito non trovato"}), 404

    perizia_doc = {
        "sinistro_id":       id_sinistro,
        "perito_id":         id_perito,
        "titolo":            data.get("titolo"),
        "tipo_danno":        data.get("tipo_danno"),
        "stima_danno":       data.get("stima_danno"),
        "parti_danneggiate": data.get("parti_danneggiate", []),
        "descrizione":       data.get("descrizione"),
        "conclusione":       data.get("conclusione"),
        "veicolo":           data.get("veicolo"),
        "claim_code":        data.get("claim_code"),
        "stato":             data.get("stato", "Bozza"),
        "note_tecniche":     data.get("note_tecniche"),
        "documenti":         data.get("documenti", []),
        "data_inserimento":  datetime.utcnow()
    }

    result     = col_perizie.insert_one(perizia_doc)
    perizia_id = result.inserted_id

    # Aggiorna stato sinistro (non bloccante)
    try:
        col_sinistri.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {
                "stato":              "in_perizia",
                "perito_id":          id_perito,
                "perizia_id":         str(perizia_id),
                "data_aggiornamento": datetime.utcnow()
            }}
        )
    except Exception:
        pass

    return jsonify({
        "status":     "Pratica creata",
        "id_perizia": str(perizia_id)
    }), 201


# ── POST rimborso ──────────────────────────────────────────────────────────────

@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/rimborso', methods=['POST'])
def registra_rimborso(id_sinistro, id_perito, id_perizia):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON mancante"}), 400

    try:
        p_id = ObjectId(id_perizia)
    except Exception:
        return jsonify({"error": "Formato ID perizia non valido"}), 400

    res = col_perizie.update_one(
        {"_id": p_id},
        {"$set": {
            "stima_danno":        data.get("stima_danno"),
            "esito":              data.get("esito"),
            "stato":              "rimborso_inserito",
            "data_aggiornamento": datetime.utcnow()
        }}
    )

    if res.matched_count == 0:
        return jsonify({"error": "Perizia non trovata"}), 404

    try:
        col_sinistri.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {
                "stato":              "rimborso_proposto",
                "data_aggiornamento": datetime.utcnow()
            }}
        )
    except Exception:
        pass

    return jsonify({"status": "Rimborso salvato"}), 200


# ── POST intervento ────────────────────────────────────────────────────────────

@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/intervento', methods=['POST'])
def assegna_intervento(id_sinistro, id_perito, id_perizia):
    data        = request.get_json()
    id_officina = data.get("id_officina")

    if not id_officina:
        return jsonify({"error": "ID officina mancante"}), 400

    # Verifica esistenza Officina su MySQL (non bloccante)
    try:
        conn   = get_mysql()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Officina WHERE id = %s", (id_officina,))
        officina_esiste = cursor.fetchone()
        cursor.close()
        conn.close()
        if not officina_esiste:
            return jsonify({"error": "Officina non trovata"}), 404
    except Exception as e:
        pass  # Se MySQL non raggiungibile, procediamo

    try:
        s_id = ObjectId(id_sinistro)
        p_id = ObjectId(id_perizia)
    except Exception:
        return jsonify({"error": "Formato ID non valido"}), 400

    col_sinistri.update_one(
        {"_id": s_id},
        {"$set": {
            "id_officina":        id_officina,
            "stato":              "in_riparazione",
            "data_inizio_lavori": data.get("data_inizio_lavori"),
            "data_aggiornamento": datetime.utcnow()
        }}
    )

    col_perizie.update_one(
        {"_id": p_id},
        {"$set": {
            "stato":       "inviata_officina",
            "id_officina": id_officina
        }}
    )

    return jsonify({
        "status":      "Successo",
        "nuovo_stato": "in_riparazione"
    }), 200


# ── GET tutte le perizie di un perito ─────────────────────────────────────────

@app.route('/perito/<perito_id>/perizie', methods=['GET'])
def get_perizie_perito(perito_id):
    try:
        docs = list(col_perizie.find({"perito_id": perito_id}))
        for d in docs:
            d['_id'] = str(d['_id'])
            if 'sinistro_id' in d and isinstance(d['sinistro_id'], ObjectId):
                d['sinistro_id'] = str(d['sinistro_id'])
            if 'data_inserimento' in d and isinstance(d['data_inserimento'], datetime):
                d['data_inserimento'] = d['data_inserimento'].isoformat()
            if 'data_aggiornamento' in d and isinstance(d['data_aggiornamento'], datetime):
                d['data_aggiornamento'] = d['data_aggiornamento'].isoformat()
        return jsonify(docs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── DELETE perizia per ID ──────────────────────────────────────────────────────

@app.route('/perizia/<perizia_id>', methods=['DELETE'])
def elimina_perizia(perizia_id):
    try:
        result = col_perizie.delete_one({"_id": ObjectId(perizia_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Perizia non trovata"}), 404
        return jsonify({"status": "eliminata"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Avvio ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)