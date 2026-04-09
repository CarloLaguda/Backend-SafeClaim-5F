# 🔍 Code Review - SafeClaim Backend

**Data Review**: Maggio 2024  
**Revisor**: Senior Developer  
**Stato**: ⚠️ REVISION REQUIRED

---

## 📊 Valutazione Complessiva

| Categoria | Voto | Note |
|-----------|------|------|
| **Architettura** | 7/10 | Buona separazione componenti, ma manca modulazione |
| **Sicurezza** | 3/10 | 🔴 CRITICA: Credenziali hardcoded |
| **Error Handling** | 6/10 | Try-except presenti, ma poco specifici |
| **Documentazione** | 7/10 | Commenti buoni, ma manca docstrings |
| **Performance** | 6/10 | Niente cache, query non ottimizzate |
| **Testing** | 2/10 | 🔴 CRITICA: Nessun test automatico |
| **Manutenibilità** | 5/10 | Codice ripetitivo, poca riusabilità |
| **GDPR/Privacy** | 4/10 | ⚠️ Nessuna anonimizzazione dati |
| **Scalabilità** | 4/10 | In-memory store fallisce con molti utenti |

**VOTO FINALE: 5.4/10** ⚠️ Produttivo ma con seri problemi di sicurezza

---

## 🔴 CRITICAL ISSUES

### 1. **CREDENZIALI HARDCODED NEL CODICE**

**Severity**: 🔴 CRITICA  
**File**: `API_Automobilista.py:9`, `API_ChatBot.py:20`, `DB_Creation.py:1-30`

#### ❌ PROBLEMA
```python
# API_Automobilista.py (linea 9)
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"

# API_ChatBot.py (linea 20)
MONGO_URI = "mongodb://safeclaim:0tHz...%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"

# DB_Creation.py (linea 7-8)
EMAIL_CONFIG = {
    "password": "elcgkjhbvqjklost",  # PASSWORD IN CHIARO!
}
```

#### ⚠️ RISCHI
- 🔓 Accesso non autorizzato a MongoDB
- 📧 Spoof email dal compromesso account Gmail
- 💰 Furto dati clienti nei sinistri
- ⚖️ Violazione GDPR (art. 33: obbligo notifica)
- 👮 Responsabilità legale enterprise

#### ✅ SOLUZIONE (FISSA SUBITO)
```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_CONFIG = {
    "connection_string": os.getenv("MONGO_CONNECTION_STRING"),
    "db_name": os.getenv("MONGO_DB_NAME", "FakeClaim")
}

EMAIL_CONFIG = {
    "sender": os.getenv("EMAIL_SENDER"),
    "password": os.getenv("EMAIL_PASSWORD"),  # Da variabile ambiente
    "smtp_server": "smtp.gmail.com",
    "port": 465
}

# .env (NON committare mai in Git!)
MONGO_CONNECTION_STRING=mongodb+srv://user:pass@cluster...
MONGO_DB_NAME=FakeClaim
EMAIL_SENDER=your@gmail.com
EMAIL_PASSWORD=your-app-password
```

#### Implementazione
```bash
# 1. Installa dotenv
pip install python-dotenv

# 2. Crea .env nel root
echo "MONGO_CONNECTION_STRING=..." >> .env
echo ".env" >> .gitignore

# 3. Aggiorna codice per usare config.py
from config import MONGO_CONFIG, EMAIL_CONFIG
CONNECTION_STRING = MONGO_CONFIG["connection_string"]
```

---

### 2. **ARCHIVIAZIONE DATI SENSIBILI SENZA PROTEZIONE**

**Severity**: 🔴 CRITICA  
**File**: Tutte API, `DB_Creation.py`

#### ❌ PROBLEMA
MongoDB salva:
- ✋ Nome e cognome: **DATI PERSONALI** (GDPR)
- ✋ Targa veicolo: **Identificativo univoco**
- ✋ Posizione GPS: **DATI BIOMETRICI INDIRETTI**
- ✋ Feedback conversazioni: **PROFILO COMPORTAMENTO**

**SENZA**: crittografia, accesso control, audit log

#### ⚠️ VIOLAZIONI
- GDPR Articolo 32: "devono adottare misure per proteggere dati"
- GDPR Articolo 17: "diritto all'oblio" non implementato
- GDPR Articolo 30: nessun registro trattamenti

