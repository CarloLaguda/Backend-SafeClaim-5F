"""
endpoint_5F_Assicurazione.py — Porta 5000
Gestione sinistri lato assicuratore, registrazione completa, veicoli.

STRUTTURA MONGODB (nuova):
  - Proto_Sinistro_SC  → sinistri (sostituisce 'Sinistri')
"""

from flask import Flask, request, jsonify
import mysql.connector
import re
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from flask_cors import CORS
from dotenv import load_dotenv
import os

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
sinistri_col = None
col_pratiche = None

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db     = mongo_client["SafeClaim"]
    sinistri_col = mongo_db["Proto_Sinistro_SC"]   # ← nuova collezione
    col_pratiche = mongo_db["Pratica"]
    mongo_client.admin.command("ping")
    _MONGO_DISPONIBILE = True
    print("✅ Connessione a MongoDB Atlas (SafeClaim) riuscita!")
except Exception as e:
    print(f"❌ Errore critico connessione MongoDB: {e}")


def get_mysql_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)


def _serializza_sinistro(s: dict) -> dict:
    s["_id"] = str(s["_id"])
    for campo in ("data_sinistro", "data_assegnazione"):
        if isinstance(s.get(campo), datetime):
            s[campo] = s[campo].isoformat()
    preventivo = s.get("preventivo")
    if isinstance(preventivo, dict) and isinstance(preventivo.get("data"), datetime):
        preventivo["data"] = preventivo["data"].isoformat()
    analisi = s.get("analisi_ai")
    if analisi and isinstance(analisi.get("data_analisi"), datetime):
        analisi["data_analisi"] = analisi["data_analisi"].isoformat()
    return s


# ═════════════════════════════════════════════
#  ROTTE — SINISTRI (Proto_Sinistro_SC)
# ═════════════════════════════════════════════

