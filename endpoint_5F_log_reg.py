from flask import Flask, request, jsonify
import mysql.connector
import re
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timedelta, timezone
from flask_cors import CORS
from dotenv import load_dotenv
import os
import jwt
import bcrypt
from functools import wraps

app = Flask(__name__)
CORS(app)

# ── Configurazione ───────────────────────────────────────────────────────────
load_dotenv()

MYSQL_CONFIG = {
    "host":     os.getenv("MYSQL_HOST"),
    "port":     int(os.getenv("MYSQL_PORT", 3306)),
    "user":     os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
}

MONGO_URI            = os.getenv("MONGO_URI")
JWT_SECRET           = os.getenv("JWT_SECRET", "cambia-questa-chiave-in-produzione")
JWT_ALGORITHM        = "HS256"
JWT_ACCESS_HOURS     = 1          # access token: breve durata
JWT_REFRESH_DAYS     = 30         # refresh token: lunga durata
BCRYPT_ROUNDS        = 12         # costo hashing bcrypt

# ── MongoDB ──────────────────────────────────────────────────────────────────
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_db     = mongo_client["FakeClaim"]
    mongo_client.admin.command("ping")
    print("✅ Connessione a MongoDB Atlas riuscita!")
except Exception as e:
    print(f"❌ Errore critico connessione MongoDB: {e}")

# Collezione blacklist — un documento per ogni token revocato
blacklist_collection = mongo_db["token_blacklist"]

# Indice TTL: MongoDB elimina automaticamente i documenti scaduti
try:
    blacklist_collection.create_index("exp", expireAfterSeconds=0)
except Exception:
    pass  # indice già esistente


# ── MySQL helper ─────────────────────────────────────────────────────────────
def get_mysql_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)

TABELLA_PER_RUOLO = {
    "automobilista": "Automobilista",
    "perito":        "Perito",
    "assicuratore":  "Assicuratore",
}


# ── Password helpers ─────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Restituisce l'hash bcrypt della password in chiaro."""
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verifica_password(plain: str, hashed: str) -> bool:
    """Confronta la password in chiaro con l'hash salvato nel DB."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT helpers ──────────────────────────────────────────────────────────────
def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def genera_access_token(user_id: int, ruolo: str) -> str:
    """JWT di breve durata (1 h) per autenticare le richieste API."""
    payload = {
        "sub":   user_id,
        "ruolo": ruolo,
        "type":  "access",
        "iat":   _now_utc(),
        "exp":   _now_utc() + timedelta(hours=JWT_ACCESS_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def genera_refresh_token(user_id: int, ruolo: str) -> str:
    """JWT di lunga durata (30 gg) per ottenere nuovi access token."""
    payload = {
        "sub":   user_id,
        "ruolo": ruolo,
        "type":  "refresh",
        "iat":   _now_utc(),
        "exp":   _now_utc() + timedelta(days=JWT_REFRESH_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decodifica_token(token: str) -> dict:
    """Decodifica e verifica un JWT; solleva eccezione se non valido."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def _token_in_blacklist(token: str) -> bool:
    """Verifica se il token è stato revocato (presente nella blacklist MongoDB)."""
    return blacklist_collection.find_one({"token": token}) is not None


def _revoca_token(token: str, exp_timestamp: int) -> None:
    """Inserisce il token nella blacklist con la sua scadenza originale."""
    exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    blacklist_collection.update_one(
        {"token": token},
        {"$setOnInsert": {"token": token, "exp": exp_dt}},
        upsert=True,
    )