#### ✅ SOLUZIONE
```python
# security.py
from cryptography.fernet import Fernet
import os

class DataEncryption:
    def __init__(self):
        self.cipher = Fernet(os.getenv("ENCRYPTION_KEY").encode())
    
    def encrypt_nome_cognome(self, nome, cognome):
        """Cripta dati personali prima di salvare"""
        full_name = f"{nome}|{cognome}"
        return self.cipher.encrypt(full_name.encode()).decode()
    
    def decrypt_nome_cognome(self, encrypted):
        """Decripta solo per operazioni autorizzate"""
        decrypted = self.cipher.decrypt(encrypted.encode()).decode()
        return decrypted.split("|")

# In API_Automobilista.py
from security import DataEncryption

crypto = DataEncryption()
nuovo_soccorso_mongo = {
    "nome_encrypted": crypto.encrypt_nome_cognome(nome, cognome),
    "targa": targa,  # Potrebbe anche essere hashato
    "posizione": {...}  # Considera privacy-preserving location
}

# Genera encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

### 3. **NESSUN CONTROLLO DI AUTENTICAZIONE/AUTORIZZAZIONE**

**Severity**: 🔴 CRITICA  
**File**: `API_Automobilista.py`, `API_ChatBot.py`

#### ❌ PROBLEMA
```python
@app.route('/soccorso/<string:identificatore>', methods=['GET'])
def get_dettaglo_soccorso(identificatore):
    # CHIUNQUE puo' accedere a QUALUNQUE sinistro!
    mongo_data = mongo_db.Sinistro.find_one({"_id": ObjectId(identificatore)})
```

#### ⚠️ RISCHI
- **Violazione Privacy**: Chiunque vede dati altri utenti
- **Social Engineering**: Enumeration di ID sinistri
- **Insider Threat**: Dipendenti accedono dati non autorizzati
- **GDPR**: Art. 32c violazione

#### ✅ SOLUZIONE
```python
# auth.py
from functools import wraps
from flask import request, jsonify
import jwt
import os

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({"error": "Token mancante"}), 401
        
        try:
            payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
            request.user_id = payload['user_id']
            request.user_role = payload['role']  # "utente", "operatore", "admin"
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token non valido"}), 401
        
        return f(*args, **kwargs)
    return decorated

# In API_Automobilista.py
from auth import token_required

@app.route('/soccorso/<string:identificatore>', methods=['GET'])
@token_required
def get_dettaglio_soccorso(identificatore):
    """GET con autenticazione e autorizzazione"""
    
    # Verifica autorizzazione
    if request.user_role == "utente":
        # Utente puo' vedere solo i SUOI sinistri
        mongo_data = mongo_db.Sinistro.find_one({
            "_id": ObjectId(identificatore),
            "user_id": request.user_id  # ← Filtro critico
        })
    elif request.user_role == "operatore":
        # Operatore puo' vedere sinistri assegnati
        mongo_data = mongo_db.Sinistro.find_one({
            "_id": ObjectId(identificatore),
            "operatore_assegnato": request.user_id
        })
    
    if not mongo_data:
        return jsonify({"error": "Non autorizzato"}), 403
    
    return jsonify({"soccorso_info": mongo_data}), 200

