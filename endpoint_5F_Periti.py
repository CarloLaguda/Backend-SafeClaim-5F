from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import mysql.connector
from bson import ObjectId
from datetime import datetime
import urllib.parse
import os
from dotenv import load_dotenv

app = Flask(_name_)
CORS(app)

# --- CONFIGURAZIONE DATABASE ---

load_dotenv()

MYSQL_CONFIG = {
    "host":     os.getenv("MYSQL_HOST"),
    "port":     int(os.getenv("MYSQL_PORT", 3306)),
    "user":     os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
}

MONGO_URI = os.getenv("MONGO_URI")

# MongoDB Atlas (FakeClaim)
_pw = urllib.parse.quote_plus("xxx123##")
MONGO_URI = f"mongodb+srv://dbFakeClaim:{_pw}@cluster0.zgw1jft.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db     = mongo_client["FakeClaim"]
    col_pratiche = mongo_db["Pratica"]
    col_perizie  = mongo_db["Perizia"]
    col_sinistri = mongo_db["Sinistri"]
    mongo_client.admin.command('ping')
    print("✅ Connessione a MongoDB Atlas (FakeClaim) riuscita!")
except Exception as e:
    print(f"❌ Errore connessione MongoDB: {e}")

def get_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)

# ── GET pratica ────────────────────────────────────────────────────────────────

@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["GET"])
def get_pratica(sinistro_id, perito_id):
    try:
        query = {"sinistro_id": sinistro_id, "perito_id": perito_id}
        pratica = col_pratiche.find_one(query)
        if not pratica:
            return jsonify({"error": "Pratica non trovata"}), 404
        pratica["_id"] = str(pratica["_id"])
        pratica["sinistro_id"] = str(pratica["sinistro_id"])
        return jsonify(pratica), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ── GET tutte le pratiche per l'Assicurazione ─────────────────────────────────

@app.route("/pratiche_assicurazione", methods=["GET"])
def get_pratiche_assicurazione():
    try:
        pratiche_cursor = col_pratiche.find()
        risultati = []
        for pratica in pratiche_cursor:
            pratica["_id"] = str(pratica["_id"])
            if "data_inserimento" in pratica and isinstance(pratica["data_inserimento"], datetime):
                pratica["data_inserimento"] = pratica["data_inserimento"].isoformat()
            if "data_aggiornamento" in pratica and isinstance(pratica["data_aggiornamento"], datetime):
                pratica["data_aggiornamento"] = pratica["data_aggiornamento"].isoformat()
            for key in ["sinistro_id", "perito_id", "perizia_id"]:
                if key in pratica and pratica[key] is not None:
                    pratica[key] = str(pratica[key])
            risultati.append(pratica)
        return jsonify({"totale": len(risultati), "pratiche": risultati}), 200
    except Exception as e:
        return jsonify({"error": f"Errore nel recupero pratiche assicurazione: {str(e)}"}), 500


# ── GET pratiche assegnate a un perito (con sinistro embedded) ────────────────

@app.route('/perito/<perito_id>/pratiche', methods=['GET'])
def get_pratiche_perito(perito_id):
    try:
        pratiche = list(col_pratiche.find({"perito_id": perito_id}))
        result = []
        for p in pratiche:
            p['_id'] = str(p['_id'])
            for key in ['sinistro_id', 'perizia_id']:
                if key in p and p[key] is not None:
                    p[key] = str(p[key])
            for key in ['data_inserimento', 'data_aggiornamento', 'data_creazione']:
                if key in p and isinstance(p[key], datetime):
                    p[key] = p[key].isoformat()

            sin_id = p.get('sinistro_id')
            if sin_id:
                try:
                    sinistro = col_sinistri.find_one({"_id": ObjectId(sin_id)})
                    if sinistro:
                        sinistro['_id'] = str(sinistro['_id'])
                        if isinstance(sinistro.get('data_evento'), datetime):
                            sinistro['data_evento'] = sinistro['data_evento'].isoformat()
                        if isinstance(sinistro.get('data_inserimento'), datetime):
                            sinistro['data_inserimento'] = sinistro['data_inserimento'].isoformat()
                        analisi = sinistro.get('analisi_ai')
                        p['sinistro'] = {
                            '_id':                    sinistro['_id'],
                            'targa':                  sinistro.get('targa'),
                            'marca':                  sinistro.get('marca'),
                            'modello':                sinistro.get('modello'),
                            'data_evento':            sinistro.get('data_evento'),
                            'descrizione':            sinistro.get('descrizione'),
                            'luogo':                  sinistro.get('luogo'),
                            'tipo_sinistro':          sinistro.get('tipo_sinistro'),
                            'stima_danno':            sinistro.get('stima_danno'),
                            'stato':                  sinistro.get('stato'),
                            'compagnia_assicurativa': sinistro.get('compagnia_assicurativa'),
                            'priorita':               sinistro.get('priorita'),
                            'num_immagini':           len(sinistro.get('immagini', [])),
                            'analisi_ai_stato':       analisi.get('stato') if analisi else 'non_avviata',
                        }
                except Exception as inner_err:
                    print(f"[pratiche] Errore caricamento sinistro {sin_id}: {inner_err}")
            result.append(p)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── POST crea pratica (con o senza perito) ────────────────────────────────────

