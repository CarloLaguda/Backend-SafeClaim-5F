"""
endpoint_5F_Sinistri_User.py — Branch main
Gestione sinistri, interventi e veicoli.
Le immagini vengono salvate su Cloudinary tramite Storage.py,
poi analizzate in modo asincrono da Gemini Vision (Google).

STRUTTURA MONGODB (nuova):
  - Proto_Sinistro_SC  → collezione sinistri
  - Proto_Intervento_SC → collezione interventi

ROBUSTEZZA: il server si avvia sempre, anche se Gemini, MongoDB
o MariaDB non sono raggiungibili. Ogni sottosistema ha il suo
try/except indipendente e un flag di disponibilità.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from datetime import datetime, UTC, timezone
import threading
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Importazione opzionale di Gemini
try:
    from google import genai
    from google.genai import types
    _GENAI_IMPORTATO = True
except Exception as _e:
    print(f"⚠️  Impossibile importare google-genai: {_e}")
    _GENAI_IMPORTATO = False

# Importazione opzionale di Storage (Cloudinary)
try:
    from Storage import carica_immagine
    _STORAGE_DISPONIBILE = True
except Exception as _e:
    print(f"⚠️  Impossibile importare Storage.py: {_e}")
    _STORAGE_DISPONIBILE = False

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
#  CONFIGURAZIONE MYSQL
# ─────────────────────────────────────────────

MYSQL_CONFIG = {
    "host":     os.getenv("MYSQL_HOST"),
    "port":     int(os.getenv("MYSQL_PORT", 3306)),
    "user":     os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
}

def get_mysql():
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Exception as e:
        print(f"❌ Errore connessione MySQL: {e}")
        raise

# ─────────────────────────────────────────────
#  CONFIGURAZIONE MONGODB ATLAS
#  Nuove collezioni: Proto_Sinistro_SC, Proto_Intervento_SC
# ─────────────────────────────────────────────

col_sinistri   = None
col_interventi = None
soccorso_col   = None
_MONGO_DISPONIBILE = False

try:
    MONGO_URI  = os.getenv("MONGO_URI")
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db     = mongo_client["SafeClaim"]
    col_sinistri   = mongo_db["Proto_Sinistro_SC"]
    col_interventi = mongo_db["Proto_Intervento_SC"]
    soccorso_col   = mongo_db["Soccorso"]
    mongo_client.admin.command("ping")
    _MONGO_DISPONIBILE = True
    print("✅ Connessione a MongoDB Atlas (SafeClaim) riuscita!")
except Exception as e:
    print(f"❌ Errore connessione MongoDB: {e} — le rotte MongoDB risponderanno con 503.")

# ─────────────────────────────────────────────
#  CONFIGURAZIONE GEMINI VISION
# ─────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL   = "gemini-2.5-flash"

gemini_client      = None
gemini_disponibile = False

if _GENAI_IMPORTATO:
    try:
        gemini_client      = genai.Client(api_key=GEMINI_API_KEY)
        gemini_disponibile = True
        print("✅ Gemini Vision inizializzato correttamente.")
    except Exception as e:
        print(f"⚠️  Gemini Vision non disponibile: {e} — l'analisi AI sarà disabilitata.")
else:
    print("⚠️  Gemini Vision non disponibile (libreria non importata).")

PROMPT_PERITO = (
    "Agisci come un perito assicurativo esperto. Analizza l'immagine e descrivi l'incidente "
    "identificando: 1. Punto d'impatto principale. 2. Componenti danneggiati (es. paraurti, "
    "gruppi ottici, cristalli). 3. Entità del danno (graffio, ammaccatura, deformazione strutturale). "
    "Usa un linguaggio tecnico."
)

# ─────────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────────

def _richiedi_mongo():
    if not _MONGO_DISPONIBILE:
        return jsonify({"error": "Database MongoDB non disponibile. Riprova più tardi."}), 503
    return None

def _serializza_sinistro(s: dict) -> dict:
    """Converte campi non-JSON-serializzabili di un documento sinistro."""
    s["_id"] = str(s["_id"])
    for campo in ("data_sinistro", "data_assegnazione"):
        if isinstance(s.get(campo), datetime):
            s[campo] = s[campo].isoformat()
    # Preventivo: data
    preventivo = s.get("preventivo")
    if isinstance(preventivo, dict) and isinstance(preventivo.get("data"), datetime):
        preventivo["data"] = preventivo["data"].isoformat()
    # Analisi AI (campo opzionale aggiunto da Gemini)
    analisi = s.get("analisi_ai")
    if analisi and isinstance(analisi.get("data_analisi"), datetime):
        analisi["data_analisi"] = analisi["data_analisi"].isoformat()
    if not analisi:
        s["analisi_ai"] = {"stato": "non_avviata"}
    if "immagini" not in s or s["immagini"] is None:
        s["immagini"] = []
    return s

def _serializza_intervento(i: dict) -> dict:
    """Converte campi non-JSON-serializzabili di un documento intervento."""
    i["_id"] = str(i["_id"])
    for campo in ("data_inizio", "data_fine"):
        if isinstance(i.get(campo), datetime):
            i[campo] = i[campo].isoformat()
    return i

# ─────────────────────────────────────────────
#  ANALISI AI IN BACKGROUND
# ─────────────────────────────────────────────

def analizza_immagine_ai(sinistro_id: str, image_url: str):
    import time

    if not gemini_disponibile:
        print(f"[AI] Gemini non disponibile — sinistro {sinistro_id} non analizzato.")
        try:
            col_sinistri.update_one(
                {"_id": ObjectId(sinistro_id)},
                {"$set": {"analisi_ai": {
                    "stato":        "non_disponibile",
                    "errore":       "Gemini API non configurata o chiave non valida.",
                    "data_analisi": datetime.now(UTC)
                }}}
            )
        except Exception as mongo_err:
            print(f"[AI] Impossibile aggiornare MongoDB: {mongo_err}")
        return

    MAX_TENTATIVI = 3
    ATTESA_BASE   = 15

    for tentativo in range(1, MAX_TENTATIVI + 1):
        try:
            print(f"[AI] Tentativo {tentativo}/{MAX_TENTATIVI} per sinistro {sinistro_id}...")
            import requests as http_requests
            risposta_http = http_requests.get(image_url, timeout=15)
            risposta_http.raise_for_status()

            risposta = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    PROMPT_PERITO,
                    types.Part.from_bytes(
                        data=risposta_http.content,
                        mime_type="image/jpeg"
                    )
                ]
            )
            risultato_ai = risposta.text.strip()
            print(f"✅ [AI] Analisi completata per sinistro {sinistro_id}")

            col_sinistri.update_one(
                {"_id": ObjectId(sinistro_id)},
                {"$set": {"analisi_ai": {
                    "testo":        risultato_ai,
                    "modello":      GEMINI_MODEL,
                    "data_analisi": datetime.now(UTC),
                    "stato":        "completata"
                }}}
            )
            return

        except Exception as e:
            print(f"[AI] Errore tentativo {tentativo}/{MAX_TENTATIVI}: {e}")
            if tentativo < MAX_TENTATIVI:
                attesa = ATTESA_BASE * tentativo
                print(f"[AI] Attendo {attesa}s prima di ritentare...")
                time.sleep(attesa)
            else:
                try:
                    col_sinistri.update_one(
                        {"_id": ObjectId(sinistro_id)},
                        {"$set": {"analisi_ai": {
                            "stato":        "errore",
                            "errore":       str(e),
                            "data_analisi": datetime.now(UTC)
                        }}}
                    )
                except Exception as mongo_err:
                    print(f"[AI] Impossibile aggiornare MongoDB dopo errore: {mongo_err}")

# ═════════════════════════════════════════════
#  ROTTE — SINISTRI  (Proto_Sinistro_SC)
# ═════════════════════════════════════════════

@app.route("/sinistro", methods=["POST"])
def apri_sinistro():
    """
    Crea un nuovo sinistro.

    Body JSON:
      officina_id          int       (opzionale)
      targa                str       obbligatorio
      modello_veicolo      str
      descrizione_danno    str       obbligatorio
      data_sinistro        str       ISO 8601, obbligatorio
      cliente              str
      compagnia_assicurativa str
      numero_sinistro      str
      telaio               str
      priorita             str       default 'normale'
      note                 str
      contatto_cliente     {telefono, email}
    """
    err = _richiedi_mongo()
    if err:
        return err

    data = request.json or {}
    required = ["targa", "data_sinistro", "descrizione_danno"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Campi obbligatori mancanti: {required}"}), 400

    try:
        data_sinistro_dt = datetime.fromisoformat(data["data_sinistro"])
    except (ValueError, TypeError):
        return jsonify({"error": "Formato data_sinistro non valido. Usa YYYY-MM-DDTHH:MM:SS."}), 400

    try:
        nuovo_sinistro = {
            "officina_id":             data.get("officina_id"),
            "attivo":                  True,
            "targa":                   data["targa"],
            "modello_veicolo":         data.get("modello_veicolo"),
            "descrizione_danno":       data["descrizione_danno"],
            "data_sinistro":           data_sinistro_dt,
            "cliente":                 data.get("cliente"),
            "compagnia_assicurativa":  data.get("compagnia_assicurativa"),
            "numero_sinistro":         data.get("numero_sinistro"),
            "telaio":                  data.get("telaio"),
            "data_assegnazione":       datetime.now(UTC),
            "priorita":                data.get("priorita", "normale"),
            "stato_sinistro":          "aperto",
            "note":                    data.get("note"),
            "contatto_cliente":        data.get("contatto_cliente", {}),
            "preventivo": {
                "data":             None,
                "costo_totale":     None,
                "ore_manodopera":   None,
                "giorni_previsti":  None,
                "stato":            "da_creare",
                "dettaglio_voci":   [],
                "fattura":          None
            },
            "immagini":    [],
            "analisi_ai":  None
        }

        result = col_sinistri.insert_one(nuovo_sinistro)
        return jsonify({"status": "success", "mongo_id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sinistri", methods=["GET"])
def get_tutti_sinistri():
    """
    Lista sinistri. Query params opzionali:
      officina_id   int   → filtra per officina
      attivo        bool  → filtra per stato attivo/inattivo
    """
    err = _richiedi_mongo()
    if err:
        return err

    try:
        filtro = {}
        officina_id = request.args.get("officina_id")
        if officina_id:
            filtro["officina_id"] = int(officina_id)
        attivo = request.args.get("attivo")
        if attivo is not None:
            filtro["attivo"] = attivo.lower() in ("1", "true", "yes")

        sinistri = list(col_sinistri.find(filtro).sort("data_assegnazione", DESCENDING))
        for s in sinistri:
            _serializza_sinistro(s)
        return jsonify(sinistri), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sinistro/<sinistro_id>", methods=["GET"])
def get_sinistro_by_id(sinistro_id):
    err = _richiedi_mongo()
    if err:
        return err

    if not ObjectId.is_valid(sinistro_id):
        return jsonify({"error": "ID sinistro non valido"}), 400
    try:
        s = col_sinistri.find_one({"_id": ObjectId(sinistro_id)})
        if not s:
            return jsonify({"error": "Sinistro non trovato"}), 404
        return jsonify(_serializza_sinistro(s)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sinistro/<sinistro_id>", methods=["PUT"])
def aggiorna_sinistro(sinistro_id):
    """
    Aggiorna campi del sinistro.
    Campi aggiornabili: stato_sinistro, descrizione_danno, note,
                        priorita, officina_id, attivo, contatto_cliente.
    """
    err = _richiedi_mongo()
    if err:
        return err

    if not ObjectId.is_valid(sinistro_id):
        return jsonify({"error": "ID non valido"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dati mancanti"}), 400

    campi_ammessi = [
        "stato_sinistro", "descrizione_danno", "note",
        "priorita", "officina_id", "attivo", "contatto_cliente"
    ]
    update_set = {k: data[k] for k in campi_ammessi if k in data}
    if not update_set:
        return jsonify({"error": "Nessun campo aggiornabile fornito"}), 400

    try:
        result = col_sinistri.update_one(
            {"_id": ObjectId(sinistro_id)},
            {"$set": update_set}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404
        return jsonify({"status": "success", "campi_aggiornati": list(update_set.keys())}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sinistro/<sinistro_id>", methods=["DELETE"])
def elimina_sinistro(sinistro_id):
    err = _richiedi_mongo()
    if err:
        return err

    if not ObjectId.is_valid(sinistro_id):
        return jsonify({"error": "ID sinistro non valido"}), 400
    try:
        result = col_sinistri.delete_one({"_id": ObjectId(sinistro_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404
        # Elimina anche gli interventi collegati
        interventi_eliminati = col_interventi.delete_many({"sinistro_id": sinistro_id})
        return jsonify({
            "status":               "eliminato",
            "id":                   sinistro_id,
            "interventi_eliminati": interventi_eliminati.deleted_count
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
#  PREVENTIVO (sotto-documento del sinistro)
# ─────────────────────────────────────────────

@app.route("/sinistro/<sinistro_id>/preventivo", methods=["PUT"])
def aggiorna_preventivo(sinistro_id):
    """
    Aggiorna il sotto-documento preventivo di un sinistro.

    Body JSON (tutti opzionali):
      data            str ISO 8601
      costo_totale    float
      ore_manodopera  float
      giorni_previsti int
      stato           str  (es. 'da_creare', 'bozza', 'inviato', 'approvato')
      dettaglio_voci  list [{descrizione, quantita, prezzo_unitario}]
      fattura         str  (riferimento fattura)
    """
    err = _richiedi_mongo()
    if err:
        return err

    if not ObjectId.is_valid(sinistro_id):
        return jsonify({"error": "ID sinistro non valido"}), 400

    data = request.get_json() or {}
    update_fields = {}

    if "data" in data:
        try:
            update_fields["preventivo.data"] = datetime.fromisoformat(data["data"])
        except (ValueError, TypeError):
            return jsonify({"error": "Formato data preventivo non valido"}), 400

    for campo in ("costo_totale", "ore_manodopera", "giorni_previsti",
                  "stato", "dettaglio_voci", "fattura"):
        if campo in data:
            update_fields[f"preventivo.{campo}"] = data[campo]

    if not update_fields:
        return jsonify({"error": "Nessun campo preventivo fornito"}), 400

    try:
        result = col_sinistri.update_one(
            {"_id": ObjectId(sinistro_id)},
            {"$set": update_fields}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404
        return jsonify({"status": "success", "campi_aggiornati": list(update_fields.keys())}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═════════════════════════════════════════════
#  ROTTE — INTERVENTI  (Proto_Intervento_SC)
# ═════════════════════════════════════════════

@app.route("/sinistro/<sinistro_id>/interventi", methods=["GET"])
def get_interventi_sinistro(sinistro_id):
    """Restituisce tutti gli interventi associati a un sinistro (per _id stringa)."""
    err = _richiedi_mongo()
    if err:
        return err

    try:
        interventi = list(col_interventi.find({"sinistro_id": sinistro_id}))
        for i in interventi:
            _serializza_intervento(i)
        return jsonify(interventi), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/officina/<int:officina_id>/interventi", methods=["GET"])
def get_interventi_officina(officina_id):
    """
    Restituisce tutti gli interventi di un'officina.
    Query param opzionale: stato (es. 'in_corso', 'completato', 'in_attesa')
    """
    err = _richiedi_mongo()
    if err:
        return err

    try:
        filtro = {"officina_id": officina_id}
        stato = request.args.get("stato")
        if stato:
            filtro["stato"] = stato

        interventi = list(col_interventi.find(filtro).sort("data_inizio", DESCENDING))
        for i in interventi:
            _serializza_intervento(i)
        return jsonify(interventi), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/intervento/<intervento_id>", methods=["GET"])
def get_intervento_by_id(intervento_id):
    err = _richiedi_mongo()
    if err:
        return err

    if not ObjectId.is_valid(intervento_id):
        return jsonify({"error": "ID intervento non valido"}), 400
    try:
        i = col_interventi.find_one({"_id": ObjectId(intervento_id)})
        if not i:
            return jsonify({"error": "Intervento non trovato"}), 404
        return jsonify(_serializza_intervento(i)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/intervento", methods=["POST"])
def crea_intervento():
    """
    Crea un nuovo intervento.

    Body JSON:
      sinistro_id        str   obbligatorio (_id del sinistro come stringa)
      officina_id        int   obbligatorio
      veicolo_targa      str   obbligatorio
      data_inizio        str   ISO 8601
      tipo_intervento    str   es. 'meccanica', 'carrozzeria', 'elettrica'
      descrizione_lavori str
      ricambi_utilizzati list  [{nome, codice, costo}]
      manodopera_ore     float
      foto_prima         list  [url_string]
      note_tecnico       str
    """
    err = _richiedi_mongo()
    if err:
        return err

    data = request.get_json() or {}
    required = ["sinistro_id", "officina_id", "veicolo_targa"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Campi obbligatori mancanti: {required}"}), 400

    data_inizio = None
    if data.get("data_inizio"):
        try:
            data_inizio = datetime.fromisoformat(data["data_inizio"])
        except (ValueError, TypeError):
            return jsonify({"error": "Formato data_inizio non valido"}), 400

    try:
        nuovo_intervento = {
            "sinistro_id":         data["sinistro_id"],
            "officina_id":         data["officina_id"],
            "veicolo_targa":       data["veicolo_targa"],
            "data_inizio":         data_inizio or datetime.now(UTC),
            "data_fine":           None,
            "tipo_intervento":     data.get("tipo_intervento"),
            "descrizione_lavori":  data.get("descrizione_lavori"),
            "ricambi_utilizzati":  data.get("ricambi_utilizzati", []),
            "manodopera_ore":      data.get("manodopera_ore", 0),
            "foto_prima":          data.get("foto_prima", []),
            "foto_dopo":           [],
            "note_tecnico":        data.get("note_tecnico"),
            "stato":               "in_attesa"
        }

        result = col_interventi.insert_one(nuovo_intervento)
        # Aggiorna lo stato del sinistro collegato
        col_sinistri.update_one(
            {"_id": ObjectId(data["sinistro_id"])} if ObjectId.is_valid(data["sinistro_id"])
            else {"numero_sinistro": data["sinistro_id"]},
            {"$set": {"stato_sinistro": "in_riparazione"}}
        )
        return jsonify({"status": "success", "mongo_id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/intervento/<intervento_id>", methods=["PUT"])
def aggiorna_intervento(intervento_id):
    """
    Aggiorna un intervento.

    Body JSON (tutti opzionali):
      tipo_intervento, descrizione_lavori, ricambi_utilizzati,
      manodopera_ore, foto_dopo, note_tecnico, stato,
      data_fine (ISO 8601)
    """
    err = _richiedi_mongo()
    if err:
        return err

    if not ObjectId.is_valid(intervento_id):
        return jsonify({"error": "ID intervento non valido"}), 400

    data = request.get_json() or {}
    campi_ammessi = [
        "tipo_intervento", "descrizione_lavori", "ricambi_utilizzati",
        "manodopera_ore", "foto_dopo", "note_tecnico", "stato"
    ]
    update_set = {k: data[k] for k in campi_ammessi if k in data}

    if "data_fine" in data:
        try:
            update_set["data_fine"] = datetime.fromisoformat(data["data_fine"])
        except (ValueError, TypeError):
            return jsonify({"error": "Formato data_fine non valido"}), 400

    if not update_set:
        return jsonify({"error": "Nessun campo aggiornabile fornito"}), 400

    try:
        result = col_interventi.update_one(
            {"_id": ObjectId(intervento_id)},
            {"$set": update_set}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Intervento non trovato"}), 404

        # Se l'intervento è completato, aggiorna lo stato del sinistro
        if update_set.get("stato") == "completato":
            intervento = col_interventi.find_one({"_id": ObjectId(intervento_id)}, {"sinistro_id": 1})
            if intervento and intervento.get("sinistro_id"):
                sin_id = intervento["sinistro_id"]
                try:
                    col_sinistri.update_one(
                        {"_id": ObjectId(sin_id)} if ObjectId.is_valid(sin_id) else {"numero_sinistro": sin_id},
                        {"$set": {"stato_sinistro": "riparazione_completata"}}
                    )
                except Exception:
                    pass

        return jsonify({"status": "success", "campi_aggiornati": list(update_set.keys())}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/intervento/<intervento_id>/foto-dopo", methods=["POST"])
def aggiungi_foto_dopo(intervento_id):
    """Aggiunge foto post-intervento tramite Cloudinary."""
    err = _richiedi_mongo()
    if err:
        return err

    if not ObjectId.is_valid(intervento_id):
        return jsonify({"error": "ID intervento non valido"}), 400

    if not _STORAGE_DISPONIBILE:
        return jsonify({"error": "Storage Cloudinary non disponibile."}), 503

    files = request.files.getlist("foto") or ([request.files.get("foto")] if request.files.get("foto") else [])
    if not files:
        return jsonify({"error": "Nessuna foto fornita"}), 400

    try:
        intervento = col_interventi.find_one({"_id": ObjectId(intervento_id)})
        if not intervento:
            return jsonify({"error": "Intervento non trovato"}), 404

        foto_urls = []
        for file in files:
            info = carica_immagine(file.read(), intervento_id)
            foto_urls.append(info["secure_url"])

        col_interventi.update_one(
            {"_id": ObjectId(intervento_id)},
            {"$push": {"foto_dopo": {"$each": foto_urls}}}
        )
        return jsonify({"status": "success", "foto_aggiunte": len(foto_urls), "urls": foto_urls}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/intervento/<intervento_id>/ricambio", methods=["POST"])
def aggiungi_ricambio(intervento_id):
    """
    Aggiunge un ricambio alla lista ricambi_utilizzati di un intervento.

    Body JSON:
      nome    str   obbligatorio
      codice  str
      costo   float
    """
    err = _richiedi_mongo()
    if err:
        return err

    if not ObjectId.is_valid(intervento_id):
        return jsonify({"error": "ID intervento non valido"}), 400

    data = request.get_json() or {}
    if not data.get("nome"):
        return jsonify({"error": "Campo 'nome' obbligatorio"}), 400

    ricambio = {
        "nome":   data["nome"],
        "codice": data.get("codice"),
        "costo":  data.get("costo", 0)
    }

    try:
        result = col_interventi.update_one(
            {"_id": ObjectId(intervento_id)},
            {"$push": {"ricambi_utilizzati": ricambio}}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Intervento non trovato"}), 404
        return jsonify({"status": "success", "ricambio": ricambio}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/intervento/<intervento_id>", methods=["DELETE"])
def elimina_intervento(intervento_id):
    err = _richiedi_mongo()
    if err:
        return err

    if not ObjectId.is_valid(intervento_id):
        return jsonify({"error": "ID intervento non valido"}), 400
    try:
        result = col_interventi.delete_one({"_id": ObjectId(intervento_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Intervento non trovato"}), 404
        return jsonify({"status": "eliminato", "id": intervento_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═════════════════════════════════════════════
#  ROTTE — UPLOAD IMMAGINI + ANALISI AI
# ═════════════════════════════════════════════

@app.route("/sinistro/<sinistro_id>/immagini", methods=["POST"])
def aggiungi_immagine(sinistro_id):
    err = _richiedi_mongo()
    if err:
        return err

    if not ObjectId.is_valid(sinistro_id):
        return jsonify({"error": "ID sinistro non valido"}), 400

    if not _STORAGE_DISPONIBILE:
        return jsonify({"error": "Storage Cloudinary non disponibile."}), 503

    if "immagini" not in request.files and "immagine" not in request.files:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    files = request.files.getlist("immagini") or [request.files.get("immagine")]

    try:
        sinistro = col_sinistri.find_one({"_id": ObjectId(sinistro_id)})
        if not sinistro:
            return jsonify({"error": "Sinistro non trovato"}), 404

        immagini_caricate = []
        for file in files:
            print(f"☁️  Caricamento immagine su Cloudinary per sinistro {sinistro_id}...")
            info_cloudinary = carica_immagine(file.read(), sinistro_id)
            print(f"✅ Immagine caricata: {info_cloudinary['secure_url']}")
            immagini_caricate.append({
                "url":       info_cloudinary["secure_url"],
                "public_id": info_cloudinary["public_id"]
            })
            if gemini_disponibile:
                thread = threading.Thread(
                    target=analizza_immagine_ai,
                    args=(sinistro_id, info_cloudinary["secure_url"]),
                    daemon=True
                )
                thread.start()

        stato_analisi = "in_elaborazione" if gemini_disponibile else "non_disponibile"

        col_sinistri.update_one(
            {"_id": ObjectId(sinistro_id)},
            {
                "$push": {"immagini": {"$each": immagini_caricate}},
                "$set":  {"analisi_ai": {
                    "stato":      stato_analisi,
                    "data_avvio": datetime.now(UTC)
                }}
            }
        )

        return jsonify({
            "status":           "accepted",
            "id_sinistro":      sinistro_id,
            "immagini":         [i["url"] for i in immagini_caricate],
            "messaggio":        f"{len(immagini_caricate)} immagini salvate."
                                + (" Analisi AI avviata in background." if gemini_disponibile
                                   else " Analisi AI non disponibile."),
            "analisi_ai_stato": stato_analisi
        }), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/sinistro/<sinistro_id>/analisi", methods=["GET"])
def get_analisi_ai(sinistro_id):
    err = _richiedi_mongo()
    if err:
        return err

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


# ═════════════════════════════════════════════
#  ROTTE — SOCCORSO
# ═════════════════════════════════════════════

@app.route("/soccorso", methods=["POST"])
def crea_richiesta_soccorso():
    data = request.get_json()

    targa            = data.get("targa")
    id_sinistro      = data.get("id_sinistro")
    id_officina      = data.get("id_officina")
    lat              = data.get("lat")
    lon              = data.get("lon")
    via              = data.get("via")
    orario_arrivo    = data.get("orario_arrivo")
    durata_soccorso  = data.get("durata_soccorso")

    if not targa:
        return jsonify({"error": "Targa obbligatoria"}), 400

    conn = None
    try:
        conn   = get_mysql()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT v.id AS veicolo_id, a.id AS automobilista_id
            FROM Veicolo v
            JOIN Automobilista a ON v.automobilista_id = a.id
            WHERE v.targa = %s
        """, (targa,))

        veicolo = cursor.fetchone()
        if veicolo is None:
            return jsonify({"error": "Veicolo non trovato"}), 404

        cursor.execute("""
            INSERT INTO Richiesta_Soccorso
            (id_sinistro, id_automobilista, id_officina, id_veicolo_soccorso,
             data_richiesta, orario_arrivo, durata_soccorso, stato)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_sinistro,
            veicolo["automobilista_id"],
            id_officina,
            veicolo["veicolo_id"],
            datetime.now(timezone.utc),
            orario_arrivo,
            durata_soccorso,
            "in_attesa"
        ))

        richiesta_id = cursor.lastrowid
        conn.commit()

        posizione = None
        if lat is not None and lon is not None:
            posizione = {"tipo": "gps", "lat": lat, "lon": lon}
        elif via:
            posizione = {"tipo": "indirizzo", "via": via}

        mongo_id = None
        if _MONGO_DISPONIBILE and soccorso_col is not None:
            res = soccorso_col.insert_one({
                "richiesta_mysql_id": richiesta_id,
                "id_sinistro":        id_sinistro,
                "id_automobilista":   veicolo["automobilista_id"],
                "id_officina":        id_officina,
                "id_veicolo":         veicolo["veicolo_id"],
                "targa":              targa,
                "posizione":          posizione,
                "orario_arrivo":      orario_arrivo,
                "durata_soccorso":    durata_soccorso,
                "stato":              "in_attesa",
                "data_richiesta":     datetime.now(timezone.utc)
            })
            mongo_id = str(res.inserted_id)

        return jsonify({
            "success":         True,
            "richiesta_id":    richiesta_id,
            "mongo_id":        mongo_id,
            "id_sinistro":     id_sinistro,
            "id_automobilista": veicolo["automobilista_id"],
            "id_officina":     id_officina,
            "id_veicolo":      veicolo["veicolo_id"],
            "posizione":       posizione,
            "orario_arrivo":   orario_arrivo,
            "durata_soccorso": durata_soccorso,
            "stato":           "in_attesa",
            "message":         "Richiesta di soccorso inviata con successo"
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/soccorso/utente/<int:automobilista_id>", methods=["GET"])
def get_soccorsi_utente(automobilista_id):
    conn = None
    try:
        conn   = get_mysql()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT rs.id, rs.id_automobilista, rs.data_richiesta, rs.stato
            FROM Richiesta_Soccorso rs
            WHERE rs.id_automobilista = (
                SELECT id FROM Automobilista WHERE id_utente = %s
            )
            ORDER BY rs.data_richiesta DESC
        """, (automobilista_id,))
        richieste = cursor.fetchall()
        for r in richieste:
            if isinstance(r.get("data_richiesta"), datetime):
                r["data_richiesta"] = r["data_richiesta"].isoformat()
        return jsonify(richieste), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# ═════════════════════════════════════════════