def token_richiesto(ruoli_ammessi=None, tipo="access"):
    """
    Decoratore che protegge le route verificando il JWT nell'header
    Authorization: Bearer <token>.

    - ruoli_ammessi: lista di ruoli autorizzati (None = tutti)
    - tipo: "access" (default) o "refresh"

    Il payload decodificato viene iniettato in request.jwt_payload.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Token mancante o formato non valido"}), 401

            token = auth_header.split(" ", 1)[1]

            # Controlla blacklist prima di decodificare
            if _token_in_blacklist(token):
                return jsonify({"error": "Token revocato. Effettua nuovamente il login."}), 401

            try:
                payload = _decodifica_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token scaduto. Effettua nuovamente il login."}), 401
            except jwt.InvalidTokenError as e:
                return jsonify({"error": f"Token non valido: {str(e)}"}), 401

            # Verifica tipo token
            if payload.get("type") != tipo:
                return jsonify({"error": f"È richiesto un token di tipo '{tipo}'"}), 401

            # Verifica ruolo
            if ruoli_ammessi and payload.get("ruolo") not in ruoli_ammessi:
                return jsonify({"error": "Accesso non autorizzato per questo ruolo"}), 403

            request.jwt_payload = payload
            request.raw_token   = token
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ── Serializzazione ──────────────────────────────────────────────────────────
def serializza_utente(user: dict) -> dict:
    """Converte tipi non serializzabili in JSON (es. set MySQL → str)."""
    if user and isinstance(user.get("ruolo"), set):
        user["ruolo"] = ",".join(user["ruolo"])
    return user


# ── Validazioni ──────────────────────────────────────────────────────────────
def valida_password(password: str):
    if len(password) < 8:
        return False, "La password deve essere lunga almeno 8 caratteri."
    if not re.search(r"[a-zA-Z]", password):
        return False, "La password deve contenere almeno una lettera."
    if not re.search(r"\d", password):
        return False, "La password deve contenere almeno un numero."
    return True, None


def valida_cf(cf: str):
    cf = cf.strip().upper()
    if len(cf) != 16:
        return False, "Il codice fiscale deve essere di esattamente 16 caratteri."
    if not re.match(r"^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$", cf):
        return False, "Il codice fiscale non è nel formato corretto."
    return True, None


def valida_email(email: str):
    email = email.strip()
    if "@" not in email:
        return False, "L'email deve contenere il simbolo @."
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return False, "Formato email non valido."
    return True, None


def valida_dati_utente(data: dict):
    pattern_nomi = r"^[a-zA-Zàáâäãåèéêëìíîïòóôöùúûüç \s']+$"
    if not re.match(pattern_nomi, data.get("nome", "")):
        return False, "Il nome non è valido."
    if not re.match(pattern_nomi, data.get("cognome", "")):
        return False, "Il cognome non è valido."
    cf_valido, cf_err = valida_cf(data.get("cf", ""))
    if not cf_valido:
        return False, cf_err
    email_valida, email_err = valida_email(data.get("email", ""))
    if not email_valida:
        return False, email_err
    valida_psw, err_psw = valida_password(data.get("password", ""))
    if not valida_psw:
        return False, err_psw
    return True, None


def valida_dati_aggiornamento(data: dict):
    pattern_nomi = r"^[a-zA-Zàáâäãåèéêëìíîïòóôöùúûüç \s']+$"
    if "nome" in data and not re.match(pattern_nomi, data.get("nome", "")):
        return False, "Il nome non è valido."
    if "cognome" in data and not re.match(pattern_nomi, data.get("cognome", "")):
        return False, "Il cognome non è valido."
    if "email" in data:
        email_valida, email_err = valida_email(data.get("email", ""))
        if not email_valida:
            return False, email_err
    return True, None


# ── Registrazione ────────────────────────────────────────────────────────────
@app.route("/registrazione", methods=["POST"])
def registrazione():
    """
    Registra un nuovo automobilista.
    Il campo 'password' viene hashato con bcrypt prima di essere salvato.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    ruolo = data.get("ruolo", "automobilista").lower()
    if ruolo != "automobilista":
        return jsonify({
            "error": "La registrazione pubblica è riservata agli automobilisti. "
                     "Contatta l'amministratore."
        }), 403

    # Legge la password in chiaro dal campo 'password'
    plain_password = data.get("password", "")
    data["password"] = plain_password   # usato da valida_dati_utente

    is_valid, error_message = valida_dati_utente(data)
    if not is_valid:
        return jsonify({"error": error_message}), 400

    # Hash bcrypt
    password_hashed = hash_password(plain_password)

    conn = None
    try:
        conn   = get_mysql_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO Utente
               (nome, cognome, email, telefono, password_hash, ruolo)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                data["nome"].strip().title(),
                data["cognome"].strip().title(),
                data["email"].strip().lower(),
                data.get("telefono"),
                password_hashed,            # ← hash salvato nel DB
                "automobilista",
            ),
        )
        utente_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO Automobilista (nome, cognome, cf, id_utente) VALUES (%s,%s,%s,%s)",
            (
                data["nome"].strip().title(),
                data["cognome"].strip().title(),
                data["cf"].strip().upper(),
                utente_id,
            ),
        )

        conn.commit()
        return jsonify({"status": "success", "id_utente": utente_id}), 201

    except mysql.connector.IntegrityError:
        if conn:
            conn.rollback()
        return jsonify({"error": "Email o CF già registrati"}), 409
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# ── Login ────────────────────────────────────────────────────────────────────
@app.route("/login", methods=["POST"])
def login():
    """
    Autentica l'utente con email + password.
    Restituisce un access token (1 h) e un refresh token (30 gg).
    """
    data     = request.get_json()
    email    = data.get("email")
    password = data.get("password")       # password in chiaro dal client

    if not email or not password:
        return jsonify({"error": "Email e password sono obbligatori"}), 400

    conn = None
    try:
        conn   = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                u.id,
                u.nome,
                u.cognome,
                u.email,
                u.telefono,
                u.ruolo,
                u.password_hash,
                ass.nome AS nome_compagnia
            FROM Utente u
            LEFT JOIN Assicuratore a    ON u.id = a.id_utente
            LEFT JOIN Assicurazione ass ON a.assicurazione_id = ass.id
            WHERE u.email = %s
            """,
            (email.strip().lower(),),
        )

        user = cursor.fetchone()
        if not user:
            # Stessa risposta per email inesistente o password errata (evita user enumeration)
            return jsonify({"error": "Credenziali non valide"}), 401

        # Verifica password con bcrypt
        if not verifica_password(password, user["password_hash"]):
            return jsonify({"error": "Credenziali non valide"}), 401

        # Normalizza ruolo
        if isinstance(user.get("ruolo"), set):
            user["ruolo"] = ",".join(user["ruolo"])

        user["nome_compagnia"] = user.get("nome_compagnia") or ""

        # Genera coppia di token
        access_token  = genera_access_token(user["id"], user["ruolo"])
        refresh_token = genera_refresh_token(user["id"], user["ruolo"])

        # Rimuove il campo hash dalla risposta (non inviare mai al client)
        user.pop("password_hash", None)

        return jsonify({
            "status":        "success",
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "expires_in":    JWT_ACCESS_HOURS * 3600,  # secondi
            "user":          user,
        }), 200

    except Exception as e:
        print(f"[LOGIN ERROR] {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": "Errore interno del server"}), 500
    finally:
        if conn:
            conn.close()


# ── Refresh access token ─────────────────────────────────────────────────────
@app.route("/auth/refresh", methods=["POST"])
@token_richiesto(tipo="refresh")
def refresh_token():
    """
    Accetta un refresh token valido nell'header Authorization.
    Revoca il vecchio refresh token (rotation) e restituisce
    una nuova coppia access + refresh token.
    """
    payload = request.jwt_payload
    old_token = request.raw_token

    # Token rotation: revoca il refresh token usato
    _revoca_token(old_token, payload["exp"])

    new_access  = genera_access_token(payload["sub"], payload["ruolo"])
    new_refresh = genera_refresh_token(payload["sub"], payload["ruolo"])

    return jsonify({
        "status":        "success",
        "access_token":  new_access,
        "refresh_token": new_refresh,
        "expires_in":    JWT_ACCESS_HOURS * 3600,
    }), 200


# ── Logout ───────────────────────────────────────────────────────────────────
@app.route("/auth/logout", methods=["POST"])
@token_richiesto()
def logout():
    """
    Revoca l'access token corrente.
    Il client deve inviare separatamente il refresh token se vuole revocarlo.
    Body opzionale: { "refresh_token": "<token>" }
    """
    payload    = request.jwt_payload
    raw_access = request.raw_token

    # Revoca access token
    _revoca_token(raw_access, payload["exp"])

    # Revoca anche il refresh token se fornito nel body
    body = request.get_json(silent=True) or {}
    raw_refresh = body.get("refresh_token")
    if raw_refresh:
        try:
            ref_payload = _decodifica_token(raw_refresh)
            if ref_payload.get("type") == "refresh":
                _revoca_token(raw_refresh, ref_payload["exp"])
        except jwt.InvalidTokenError:
            pass  # token refresh già scaduto o invalido: non critico

    return jsonify({"status": "success", "message": "Logout effettuato con successo"}), 200


# ── Verifica token ───────────────────────────────────────────────────────────
@app.route("/auth/verifica", methods=["GET"])
@token_richiesto()
def verifica_token():
    """
    Endpoint leggero per controllare se l'access token è ancora valido.
    Il frontend può chiamarlo all'avvio per validare la sessione salvata.
    """
    return jsonify({
        "status":  "valid",
        "user_id": request.jwt_payload["sub"],
        "ruolo":   request.jwt_payload["ruolo"],
        "exp":     request.jwt_payload["exp"],
    }), 200


# ── Cambio password ──────────────────────────────────────────────────────────
@app.route("/utente/<int:user_id>/password", methods=["PUT"])
@token_richiesto()
def cambia_password(user_id):
    """
    Permette all'utente autenticato di cambiare la propria password.
    Richiede la password attuale per conferma.
    """
    if request.jwt_payload["sub"] != user_id:
        return jsonify({"error": "Non puoi modificare la password di un altro utente"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    password_attuale = data.get("password_attuale")
    nuova_password   = data.get("nuova_password")

    if not password_attuale or not nuova_password:
        return jsonify({"error": "Password attuale e nuova password sono obbligatorie"}), 400

    valida_psw, err_psw = valida_password(nuova_password)
    if not valida_psw:
        return jsonify({"error": err_psw}), 400

    conn = None
    try:
        conn   = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT password_hash FROM Utente WHERE id = %s", (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Utente non trovato"}), 404

        if not verifica_password(password_attuale, row["password_hash"]):
            return jsonify({"error": "Password attuale non corretta"}), 401

        nuovo_hash = hash_password(nuova_password)
        cursor.execute(
            "UPDATE Utente SET password_hash = %s WHERE id = %s",
            (nuovo_hash, user_id),
        )
        conn.commit()

        return jsonify({"status": "success", "message": "Password aggiornata con successo"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# ── Aggiornamento profilo ────────────────────────────────────────────────────
@app.route("/utente/<int:user_id>", methods=["PUT"])
@token_richiesto()
def aggiorna_utente(user_id):
    """Aggiorna i dati anagrafici dell'utente (esclusa password)."""
    if request.jwt_payload["sub"] != user_id:
        return jsonify({"error": "Non puoi modificare il profilo di un altro utente"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    campi_utente   = {"nome", "cognome", "email", "telefono"}
    payload_utente = {k: v for k, v in data.items() if k in campi_utente and v is not None}

    if not payload_utente:
        return jsonify({"error": "Nessun campo valido da aggiornare"}), 400

    is_valid, err = valida_dati_aggiornamento(payload_utente)
    if not is_valid:
        return jsonify({"error": err}), 400

    if "nome"    in payload_utente: payload_utente["nome"]    = payload_utente["nome"].strip().title()
    if "cognome" in payload_utente: payload_utente["cognome"] = payload_utente["cognome"].strip().title()
    if "email"   in payload_utente: payload_utente["email"]   = payload_utente["email"].strip().lower()

    conn = None
    try:
        conn   = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        set_clause = ", ".join([f"{col} = %s" for col in payload_utente.keys()])
        values     = list(payload_utente.values()) + [user_id]
        cursor.execute(f"UPDATE Utente SET {set_clause} WHERE id = %s", values)

        if cursor.rowcount == 0:
            return jsonify({"error": "Utente non trovato"}), 404

        conn.commit()

        cursor.execute(
            "SELECT id, nome, cognome, email, telefono, ruolo FROM Utente WHERE id = %s",
            (user_id,),
        )
        user_updated = cursor.fetchone()
        return jsonify({"status": "success", "user": serializza_utente(user_updated)}), 200

    except mysql.connector.IntegrityError:
        return jsonify({"error": "Email già in uso da un altro utente"}), 409
    except mysql.connector.Error as e:
        return jsonify({"error": f"Errore database: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# ── Profilo automobilista ────────────────────────────────────────────────────
@app.route("/automobilista/<int:user_id>/profilo", methods=["GET"])
@token_richiesto(ruoli_ammessi=["automobilista"])
def profilo_automobilista(user_id):
    """
    Restituisce i dati completi dell'automobilista (incluso n_polizza),
    i dati del veicolo e della polizza associata.
    Accessibile solo dall'automobilista proprietario del profilo.
    """
    if request.jwt_payload["sub"] != user_id:
        return jsonify({"error": "Non puoi accedere al profilo di un altro utente"}), 403

    conn = None
    try:
        conn   = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                a.id                          AS automobilista_id,
                a.nome,
                a.cognome,
                a.cf,
                a.id_utente,
                a.n_polizza,
                u.email,
                u.telefono,
                p.id                          AS polizza_id,
                p.n_polizza                   AS polizza_numero,
                p.compagnia_assicurativa,
                p.data_inizio                 AS polizza_data_inizio,
                p.data_scadenza               AS polizza_data_scadenza,
                p.massimale,
                p.tipo_copertura,
                v.targa,
                v.marca,
                v.modello,
                v.anno_immatricolazione
            FROM Automobilista a
            JOIN Utente u         ON u.id = a.id_utente
            LEFT JOIN Veicolo v   ON v.automobilista_id = a.id
            LEFT JOIN Polizza p   ON p.veicolo_id = v.id
            WHERE a.id_utente = %s
            ORDER BY p.data_inizio DESC
            LIMIT 1
            """,
            (user_id,),
        )

        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Automobilista non trovato"}), 404

        for campo in ("polizza_data_inizio", "polizza_data_scadenza"):
            if row.get(campo) and hasattr(row[campo], "isoformat"):
                row[campo] = row[campo].isoformat()

        risposta = {
            "automobilista": {
                "id":        row["automobilista_id"],
                "nome":      row["nome"],
                "cognome":   row["cognome"],
                "cf":        row["cf"],
                "id_utente": row["id_utente"],
                "email":     row["email"],
                "telefono":  row["telefono"],
                "n_polizza": row["n_polizza"],
            },
            "veicolo": {
                "targa":                 row.get("targa"),
                "marca":                 row.get("marca"),
                "modello":               row.get("modello"),
                "anno_immatricolazione": row.get("anno_immatricolazione"),
            } if row.get("targa") else None,
            "polizza": {
                "id":                     row.get("polizza_id"),
                "n_polizza":              row.get("polizza_numero"),
                "compagnia_assicurativa": row.get("compagnia_assicurativa"),
                "data_inizio":            row.get("polizza_data_inizio"),
                "data_scadenza":          row.get("polizza_data_scadenza"),
                "massimale":              row.get("massimale"),
                "tipo_copertura":         row.get("tipo_copertura"),
            } if row.get("polizza_id") else None,
        }

        return jsonify(risposta), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# ── Avvio ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000, debug=True)