@app.route('/sinistro/<id_sinistro>/pratica', methods=['POST'])
def crea_pratica(id_sinistro):
    data      = request.get_json() or {}
    perito_id = data.get("perito_id")

    if perito_id:
        try:
            conn   = get_mysql()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Perito WHERE id = %s", (perito_id,))
            perito_esiste = cursor.fetchone()
            cursor.close()
            conn.close()
            if not perito_esiste:
                return jsonify({"error": "Perito non trovato"}), 404
        except Exception:
            pass

    stato = "assegnata" if perito_id else "da_assegnare"

    pratica_doc = {
        "sinistro_id":       id_sinistro,
        "perito_id":         str(perito_id) if perito_id else None,
        "stato":             stato,
        "titolo":            data.get("titolo", "Pratica in attesa di assegnazione"),
        "descrizione":       data.get("descrizione", ""),
        "tipo_danno":        data.get("tipo_danno"),
        "stima_danno":       data.get("stima_danno"),
        "veicolo":           data.get("veicolo"),
        "parti_danneggiate": data.get("parti_danneggiate", []),
        "conclusione":       data.get("conclusione"),
        "note_tecniche":     data.get("note_tecniche"),
        "claim_code":        data.get("claim_code"),
        "documenti":         data.get("documenti", []),
        "data_inserimento":  datetime.utcnow()
    }

    result     = col_pratiche.insert_one(pratica_doc)
    pratica_id = str(result.inserted_id)

    stato_sinistro = "in_perizia" if perito_id else "da_assegnare"
    sinistro_update = {
        "stato":              stato_sinistro,
        "pratica_id":         pratica_id,
        "data_aggiornamento": datetime.utcnow()
    }
    if perito_id:
        sinistro_update["perito_id"] = str(perito_id)

    try:
        col_sinistri.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": sinistro_update}
        )
    except Exception:
        pass

    return jsonify({
        "status":     "Pratica creata",
        "id_pratica": pratica_id,
        "stato":      stato
    }), 201


# ── PUT assegna perito a pratica esistente (dall'assicurazione) ───────────────

@app.route('/pratica/<pratica_id>/assegna', methods=['PUT'])
def assegna_perito_pratica(pratica_id):
    data = request.get_json()
    if not data or not data.get("perito_id"):
        return jsonify({"error": "perito_id mancante"}), 400
    if not ObjectId.is_valid(pratica_id):
        return jsonify({"error": "ID pratica non valido"}), 400

    perito_id = str(data["perito_id"])

    try:
        conn   = get_mysql()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Perito WHERE id = %s", (perito_id,))
        perito_esiste = cursor.fetchone()
        cursor.close()
        conn.close()
        if not perito_esiste:
            return jsonify({"error": "Perito non trovato"}), 404
    except Exception:
        pass

    result = col_pratiche.update_one(
        {"_id": ObjectId(pratica_id)},
        {"$set": {
            "perito_id":          perito_id,
            "stato":              "assegnata",
            "data_aggiornamento": datetime.utcnow()
        }}
    )
    if result.matched_count == 0:
        return jsonify({"error": "Pratica non trovata"}), 404

    pratica = col_pratiche.find_one({"_id": ObjectId(pratica_id)})
    if pratica and pratica.get("sinistro_id"):
        try:
            col_sinistri.update_one(
                {"_id": ObjectId(pratica["sinistro_id"])},
                {"$set": {
                    "perito_id":          perito_id,
                    "stato":              "in_perizia",
                    "data_aggiornamento": datetime.utcnow()
                }}
            )
        except Exception:
            pass

    return jsonify({
        "status":     "Perito assegnato",
        "pratica_id": pratica_id,
        "perito_id":  perito_id
    }), 200


# ── PUT accetta / rifiuta pratica (dal perito) ────────────────────────────────
#
# Questo è l'endpoint che il frontend chiama quando il perito accetta o rifiuta.
# Separato dall'endpoint /sinistro/.../pratica per usare direttamente l'_id
# della pratica, evitando mismatch tra sinistro_id stringa e ObjectId.

