"""
endpoint_5F_Periti.py — Porta 8000
Gestione pratiche, perizie e assegnazioni periti.

STRUTTURA MONGODB (nuova):
  - Proto_Sinistro_SC   → sinistri
  - Proto_Intervento_SC → interventi
  - Proto_Documenti_SC  → documenti allegati a pratiche/perizie

Le collezioni Pratica e Perizia mantengono i loro nomi originali
in quanto sono entità distinte non presenti nella nuova struttura base.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import mysql.connector
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
#  CONFIGURAZIONE DATABASE
# ─────────────────────────────────────────────

MYSQL_CONFIG = {
    "host":     os.getenv("MYSQL_HOST"),
    "port":     int(os.getenv("MYSQL_PORT", 3306)),
    "user":     os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
}

MONGO_URI = os.getenv("MONGO_URI")

_MONGO_DISPONIBILE = False
col_pratiche   = None
col_perizie    = None
col_sinistri   = None
col_interventi = None
col_documenti  = None

try:
    mongo_client   = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db       = mongo_client["SafeClaim"]
    col_pratiche   = mongo_db["Pratica"]
    col_perizie    = mongo_db["Perizia"]
    col_sinistri   = mongo_db["Proto_Sinistro_SC"]
    col_interventi = mongo_db["Proto_Intervento_SC"]
    col_documenti  = mongo_db["Proto_Documenti_SC"]
    mongo_client.admin.command("ping")
    _MONGO_DISPONIBILE = True
    print("✅ Connessione a MongoDB Atlas (SafeClaim) riuscita!")
except Exception as e:
    print(f"❌ Errore connessione MongoDB: {e}")


def get_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)


def _sinistro_summary(sinistro: dict) -> dict:
    """Estrae i campi rilevanti di un sinistro per embed nelle pratiche."""
    analisi = sinistro.get("analisi_ai")
    return {
        "_id":                    str(sinistro["_id"]),
        "targa":                  sinistro.get("targa"),
        "modello_veicolo":        sinistro.get("modello_veicolo"),
        "descrizione_danno":      sinistro.get("descrizione_danno"),
        "data_sinistro":          sinistro["data_sinistro"].isoformat()
                                  if isinstance(sinistro.get("data_sinistro"), datetime)
                                  else sinistro.get("data_sinistro"),
        "cliente":                sinistro.get("cliente"),
        "compagnia_assicurativa": sinistro.get("compagnia_assicurativa"),
        "numero_sinistro":        sinistro.get("numero_sinistro"),
        "stato_sinistro":         sinistro.get("stato_sinistro"),
        "priorita":               sinistro.get("priorita"),
        "officina_id":            sinistro.get("officina_id"),
        "num_immagini":           len(sinistro.get("immagini", [])),
        "analisi_ai_stato":       analisi.get("stato") if analisi else "non_avviata",
    }


# ═════════════════════════════════════════════
#  ROTTE — PRATICHE
# ═════════════════════════════════════════════

@app.route("/sinistro/<sinistro_id>/perito/<perito_id>/pratica", methods=["GET"])
def get_pratica(sinistro_id, perito_id):
    try:
        pratica = col_pratiche.find_one({"sinistro_id": sinistro_id, "perito_id": perito_id})
        if not pratica:
            return jsonify({"error": "Pratica non trovata"}), 404
        pratica["_id"] = str(pratica["_id"])
        for key in ["sinistro_id", "perito_id", "perizia_id"]:
            if key in pratica and pratica[key] is not None:
                pratica[key] = str(pratica[key])
        for key in ["data_inserimento", "data_aggiornamento"]:
            if isinstance(pratica.get(key), datetime):
                pratica[key] = pratica[key].isoformat()
        return jsonify(pratica), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/pratiche_assicurazione", methods=["GET"])
def get_pratiche_assicurazione():
    try:
        pratiche_cursor = col_pratiche.find()
        risultati = []
        for pratica in pratiche_cursor:
            pratica["_id"] = str(pratica["_id"])
            for key in ["data_inserimento", "data_aggiornamento", "data_creazione"]:
                if isinstance(pratica.get(key), datetime):
                    pratica[key] = pratica[key].isoformat()
            for key in ["sinistro_id", "perito_id", "perizia_id"]:
                if key in pratica and pratica[key] is not None:
                    pratica[key] = str(pratica[key])

            # Embed sinistro dalla nuova collezione Proto_Sinistro_SC
            sin_id = pratica.get("sinistro_id")
            if sin_id:
                try:
                    sinistro = col_sinistri.find_one({"_id": ObjectId(sin_id)}) \
                               if ObjectId.is_valid(sin_id) else None
                    if sinistro:
                        pratica["sinistro"] = _sinistro_summary(sinistro)
                except Exception as inner_err:
                    print(f"[pratiche] Errore caricamento sinistro {sin_id}: {inner_err}")

            risultati.append(pratica)
        return jsonify({"totale": len(risultati), "pratiche": risultati}), 200
    except Exception as e:
        return jsonify({"error": f"Errore nel recupero pratiche: {str(e)}"}), 500


@app.route("/perito/<perito_id>/pratiche", methods=["GET"])
def get_pratiche_perito(perito_id):
    """
    Restituisce le pratiche assegnate a un perito con il sinistro embedded.
    Aggiunge anche gli interventi aperti per il sinistro.
    """
    try:
        pratiche = list(col_pratiche.find({"perito_id": perito_id}))
        result = []
        for p in pratiche:
            p["_id"] = str(p["_id"])
            for key in ["sinistro_id", "perizia_id"]:
                if key in p and p[key] is not None:
                    p[key] = str(p[key])
            for key in ["data_inserimento", "data_aggiornamento", "data_creazione"]:
                if isinstance(p.get(key), datetime):
                    p[key] = p[key].isoformat()

            sin_id = p.get("sinistro_id")
            if sin_id:
                # Embed sinistro da Proto_Sinistro_SC
                try:
                    sinistro = col_sinistri.find_one({"_id": ObjectId(sin_id)}) \
                               if ObjectId.is_valid(sin_id) else None
                    if sinistro:
                        p["sinistro"] = _sinistro_summary(sinistro)
                except Exception as inner_err:
                    print(f"[pratiche] Errore caricamento sinistro {sin_id}: {inner_err}")

                # Embed interventi da Proto_Intervento_SC
                try:
                    interventi = list(col_interventi.find({"sinistro_id": sin_id}))
                    for i in interventi:
                        i["_id"] = str(i["_id"])
                        for campo in ("data_inizio", "data_fine"):
                            if isinstance(i.get(campo), datetime):
                                i[campo] = i[campo].isoformat()
                    p["interventi"] = interventi
                except Exception as inner_err:
                    print(f"[pratiche] Errore caricamento interventi {sin_id}: {inner_err}")

            result.append(p)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sinistro/<id_sinistro>/pratica", methods=["POST"])
def crea_pratica(id_sinistro):
    """
    Crea una pratica per un sinistro.
    perito_id opzionale: se assente la pratica è 'da_assegnare'.
    """
    data      = request.get_json() or {}
    perito_id = data.get("perito_id")

    if perito_id:
        try:
            conn   = get_mysql()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Perito WHERE id = %s", (perito_id,))
            if not cursor.fetchone():
                cursor.close(); conn.close()
                return jsonify({"error": "Perito non trovato"}), 404
            cursor.close(); conn.close()
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

    # Aggiorna stato sinistro nella nuova collezione
    stato_sinistro = "in_perizia" if perito_id else "da_assegnare"
    sinistro_update = {
        "stato_sinistro":  stato_sinistro,
        "pratica_id":      pratica_id,
    }
    if perito_id:
        sinistro_update["perito_id"] = str(perito_id)

    try:
        if ObjectId.is_valid(id_sinistro):
            col_sinistri.update_one(
                {"_id": ObjectId(id_sinistro)},
                {"$set": sinistro_update}
            )
    except Exception as e:
        print(f"[crea_pratica] Errore aggiornamento sinistro: {e}")

    return jsonify({"status": "Pratica creata", "id_pratica": pratica_id, "stato": stato}), 201


@app.route("/pratica/<pratica_id>/assegna", methods=["PUT"])
def assegna_perito_pratica(pratica_id):
    """Assegna un perito a una pratica 'da_assegnare'."""
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
        if not cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({"error": "Perito non trovato"}), 404
        cursor.close(); conn.close()
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
        sin_id = pratica["sinistro_id"]
        try:
            if ObjectId.is_valid(sin_id):
                col_sinistri.update_one(
                    {"_id": ObjectId(sin_id)},
                    {"$set": {"perito_id": perito_id, "stato_sinistro": "in_perizia"}}
                )
        except Exception as e:
            print(f"[assegna_perito] Errore aggiornamento sinistro: {e}")

    return jsonify({"status": "Perito assegnato", "pratica_id": pratica_id, "perito_id": perito_id}), 200


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


@app.route("/pratica/<pratica_id>/perito/<perito_id>", methods=["DELETE"])
def elimina_pratica(pratica_id, perito_id):
    if not ObjectId.is_valid(pratica_id):
        return jsonify({"error": "ID pratica non valido"}), 400
    try:
        result = col_pratiche.delete_one({
            "_id": ObjectId(pratica_id),
            "perito_id": perito_id
        })
        if result.deleted_count == 0:
            return jsonify({"error": "Pratica non trovata o non appartiene a questo perito"}), 404
        return jsonify({"status": "eliminata", "pratica_id": pratica_id, "perito_id": perito_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═════════════════════════════════════════════
#  ROTTE — RIMBORSO & INTERVENTO (perito)
# ═════════════════════════════════════════════

@app.route("/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/rimborso", methods=["POST"])
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

    # Aggiorna stato sinistro (Proto_Sinistro_SC)
    try:
        if ObjectId.is_valid(id_sinistro):
            col_sinistri.update_one(
                {"_id": ObjectId(id_sinistro)},
                {"$set": {"stato_sinistro": "rimborso_proposto"}}
            )
    except Exception as e:
        print(f"[rimborso] Errore aggiornamento sinistro: {e}")

    return jsonify({"status": "Rimborso salvato"}), 200


@app.route("/sinistro/<id_sinistro>/perito/<id_perito>/pratica/<id_perizia>/intervento", methods=["POST"])
def assegna_intervento(id_sinistro, id_perito, id_perizia):
    """
    Il perito assegna il sinistro a un'officina e crea un intervento
    nella collezione Proto_Intervento_SC.
    """
    data        = request.get_json() or {}
    id_officina = data.get("id_officina")
    if not id_officina:
        return jsonify({"error": "ID officina mancante"}), 400

    # Verifica officina su MySQL
    try:
        conn   = get_mysql()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM Officina WHERE id = %s", (id_officina,))
        officina = cursor.fetchone()
        cursor.close(); conn.close()
        if not officina:
            return jsonify({"error": "Officina non trovata"}), 404
    except Exception:
        pass

    try:
        s_id = ObjectId(id_sinistro)
        p_id = ObjectId(id_perizia)
    except Exception:
        return jsonify({"error": "Formato ID non valido"}), 400

    # Recupera targa dal sinistro
    sinistro = col_sinistri.find_one({"_id": s_id}, {"targa": 1})
    targa    = sinistro.get("targa") if sinistro else None

    # Aggiorna sinistro
    col_sinistri.update_one(
        {"_id": s_id},
        {"$set": {
            "officina_id":    id_officina,
            "stato_sinistro": "in_riparazione",
        }}
    )

    # Aggiorna perizia
    col_perizie.update_one(
        {"_id": p_id},
        {"$set": {"stato": "inviata_officina", "id_officina": id_officina}}
    )

    # Crea intervento in Proto_Intervento_SC
    data_inizio = None
    if data.get("data_inizio_lavori"):
        try:
            data_inizio = datetime.fromisoformat(data["data_inizio_lavori"])
        except Exception:
            pass

    nuovo_intervento = {
        "sinistro_id":        id_sinistro,
        "officina_id":        id_officina,
        "veicolo_targa":      targa,
        "data_inizio":        data_inizio or datetime.utcnow(),
        "data_fine":          None,
        "tipo_intervento":    data.get("tipo_intervento"),
        "descrizione_lavori": data.get("descrizione_lavori"),
        "ricambi_utilizzati": [],
        "manodopera_ore":     0,
        "foto_prima":         [],
        "foto_dopo":          [],
        "note_tecnico":       None,
        "stato":              "in_attesa"
    }
    intervento_result = col_interventi.insert_one(nuovo_intervento)

    return jsonify({
        "status":        "Successo",
        "nuovo_stato":   "in_riparazione",
        "intervento_id": str(intervento_result.inserted_id)
    }), 200


# ═════════════════════════════════════════════
#  ROTTE — PERIZIE
# ═════════════════════════════════════════════

@app.route("/perito/<perito_id>/perizie", methods=["GET"])
def get_perizie_perito(perito_id):
    try:
        docs = list(col_perizie.find({"perito_id": perito_id}))
        for d in docs:
            d["_id"] = str(d["_id"])
            if isinstance(d.get("sinistro_id"), ObjectId):
                d["sinistro_id"] = str(d["sinistro_id"])
            for key in ["data_inserimento", "data_aggiornamento"]:
                if isinstance(d.get(key), datetime):
                    d[key] = d[key].isoformat()
        return jsonify(docs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/perizia/<perizia_id>", methods=["DELETE"])
def elimina_perizia(perizia_id):
    try:
        result = col_perizie.delete_one({"_id": ObjectId(perizia_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Perizia non trovata"}), 404
        return jsonify({"status": "eliminata"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═════════════════════════════════════════════
#  ROTTE — PERITI (MySQL)
# ═════════════════════════════════════════════

@app.route("/periti", methods=["GET"])
def get_periti():
    try:
        conn   = get_mysql()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Perito ORDER BY id ASC")
        periti = cursor.fetchall()
        cursor.close(); conn.close()
        return jsonify({"totale": len(periti), "periti": periti}), 200
    except Exception as e:
        print(f"❌ Errore /periti: {e}")
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
#  AVVIO
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)