#  ROTTE — VEICOLI  (MySQL)
# ═════════════════════════════════════════════

@app.route("/veicoli-utente/<int:user_id>", methods=["GET"])
def get_veicoli_utente(user_id):
    conn = None
    try:
        conn   = get_mysql()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT v.id, v.targa, v.marca, v.modello, v.anno_immatricolazione,
                   a.nome AS nome_proprietario, a.cognome AS cognome_proprietario
            FROM Veicolo v
            JOIN Automobilista a ON v.automobilista_id = a.id
            WHERE a.id_utente = %s
        """, (user_id,))
        return jsonify(cursor.fetchall()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/veicolo/user/<int:user_id>", methods=["POST"])
def crea_veicolo_utente(user_id):
    data = request.get_json()
    if not data or "targa" not in data:
        return jsonify({"error": "Campo obbligatorio mancante: targa"}), 400

    conn = None
    try:
        conn   = get_mysql()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM Automobilista WHERE id_utente = %s", (user_id,))
        auto = cursor.fetchone()
        if not auto:
            return jsonify({"error": f"Automobilista con id_utente={user_id} non trovato"}), 404
        automobilista_id = auto["id"]

        cursor.execute(
            "INSERT INTO Veicolo (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id) VALUES (%s,%s,%s,%s,%s,%s)",
            (data.get("targa"), data.get("n_telaio"), data.get("marca"),
             data.get("modello"), data.get("anno_immatricolazione"), automobilista_id)
        )
        conn.commit()
        return jsonify({
            "status":           "success",
            "message":          "Veicolo creato con successo",
            "veicolo_id":       cursor.lastrowid,
            "automobilista_id": automobilista_id
        }), 201

    except mysql.connector.IntegrityError:
        if conn:
            conn.rollback()
        return jsonify({"error": "Targa o numero telaio già esistente"}), 409
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# ─────────────────────────────────────────────
#  AVVIO
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("\n📋 Stato sottosistemi all'avvio:")
    print(f"   MongoDB  : {'✅ disponibile' if _MONGO_DISPONIBILE  else '❌ non disponibile'}")
    print(f"   Gemini   : {'✅ disponibile' if gemini_disponibile  else '⚠️  non disponibile'}")
    print(f"   Storage  : {'✅ disponibile' if _STORAGE_DISPONIBILE else '❌ non disponibile'}\n")
    app.run(debug=True, host="0.0.0.0", port=7000)