# Login endpoint (da aggiungere)
@app.route('/auth/login', methods=['POST'])
def login():
    """Genera JWT token dopo autenticazione"""
    credentials = request.json
    
    # Verifica credenziali (contro DB)
    user = db.users.find_one({"email": credentials['email']})
    
    if not user or not check_password(credentials['password'], user['password_hash']):
        return jsonify({"error": "Credenziali non valide"}), 401
    
    token = jwt.encode({
        'user_id': str(user['_id']),
        'role': user['role'],
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, os.getenv("JWT_SECRET"), algorithm="HS256")
    
    return jsonify({"token": token}), 200
```

---

## 🟡 HIGH PRIORITY ISSUES

### 4. **VALIDAZIONE INPUT INSUFFICIENTE**

**Severity**: 🟡 ALTA  
**File**: `API_Automobilista.py:30-40`

#### ❌ PROBLEMA
```python
# Accetta direttamente dati dell'utente senza sanificazione
nome = data.get('nome', "Sconosciuto")
cognome = data.get('cognome', "Sconosciuto")
descrizione_guasto = data.get('descrizione', "Richiesta soccorso stradale")

# Rischi:
# 1. Nessuna lunghezza massima → DOS
# 2. Nessun check caratteri → Injection
# 3. Nessun range lat/lon → Coordinate invalide
```

#### ✅ SOLUZIONE
```python
# validators.py
from marshmallow import Schema, fields, ValidationError

class SoccorsoSchema(Schema):
    nome = fields.String(required=True, validate=lambda x: 2 <= len(x) <= 50)
    cognome = fields.String(required=True, validate=lambda x: 2 <= len(x) <= 50)
    targa = fields.String(required=True, validate=lambda x: len(x) == 7)  # IT: AA123BB
    lat = fields.Float(required=True, validate=lambda x: -90 <= x <= 90)
    lon = fields.Float(required=True, validate=lambda x: -180 <= x <= 180)
    descrizione = fields.String(required=False, validate=lambda x: len(x) <= 500)

# In API_Automobilista.py
@app.route('/soccorso', methods=['POST'])
def crea_richiesta_soccorso():
    schema = SoccorsoSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    
    # ... resto del codice
```

---

### 5. **ERROR HANDLING TROPPO GENERICO**

**Severity**: 🟡 ALTA  
**File**: Tutti i file

#### ❌ PROBLEMA
```python
except pymongo.errors.PyMongoError as e:
    return jsonify({"error": f"Errore Database MongoDB: {str(e)}"}), 500

except Exception as e:  # ← TROPPO GENERICO
    return jsonify({"error": f"Errore generico: {str(e)}"}), 500
```

#### Rischi
- Exposing stack trace interno a client (security)
- Difficile debugging in produzione
- Non distingue errori recoverable da critical

#### ✅ SOLUZIONE
```python
# errors.py
class SafeClaimException(Exception):
    def __init__(self, message, status_code=500, log_level="error"):
        self.message = message
        self.status_code = status_code
        self.log_level = log_level

class TargaEccezioneMancante(SafeClaimException):
    def __init__(self):
        super().__init__("Targa veicolo mancante", 400, "warning")

class DatabaseConnessioneFallita(SafeClaimException):
    def __init__(self, original_error):
        super().__init__("Database temporaneamente non disponibile", 503, "critical")
        self.original_error = original_error

# In API_Automobilista.py
@app.route('/soccorso', methods=['POST'])
def crea_richiesta_soccorso():
    try:
        data = request.json
        if not data:
            raise SafeClaimException("Corpo richiesta vuoto", 400, "warning")
        
        targa = data.get('targa')
        if not targa:
            raise TargaEccezioneMancante()
        
        try:
            result = mongo_db.Sinistro.insert_one(nuovo_soccorso_mongo)
        except pymongo.errors.ServerSelectionTimeoutError as e:
            raise DatabaseConnessioneFallita(e)
    
    except SafeClaimException as e:
        logger.log(e.log_level, e.message)
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        return jsonify({"error": "Errore interno server"}), 500  # NON esporre dettagli

@app.errorhandler(500)
def handle_500(error):
    logger.critical(f"500 error: {error}")
    return jsonify({"error": "Errore interno"}), 500
```

---

### 6. **SESSION IN-MEMORY → PERDE DATI SU CRASH**

**Severity**: 🟡 ALTA  
**File**: `API_ChatBot.py:18`

#### ❌ PROBLEMA
```python
active_sessions = {}  # ← Dizionario in memoria volatile

# Se server crasha/restart:
# - Tutte le sessioni attive perdute
# - Dati conversazioni non salvati
# - Cattiva UX: "La tua sessione è scaduta"
```

#### ✅ SOLUZIONE
```python
# session_manager.py
import redis
from datetime import datetime, timedelta

class SessionManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=6379,
            decode_responses=True
        )
        self.session_ttl = 3600  # 1 ora
    
    def create_session(self, session_id):
        session_data = {
            "created_at": datetime.now().isoformat(),
            "messages": "[]",  # JSON stringato
            "feedback": "[]"
        }
        self.redis_client.hset(f"session:{session_id}", mapping=session_data)
        self.redis_client.expire(f"session:{session_id}", self.session_ttl)
    
    def get_session(self, session_id):
        data = self.redis_client.hgetall(f"session:{session_id}")
        return ConversationSession.from_dict(data) if data else None
    
    def save_session(self, session):
        self.redis_client.hset(
            f"session:{session.session_id}",
            mapping=session.to_dict()
        )

# In API_ChatBot.py
from session_manager import SessionManager

session_mgr = SessionManager()

@app.route('/chat/init', methods=['POST'])
def init_chat():
    session_id = str(uuid.uuid4())
    session_mgr.create_session(session_id)
    return jsonify({"status": "success", "session_id": session_id}), 200

@app.route('/chat', methods=['POST'])
def chat_bot():
    data = request.json
    session = session_mgr.get_session(data['session_id'])
    # ... elabora messaggio
    session_mgr.save_session(session)  # Persist immediato