@app.route('/pratica/<pratica_id>/perito/<perito_id>', methods=['PUT'])
def aggiorna_pratica_perito(pratica_id, perito_id):
    """
    Il perito accetta (stato → in_perizia) o rifiuta (stato → da_assegnare)
    una pratica assegnatagli.
    Body: { "stato": "in_perizia" | "da_assegnare", "_reset_perito": true/false }
    """
    if not ObjectId.is_valid(pratica_id):
        return jsonify({"error": "ID pratica non valido"}), 400

    data = request.get_json() or {}
    nuovo_stato   = data.get("stato", "in_perizia")
    reset_perito  = data.get("_reset_perito", False)

    update_fields = {
        "stato":              nuovo_stato,
        "data_aggiornamento": datetime.utcnow()
    }
    if reset_perito:
        update_fields["perito_id"] = None

    result = col_pratiche.update_one(
        {"_id": ObjectId(pratica_id), "perito_id": perito_id},
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        # Tentiamo senza il filtro perito_id per pratica senza perito embedded
        result = col_pratiche.update_one(
            {"_id": ObjectId(pratica_id)},
            {"$set": update_fields}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Pratica non trovata"}), 404

    # Aggiorna anche il sinistro collegato
    pratica = col_pratiche.find_one({"_id": ObjectId(pratica_id)})
    if pratica and pratica.get("sinistro_id"):
        sin_id = pratica["sinistro_id"]
        stato_sinistro = "in_perizia" if nuovo_stato == "in_perizia" else "aperto"
        sinistro_update = {
            "stato":              stato_sinistro,
            "data_aggiornamento": datetime.utcnow()
        }
        if reset_perito:
            sinistro_update["perito_id"] = None
        try:
            col_sinistri.update_one(
                {"_id": ObjectId(str(sin_id))},
                {"$set": sinistro_update}
            )
        except Exception as e:
            print(f"[aggiorna_pratica_perito] Errore aggiornamento sinistro: {e}")

    return jsonify({
        "status":     "ok",
        "pratica_id": pratica_id,
        "stato":      nuovo_stato
    }), 200


# ── DELETE pratica (dal perito, via pratica_id) ───────────────────────────────

@app.route('/pratica/<pratica_id>/perito/<perito_id>', methods=['DELETE'])
def elimina_pratica(pratica_id, perito_id):
    if not ObjectId.is_valid(pratica_id):
        return jsonify({"error": "ID pratica non valido"}), 400
    try:
        result = col_pratiche.delete_one({
            "_id": ObjectId(pratica_id),
            "perito_id": perito_id
        })
        if result.deleted_count == 0:
            # fallback senza filtro perito
            result = col_pratiche.delete_one({"_id": ObjectId(pratica_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Pratica non trovata"}), 404
        return jsonify({"status": "eliminata", "pratica_id": pratica_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── PUT pratica (upsert via sinistro_id + perito_id) ─────────────────────────

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
    col_pratiche.update_one(query, update_data, upsert=True)
    return jsonify({"status": "success"}), 200


# ── POST rimborso ─────────────────────────────────────────────────────────────

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
            {"$set": {"stato": "rimborso_proposto", "data_aggiornamento": datetime.utcnow()}}
        )
    except Exception:
        pass
    return jsonify({"status": "Rimborso salvato"}), 200


# ── POST intervento ───────────────────────────────────────────────────────────

@app.route('/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/intervento', methods=['POST'])
def assegna_intervento(id_sinistro, id_perito, id_perizia):
    data        = request.get_json()
    id_officina = data.get("id_officina")
    if not id_officina:
        return jsonify({"error": "ID officina mancante"}), 400

    try:
        conn   = get_mysql()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Officina WHERE id = %s", (id_officina,))
        officina_esiste = cursor.fetchone()
        cursor.close()
        conn.close()
        if not officina_esiste:
            return jsonify({"error": "Officina non trovata"}), 404
    except Exception:
        pass

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
        {"$set": {"stato": "inviata_officina", "id_officina": id_officina}}
    )
    return jsonify({"status": "Successo", "nuovo_stato": "in_riparazione"}), 200


# ── GET perizie perito ────────────────────────────────────────────────────────

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


# ── DELETE perizia ────────────────────────────────────────────────────────────

@app.route('/perizia/<perizia_id>', methods=['DELETE'])
def elimina_perizia(perizia_id):
    try:
        result = col_perizie.delete_one({"_id": ObjectId(perizia_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Perizia non trovata"}), 404
        return jsonify({"status": "eliminata"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── GET periti (da MySQL) ─────────────────────────────────────────────────────

@app.route('/periti', methods=['GET'])
def get_periti():
    try:
        conn   = get_mysql()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Perito ORDER BY id ASC")
        periti = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"totale": len(periti), "periti": periti}), 200
    except Exception as e:
        print(f"❌ Errore /periti: {e}")
        return jsonify({"error": str(e)}), 500


# ── Avvio ─────────────────────────────────────────────────────────────────────

if _name_ == "_main_":
    app.run(host="0.0.0.0", port=8000, debug=True)