@app.route("/sinistri", defaults={"id_sinistro": None}, methods=["GET"])
@app.route("/sinistri/<id_sinistro>", methods=["GET"])
def ottieni_sinistri(id_sinistro):
    """
    GET /sinistri          → lista completa
    GET /sinistri/<id>     → singolo per ObjectId
    Query param: officina_id, stato_sinistro, attivo
    """
    if not _MONGO_DISPONIBILE:
        return jsonify({"error": "MongoDB non disponibile"}), 503
    try:
        if id_sinistro:
            if not ObjectId.is_valid(id_sinistro):
                return jsonify({"error": "Formato ID non valido"}), 400
            s = sinistri_col.find_one({"_id": ObjectId(id_sinistro)})
            if not s:
                return jsonify({"error": "Sinistro non trovato"}), 404
            return jsonify(_serializza_sinistro(s)), 200
        else:
            filtro = {}
            if request.args.get("officina_id"):
                filtro["officina_id"] = int(request.args["officina_id"])
            if request.args.get("stato_sinistro"):
                filtro["stato_sinistro"] = request.args["stato_sinistro"]
            if request.args.get("attivo") is not None:
                filtro["attivo"] = request.args["attivo"].lower() in ("1", "true", "yes")

            lista = []
            for s in sinistri_col.find(filtro):
                lista.append(_serializza_sinistro(s))
            return jsonify({"count": len(lista), "data": lista}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sinistro/<id_sinistro>/perito", methods=["PUT"])
def assegna_perito(id_sinistro):
    """Assegna un perito a un sinistro aggiornando stato_sinistro."""
    if not _MONGO_DISPONIBILE:
        return jsonify({"error": "MongoDB non disponibile"}), 503
    try:
        data      = request.get_json()
        id_perito = data.get("id_perito")
        if id_perito is None:
            return jsonify({"error": "id_perito mancante"}), 400
        if not ObjectId.is_valid(id_sinistro):
            return jsonify({"error": "ID sinistro non valido"}), 400

        result = sinistri_col.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {
                "perito_id":       id_perito,
                "stato_sinistro":  "assegnato_a_perito",
                "data_assegnazione": datetime.now()
            }}
        )
        if result.matched_count > 0:
            return jsonify({"status": "success", "message": "Perito assegnato"}), 200
        return jsonify({"error": "Sinistro non trovato"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/sinistro/<id>", methods=["PUT"])
def aggiorna_sinistro(id):
    """
    Aggiornamento generico sinistro.
    Campi ammessi: stato_sinistro, descrizione_danno, perizia_id,
                   officina_id, note, priorita, attivo.
    """
    if not _MONGO_DISPONIBILE:
        return jsonify({"error": "MongoDB non disponibile"}), 503
    data = request.json
    campi_ammessi = [
        "stato_sinistro", "descrizione_danno", "perizia_id",
        "officina_id", "note", "priorita", "attivo"
    ]
    update_query = {k: v for k, v in data.items() if k in campi_ammessi}
    if not update_query:
        return jsonify({"error": "Dati non validi"}), 400
    try:
        if not ObjectId.is_valid(id):
            return jsonify({"error": "ID malformato"}), 400
        result = sinistri_col.update_one({"_id": ObjectId(id)}, {"$set": update_query})
        if result.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404
        return jsonify({"messaggio": "Aggiornato", "campi": list(update_query.keys())}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
#  PRATICHE (con embed sinistro da nuova collezione)
# ─────────────────────────────────────────────

@app.route("/pratiche_assicurazione", methods=["GET"])
def get_pratiche_assicurazione():
    if not _MONGO_DISPONIBILE:
        return jsonify({"error": "MongoDB non disponibile"}), 503
    try:
        pratiche = list(col_pratiche.find())
        for p in pratiche:
            p["_id"] = str(p["_id"])
            for k in ["data_inserimento", "data_aggiornamento"]:
                if isinstance(p.get(k), datetime):
                    p[k] = p[k].isoformat()
            # Embed sinistro da Proto_Sinistro_SC
            sin_id = p.get("sinistro_id")
            if sin_id and ObjectId.is_valid(str(sin_id)):
                sinistro = sinistri_col.find_one({"_id": ObjectId(sin_id)})
                if sinistro:
                    sinistro["_id"] = str(sinistro["_id"])
                    p["sinistro"] = {
                        k: v for k, v in sinistro.items()
                        if k in ["targa", "modello_veicolo", "descrizione_danno",
                                 "data_sinistro", "stato_sinistro", "cliente",
                                 "compagnia_assicurativa", "numero_sinistro"]
                    }
                    p["sinistro"]["immagini"]   = sinistro.get("immagini", [])
                    p["sinistro"]["analisi_ai"] = sinistro.get("analisi_ai", {})
                    if isinstance(p["sinistro"].get("data_sinistro"), datetime):
                        p["sinistro"]["data_sinistro"] = p["sinistro"]["data_sinistro"].isoformat()
        return jsonify({"totale": len(pratiche), "pratiche": pratiche}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═════════════════════════════════════════════
#  ROTTE — VEICOLI (MySQL)
# ═════════════════════════════════════════════

@app.route("/veicoli-utente/<int:user_id>", methods=["GET"])
def get_veicoli_utente(user_id):
    conn = None
    try:
        conn   = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT v.* FROM Veicolo v
            JOIN Automobilista a ON v.automobilista_id = a.id
            WHERE a.id_utente = %s
        """, (user_id,))
        veicoli = cursor.fetchall()
        return jsonify(veicoli), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/veicolo/user/<int:user_id>", methods=["POST"])
def crea_veicolo_utente(user_id):
    data = request.get_json()
    if not data or not data.get("targa"):
        return jsonify({"error": "Campo obbligatorio mancante: targa"}), 400
    conn = None
    try:
        conn   = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM Automobilista WHERE id_utente = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Utente {user_id} non trovato"}), 404
        cursor.execute(
            "INSERT INTO Veicolo (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (data.get("targa"), data.get("n_telaio"), data.get("marca"),
             data.get("modello"), data.get("anno_immatricolazione"), user_id)
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
        if conn:
            conn.close()


# ═════════════════════════════════════════════
#  REGISTRAZIONE COMPLETA (MySQL)
# ═════════════════════════════════════════════

TIPI_COPERTURA = {"RCA", "Kasko", "Furto_Incendio", "Full"}

@app.route("/registrazione-completa", methods=["POST"])
def registrazione_completa():
    """
    Registrazione completa in un'unica transazione:
      Step 1 – dati utente
      Step 2 – dati veicolo
      Step 3 – dati polizza
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    dati_utente  = data.get("utente",  {})
    dati_veicolo = data.get("veicolo", {})
    dati_polizza = data.get("polizza", {})

    for campo in ["nome", "cognome", "email", "password_hash", "cf"]:
        if not dati_utente.get(campo):
            return jsonify({"error": f"Campo utente mancante: {campo}"}), 400
    if not dati_veicolo.get("targa"):
        return jsonify({"error": "Campo veicolo mancante: targa"}), 400
    for campo in ["n_polizza", "data_inizio", "data_scadenza"]:
        if not dati_polizza.get(campo):
            return jsonify({"error": f"Campo polizza mancante: {campo}"}), 400

    tipo_copertura = dati_polizza.get("tipo_copertura", "RCA")
    if tipo_copertura not in TIPI_COPERTURA:
        return jsonify({"error": f"tipo_copertura non valido. Ammessi: {TIPI_COPERTURA}"}), 400

    conn = None
    try:
        conn   = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """INSERT INTO Utente (nome, cognome, email, telefono, password_hash, ruolo)
               VALUES (%s, %s, %s, %s, %s, 'automobilista')""",
            (dati_utente["nome"].strip().title(), dati_utente["cognome"].strip().title(),
             dati_utente["email"].strip().lower(), dati_utente.get("telefono"),
             dati_utente["password_hash"])
        )
        utente_id = cursor.lastrowid

        n_polizza = dati_polizza.get("n_polizza")
        cursor.execute(
            """INSERT INTO Automobilista (nome, cognome, cf, id_utente)
               VALUES (%s, %s, %s, %s)""",
            (dati_utente["nome"].strip().title(), dati_utente["cognome"].strip().title(),
             dati_utente["cf"].strip().upper(), utente_id)
        )
        automobilista_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO Veicolo (targa, n_telaio, marca, modello,
                                    anno_immatricolazione, automobilista_id)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (dati_veicolo.get("targa"), dati_veicolo.get("n_telaio"),
             dati_veicolo.get("marca"), dati_veicolo.get("modello"),
             dati_veicolo.get("anno_immatricolazione"), automobilista_id)
        )
        veicolo_id = cursor.lastrowid

        assicuratore_id = None
        ass_utente_id   = dati_polizza.get("assicuratore_utente_id")
        if ass_utente_id:
            cursor.execute("SELECT id FROM Assicuratore WHERE id_utente = %s", (ass_utente_id,))
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                return jsonify({"error": f"Assicuratore con id_utente={ass_utente_id} non trovato"}), 404
            assicuratore_id = row["id"]

        cursor.execute(
            """INSERT INTO Polizza (n_polizza, compagnia_assicurativa, data_inizio,
                                    data_scadenza, massimale, tipo_copertura,
                                    veicolo_id, assicuratore_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (n_polizza, dati_polizza.get("compagnia_assicurativa"),
             dati_polizza["data_inizio"], dati_polizza["data_scadenza"],
             dati_polizza.get("massimale"), tipo_copertura,
             veicolo_id, assicuratore_id)
        )
        polizza_id = cursor.lastrowid

        cursor.execute("UPDATE Automobilista SET n_polizza = %s WHERE id = %s", (n_polizza, automobilista_id))
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
        if conn: conn.rollback()
        msg = str(e).lower()
        if "email" in msg or "cf" in msg:
            return jsonify({"error": "Email o Codice Fiscale già registrati"}), 409
        if "targa" in msg or "n_telaio" in msg:
            return jsonify({"error": "Targa o numero telaio già esistente"}), 409
        if "n_polizza" in msg:
            return jsonify({"error": "Numero polizza già esistente"}), 409
        return jsonify({"error": f"Violazione integrità DB: {str(e)}"}), 409
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# ─────────────────────────────────────────────
#  AVVIO
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)