```

---

## 🟠 MEDIUM PRIORITY ISSUES

### 7. **MANCANZA DI LOGGING STRUTTURATO**

**Severity**: 🟠 MEDIA  
**File**: Tutti

#### ❌ PROBLEMA
```python
print("✅ Connessione a MongoDB Atlas riuscita!")
print(f"❌ Errore critico di connessione a MongoDB: {e}")
```

#### Perché è male
- Print statement non scalano in produzione
- Difficile cercare/filtrare logs
- Niente timestamp strutturato
- Impossibile integrazione ELK/Datadog/CloudWatch

#### ✅ SOLUZIONE
```python
# logging_config.py
import logging
import logging.handlers
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "path": f"{record.filename}:{record.lineno}"
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    
    # File handler (per persistence)
    file_handler = logging.handlers.RotatingFileHandler(
        f"/var/log/safeclaim/{name}.log",
        maxBytes=100*1024*1024,  # 100MB
        backupCount=10
    )
    file_handler.setFormatter(JSONFormatter())
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# In API_Automobilista.py
logger = setup_logger("API_Automobilista")

try:
    mongo_client = pymongo.MongoClient(CONNECTION_STRING)
    mongo_client.admin.command('ping')
    logger.info("MongoDB connection established", extra={"database": DB_NAME})
except Exception as e:
    logger.error("MongoDB connection failed", exc_info=True)
```

---

### 8. **NESSUN RATE LIMITING / DOS PROTECTION**

**Severity**: 🟠 MEDIA  
**File**: `API_Automobilista.py`, `API_ChatBot.py`

#### ❌ PROBLEMA
Chiunque può fare infinite richieste
```bash
# Attaccare server
for i in {1..10000}; do
  curl -X POST http://localhost:5000/soccorso -d '...'
done
```

#### ✅ SOLUZIONE
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/soccorso', methods=['POST'])
@limiter.limit("5 per minute")  # Max 5 richieste/minuto per IP
def crea_richiesta_soccorso():
    # ...

@app.route('/chat', methods=['POST'])
@limiter.limit("10 per minute")
def chat_bot():
    # ...
```

---

### 9. **QUERY MONGODB NON OTTIMIZZATE**

**Severity**: 🟠 MEDIA  
**File**: `API_Automobilista.py:90-100`

#### ❌ PROBLEMA
```python
# Carica TUTTI i documenti in memoria
cursor = mongo_db.Sinistro.find(query).sort("data_richiesta", -1)
risultati = list(cursor)  # ← FULL SCAN se no indici

if not risultati:
    return jsonify({"storico_incidenti": []})

# Problema: con 1M docmenti → crash memoria
```

#### ✅ SOLUZIONE
```python
@app.route('/soccorsi/ricerca', methods=['GET'])
def ricerca_cronologia_soccorsi():
    # Paginazione
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    skip = (page - 1) * per_page
    
    query = build_query(request.args)
    
    # Aggiungi indici per targa (vedi below)
    cursor = (mongo_db.Sinistro
        .find(query)
        .sort("data_richiesta", -1)
        .skip(skip)
        .limit(per_page))
    
    total = mongo_db.Sinistro.count_documents(query)
    
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
        "storico_incidenti": list(cursor)
    }), 200

# Indici MongoDB (da eseguire una volta)
db.Sinistro.createIndex({"targa": 1})
db.Sinistro.createIndex({"data_richiesta": -1})
db.Sinistro.createIndex({"nome": "text", "cognome": "text"})  # Full-text search
```

---

### 10. **MANCANZA DI TESTING**

**Severity**: 🟠 MEDIA  
**File**: Nessun file test

#### ❌ PROBLEMA
Zero test automatici = bug in produzione

#### ✅ SOLUZIONE
```python
# tests/test_automobilista.py
import pytest
from API_Automobilista import app
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_crea_richiesta_soccorso_success(client):
    """Test POST /soccorso con dati validi"""
    response = client.post('/soccorso', json={
        "nome": "Mario",
        "cognome": "Rossi",
        "targa": "AA123BB",
        "lat": "45.4642",
        "lon": "9.19"
    })
    assert response.status_code == 201
    data = json.loads(response.data)
    assert "intervento_id" in data
    assert data["stato"] == "Richiesto"

def test_crea_richiesta_targa_mancante(client):
    """Test POST /soccorso senza targa → 400"""
    response = client.post('/soccorso', json={
        "nome": "Mario",
        "cognome": "Rossi"
    })
    assert response.status_code == 400

def test_get_dettaglio_soccorso_not_found(client):
    """Test GET /soccorso con ID inesistente → 404"""
    response = client.get('/soccorso/INVALID_ID')
    assert response.status_code == 404

def test_coordinate_invalide(client):
    """Test POST con lat/lon non numerici → 400"""
    response = client.post('/soccorso', json={
        "nome": "Mario",
        "cognome": "Rossi",
        "targa": "AA123BB",
        "lat": "not_a_number",
        "lon": "9.19"
    })
    assert response.status_code == 400

# Esegui:
# pip install pytest pytest-cov
# pytest tests/test_automobilista.py -v --cov
```

---

## 🟢 MINOR ISSUES

### 11. **Mancano Docstrings TypeHint**
```python
# ❌ PRIMA
def get_context(self):
    context = ""
    for msg in self.messages[-6:]:
        context += f"{msg['role'].upper()}: {msg['content']}\n"
    return context

# ✅ DOPO
def get_context(self) -> str:
    """Genera contesto conversazione dagli ultimi 6 messaggi.
    
    Returns:
        str: Contesto formattato "ROLE: contenuto" per ogni msg
    """
    context = ""
    for msg in self.messages[-6:]:
        context += f"{msg['role'].upper()}: {msg['content']}\n"
    return context
```

### 12. **Commenti Troppo Verbosi**
```python
# ❌ PRIMA
# Se l'utente ha inserito lettere invece di numeri...
try:
    lat = float(lat_str)
    lon = float(lon_str)
except (TypeError, ValueError):  # Se l'utente ha inserito lettere...
    return ...

# ✅ DOPO
try:
    lat, lon = float(lat_str), float(lon_str)
except (TypeError, ValueError):
    return jsonify({
        "error": "Latitudine e longitudine devono essere numeri validi"
    }), 400
```

### 13. **Magic Strings**
```python
# ❌ PRIMA
if request.user_role == "operatore":
    ...
if obj.stato == "Richiesto":
    ...

# ✅ DOPO
# constants.py
class UserRoles:
    UTENTE = "utente"
    OPERATORE = "operatore"
    ADMIN = "admin"

class SoccorsoStates:
    RICHIESTO = "Richiesto"
    IN_ATTESA = "In attesa"
    COMPLETATO = "Completato"

# Nel codice
if request.user_role == UserRoles.OPERATORE:
    ...
```

---

## ✅ PUNTI POSITIVI

### Cosa è Stato Fatto Bene

1. **Buona Separazione Componenti**
   - API Automobilista separata da ChatBot
   - Logica business ben isolata
   - Config centralizzata

2. **Supporto GeoJSON Corretto**
   - Uso standard [lon, lat] corretto
   - Pronto per query geospaziali

3. **Commenti Esplicativi**
   - Ogni linea complessa ha spiegazione
   - Buono per onboarding

4. **MongoDB + CORS Abilitato**
   - Pronto per frontend diversi
   - Atlas cloud riduce ops

5. **Conversazione Stateful con StorageSystem**
   - Memory strutturata in classe
   - Buona base per persistence

---

## 📋 PIANO DI AZIONE (PRIORITÀ)

### Settimana 1 - CRITICAL
- [ ] Sposta credenziali in `.env` (2 ore)
- [ ] Implementa JWT authentication (4 ore)
- [ ] Aggiungi validazione input con Marshmallow (3 ore)

### Settimana 2 - HIGH
- [ ] Crittografia dati sensibili (3 ore)
- [ ] Setup logging strutturato (2 ore)
- [ ] Rate limiting (1 ora)
- [ ] Error handling specifico (2 ore)

### Settimana 3 - MEDIUM
- [ ] Migra session a Redis (3 ore)
- [ ] Ottimizza query MongoDB (2 ore)
- [ ] Setup testing suite (4 ore)

### Settimana 4 - IMPROVEMENTS
- [ ] Docstrings/TypeHints (3 ore)
- [ ] Monitoring/Logging (2 ore)
- [ ] API versioning (1 ora)

---

## 🎯 CONCLUSIONE

**Verdict**: Codice **FUNZIONANTE ma INSICURO**

Il backend funziona come MVP, ma **NON è pronto per produzione** senza fix di sicurezza critici. Le tre vulnerabilità principali (credenziali hardcoded, nessuna auth, dati non crittati) devono essere risolte PRIMA di qualunque deployment.

**Timeline Consigliato**: 4 settimane per raggiungere security/production-ready standards.

**Responsabili**:
- Security chief: Credenziali + Auth
- DevOps: Infrastructure + Logging
- QA: Testing + Validation

---

**Data Revisione**: Maggio 2024  
**Next Review**: Due settimane dopo implementazione criticità
