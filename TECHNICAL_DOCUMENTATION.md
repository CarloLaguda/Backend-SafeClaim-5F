# 📖 Documentazione Tecnica SafeClaim Backend

## 📋 Indice
1. [Panoramica del Progetto](#panoramica-del-progetto)
2. [Architettura del Sistema](#architettura-del-sistema)
3. [Componenti e Funzionalità](#componenti-e-funzionalità)
4. [Configurazione e Setup](#configurazione-e-setup)
5. [API Reference Completa](#api-reference-completa)
6. [Modello Dati](#modello-dati)
7. [Flussi di Integrazione](#flussi-di-integrazione)
8. [Deployment e Monitoraggio](#deployment-e-monitoraggio)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Panoramica del Progetto

**SafeClaim** è un sistema di gestione sinistri automobilistici con assistenza IA che fornisce:

- **API REST** per la gestione richieste di soccorso stradale
- **ChatBot Intelligente** con memoria conversazionale
- **Persistenza Dati** su MongoDB e MySQL
- **Sistema Notifiche** via SMTP/Gmail

### Stakeholder Principali
- 🚗 Utenti Automobilisti (ricerca soccorso)
- 👨‍💼 Operatori Assicurativi (gestione sinistri)
- 🤖 Assistente IA (supporto clienti)

---

## 🏗️ Architettura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Web/Mobile)                     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    REST API Gateway                          │
│  (Flask con CORS abilitato)                                 │
└─────────────────────────────────────────────────────────────┘
         ↙                    ↓                      ↘
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │   API SOCCORSO   │    │ API CHATBOT  │    │ NOTIFICHE    │
    │ (porta 5000) │    │ (porta 5001) │    │    (SMTP)    │
    └──────────────┘    └──────────────┘    └──────────────┘
         ↓                    ↓                      ↓
    ┌─────────────────────────────────────────────────────┐
    │              DATABASE LAYER                          │
    │  ┌──────────────────────┐  ┌──────────────────────┐ │
    │  │  MongoDB             │  │  MySQL (opzionale)   │ │
    │  │  - Sinistri          │  │  - Veicoli           │ │
    │  │  - Conversazioni     │  │  - Utenti            │ │
    │  │  - Feedback          │  │  - Storico logs      │ │
    │  └──────────────────────┘  └──────────────────────┘ │
    └─────────────────────────────────────────────────────┘
```

---

## 💡 Componenti e Funzionalità

### 1. **API_Automobilista.py** - Gestione Sinistri Stradali

#### Scopo
Gestisce la creazione e ricerca di richieste di soccorso stradale con supporto geolocalizzazione GeoJSON.

#### Features Principali
- ✅ Creazione nuove richieste soccorso con coordinate GPS
- ✅ Ricerca rapida per ID o targa veicolo
- ✅ Ricerca avanzata con filtri (nome, cognome, targa, descrizione)
- ✅ Supporto standard GeoJSON per mappe
- ✅ Ordinamento automatico per timestamp

#### Endpoints
```
POST   /soccorso                    → Crea richiesta (201)
GET    /soccorso/<id_o_targa>      → Dettagli sinistro (200)
GET    /soccorsi/ricerca            → Ricerca filtrata (200)
```

#### Flusso Dati Esempio
```
Input Utente → Validazione → Conversione lat/lon → GeoJSON → MongoDB
```

---

### 2. **API_ChatBot.py** - Assistente IA Conversazionale

#### Scopo
Fornisce supporto clienti tramite chatbot con memoria conversazionale e integrazione IA.

#### Features Principali
- ✅ Sesioni persistent con UUID univoci
- ✅ Memoria degli ultimi 6 messaggi per contesto
- ✅ Integrazione con IA Hugging Face (Phi-3)
- ✅ Sistema di feedback 1-5 stelle
- ✅ Suggerimenti intelligenti context-aware
- ✅ Salvataggio automatico in MongoDB

#### Endpoints
```
POST   /chat/init                   → Crea sessione (200)
POST   /chat                        → Invia messaggio (200)
POST   /chat/feedback               → Registra feedback (200)
GET    /chat/history/<session_id>   → Storico sessione (200)
POST   /chat/end/<session_id>       → Termina e salva (200)
```

#### Flusso Conversazione
```
1. Client chiama /chat/init → session_id generato
2. Client chiama /chat con sessione_id e messaggio
3. Bot recupera contesto (ultimi 6 messaggi)
4. IA Hugging Face processa prompt e genera risposta
5. Risposta salvata + suggerimenti generati
6. Client valuta con /chat/feedback
7. Chiama /chat/end per salvataggio finale
```

---

### 3. **DB_Creation.py** - Setup e Integrazione Sistema

#### Scopo
Script di test, configurazione e integrazione per database e notifiche email.

#### Funzionalità
- 🔍 Test connessione MySQL
- 🔍 Test connessione MongoDB
- 📧 Test invio email SMTP via Gmail
- 📋 Validazione configurazioni

---

## ⚙️ Configurazione e Setup

### Prerequisiti
```bash
- Python 3.8+
- pip (gestore pacchetti Python)
- Connessione Internet
- Account MongoDB Atlas (gratuito)
- Account Gmail con "Password per le app"
```

### Installazione Dipendenze
```bash
pip install flask flask-cors pymongo requests git+https://github.com/your-org/safeclaim-utils
```

### File di Configurazione Critici

#### MongoDB Connection String (Comune)
```python
# In API_Automobilista.py (linea 9)
CONNECTION_STRING = "mongodb+srv://user:pass@cluster.mongodb.net/?appName=Cluster0"

# In API_ChatBot.py (linea 20)
MONGO_URI = "mongodb://user:pass@host:27017/"
```

**⚠️ ATTENZIONE SICUREZZA**: Queste stringhe contengono credenziali
- ✅ SEMPRE usare variabili d'ambiente: `os.getenv("MONGO_CONNECTION")`
- ✅ MAI committare credenziali in Git
- ✅ Usare `.env` con dotenv

#### Email Configuration
```python
# Richiede "Password per le app" da Gmail, NON la password dell'account
EMAIL_CONFIG = {
    "sender": "your-email@gmail.com",
    "password": "16-character-app-password",  # SENZA SPAZI
    "smtp_server": "smtp.gmail.com",
    "port": 465
}
```

**Genera password app Gmail**:
1. Accedi a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Seleziona Mail e Windows
3. Copia la password (16 caratteri)
4. Incolla SENZA SPAZI nel config

### Avvio Servizi

#### Terminal 1 - API Automobilista (porta 5000)
```bash
python API_Automobilista.py
# Output: ✅ Connessione a MongoDB Atlas riuscita!
#         * Running on http://0.0.0.0:5000
```

#### Terminal 2 - API ChatBot (porta 5001)
```bash
python API_ChatBot.py
# Output: ✅ MongoDB: Connesso
#         🚀 Server avviato sulla porta 5001
```

---

## 📡 API Reference Completa

### 1️⃣ SOCCORSO API

#### POST /soccorso - Crea Richiesta
```http
POST http://localhost:5000/soccorso
Content-Type: application/json

{
  "nome": "Mario",
  "cognome": "Rossi",
  "targa": "AA123BB",
  "lat": "45.4642",
  "lon": "9.19",
  "descrizione": "Batteria scarica, serve booster"
}
```

**Risposta Success (201)**
```json
{
  "message": "Soccorso registrato con successo",
  "intervento_id": "65f8a1b2c3d4e5f6a7b8c9d0",
  "database_utilizzato": "FakeClaim",
  "stato": "Richiesto"
}
```

**Errori Comuni**
| Errore | Causa | Soluzione |
|--------|-------|-----------|
| 400 Bad Request | Targa mancante | Includi `"targa"` obbligatoria |
| 400 Bad Request | Lat/Lon non numerici | Usa stringhe numeriche: `"45.4"` |
| 500 Server Error | MongoDB non raggiungibile | Controlla CONNECTION_STRING |
| 500 Server Error | Timeout connessione | Aumenta serverSelectionTimeoutMS |

---

#### GET /soccorso/{id_o_targa} - Dettagli Sinistro
```http
GET http://localhost:5000/soccorso/AA123BB
```

**Risposta Success (200)**
```json
{
  "soccorso_info": {
    "_id": "65f8a1b2c3d4e5f6a7b8c9d0",
    "nome": "Mario",
    "cognome": "Rossi",
    "targa": "AA123BB",
    "posizione": {
      "type": "Point",
      "coordinates": [9.19, 45.4642]
    },
    "stato": "Richiesto",
    "dettagli": "Batteria scarica",
    "data_richiesta": "2024-05-21T10:30:00.000Z"
  }
}
```

---

#### GET /soccorsi/ricerca - Ricerca Filtrata
```http
GET http://localhost:5000/soccorsi/ricerca?targa=AA123&cognome=Rossi
```

**Query Parameters**
| Parametro | Tipo | Obbligatorio | Note |
|-----------|------|--------------|------|
| nome | string | No | Case-insensitive regex |
| cognome | string | No | Case-insensitive regex |
| targa | string | No | Case-insensitive regex |
| descrizione | string | No | Cerca nei dettagli |

**Risposta Success (200)**
```json
{
  "message": "Trovati 2 interventi",
  "storico_incidenti": [
    { "_id": "...", "targa": "AA123BB", ... },
    { "_id": "...", "targa": "AA123BB", ... }
  ]
}
```

---

### 2️⃣ CHATBOT API

#### POST /chat/init - Inizializza Sessione
```http
POST http://localhost:5001/chat/init
```

**Risposta (200)**
```json
{
  "status": "success",
  "session_id": "a3b2c1d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p"
}
```

---

#### POST /chat - Invia Messaggio
```http
POST http://localhost:5001/chat
Content-Type: application/json

{
  "session_id": "a3b2c1d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p",
  "messaggio": "Come faccio un reclamo?"
}
```

**Risposta (200)**
```json
{
  "session_id": "a3b2c1d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p",
  "risposta": "Per fare un reclamo deve contattare...",
  "suggerimenti": [
    "Puoi spiegare meglio?",
    "Quali sono i prossimi step?",
    "Come contatto l'assistenza?"
  ]
}
```

---

#### POST /chat/feedback - Registra Valutazione
```http
POST http://localhost:5001/chat/feedback
Content-Type: application/json

{
  "session_id": "a3b2c1d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p",
  "rating": 4,
  "comment": "Risposta utile ma incompleta"
}
```

---

#### GET /chat/history/{session_id} - Storico Sessione
```http
GET http://localhost:5001/chat/history/a3b2c1d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p
```

**Risposta (200)**
```json
{
  "session_id": "...",
  "messages": [
    {
      "role": "user",
      "content": "Come faccio un reclamo?",
      "timestamp": "2024-05-21T10:30:00"
    },
    {
      "role": "assistant",
      "content": "Per fare un reclamo...",
      "timestamp": "2024-05-21T10:30:05"
    }
  ],
  "created_at": "2024-05-21T10:25:00",
  "feedback": [
    {"rating": 4, "comment": "...", "timestamp": "..."}
  ]
}
```

---

## 🗄️ Modello Dati

### MongoDB Collections

#### Collezione: `Sinistro` (API_Automobilista)
```javascript
{
  "_id": ObjectId("65f8a1b2c3d4e5f6a7b8c9d0"),  // ID univoco MongoDB
  "nome": "Mario",                               // Nome richiedente
  "cognome": "Rossi",                            // Cognome richiedente
  "targa": "AA123BB",                            // Targa veicolo (unica)
  "posizione": {                                 // Standard GeoJSON
    "type": "Point",
    "coordinates": [9.19, 45.4642]              // [longitude, latitude]
  },
  "stato": "Richiesto",                         // Valori: "Richiesto", "In attesa", "Completato"
  "dettagli": "Batteria scarica, serve booster",
  "data_richiesta": ISODate("2024-05-21T10:30:00.000Z")
}
```

**Indici Consigliati**
```javascript
db.Sinistro.createIndex({ "targa": 1 })
db.Sinistro.createIndex({ "data_richiesta": -1 })
db.Sinistro.createIndex({ "posizione": "2dsphere" })  // Per query geospaziali
```

#### Collezione: `conversations` (API_ChatBot)
```javascript
{
  "session_id": "a3b2c1d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p",
  "messages": [
    {
      "role": "user|assistant",
      "content": "Testo messaggio",
      "timestamp": "2024-05-21T10:30:00.000"
    }
  ],
  "created_at": "2024-05-21T10:25:00.000",
  "feedback": [
    {
      "rating": 1-5,
      "comment": "Feedback opzionale",
      "timestamp": "2024-05-21T10:35:00.000"
    }
  ]
}
```

---

## 🔄 Flussi di Integrazione

### Flusso 1: Richiesta Soccorso Completa

```
1. Utente apre app mobile/web SafeClaim
2. App acquisisce coordinate GPS attuali
3. Utente compila form (nome, cognome, targa, descrizione)
4. App invia POST /soccorso con dati + GPS

   → API_Automobilista.py riceve richiesta
   → Valida targa obbligatoria
   → Converte lat/lon da stringhe a float
   → Crea documento GeoJSON
   → Inserisce in MongoDB.Sinistro
   → Restituisce intervento_id

5. Frontend mostra ID confermato all'utente
6. (Opzionale) Invia notifica email via SMTP
7. Operatore ricerca su /soccorsi/ricerca?targa=...
8. Dashboard mostra sinistri in tempo reale
9. Assegna intervento a soccorritore
10. Soccorritore aggiorna stato ("Completato")
```

### Flusso 2: Conversazione ChatBot

```
1. Utente clicca "Chat con IA"
2. Frontend chiama POST /chat/init
   → API genera session_id UUID
   → Crea ConversationSession in memoria
   → Restituisce session_id

3. Utente digita primo messaggio
4. Frontend chiama POST /chat con session_id + testo

   → API_ChatBot.py riceve messaggio
   → Carica ultimi 6 messaggi come contesto
   → Prepara prompt per API Hugging Face
   → Chiama IA Phi-3 per generazione risposta
   → IA ritorna risposta generata
   → Bot genera 3 suggerimenti context-aware
   → Salva tutto in memoria + MongoDB
   → Restituisce risposta + suggerimenti

5. Se utente clicca suggerimento, va al passo 4
6. Utente clicca stella di valutazione
7. Frontend chiama POST /chat/feedback con rating

8. Quando chiude chat:
   → Frontend chiama POST /chat/end/<session_id>
   → API salva intera sessione in MongoDB
   → Cancella dalla memoria (active_sessions)
```

### Flusso 3: Integrazione Email Notifiche

```
File: DB_Creation.py

1. Evento trigger (es. nuovo sinistro creato)
2. Backend chiama invia_email(destinatario, oggetto, corpo)

   → Crea messaggio MIME multipart
   → Connette a smtp.gmail.com:465 con SSL
   → Autenticazione con email + app-password
   → Invia email fisico

   → Se successo: print("📧 Email inviata...")
   → Se errore: print("❌ Errore invio...")
```

---

## 🚀 Deployment e Monitoraggio

### Prerequisiti Deployment
- ✅ Server Linux/macOS con Python 3.8+
- ✅ Firewall aperto su porte 5000, 5001
- ✅ MongoDB Atlas account (cloud)
- ✅ Credenziali Gmail app-password
- ✅ Dominio SSL per HTTPS (importante)

### Deploy su Server Produzione

#### Opzione 1: Systema Service (Linux)
```bash
# 1. Crea file servizio
sudo nano /etc/systemd/system/safeclaim.service

[Unit]
Description=SafeClaim Backend Services
After=network.target

[Service]
Type=forking
User=safeclaim
WorkingDirectory=/opt/safeclaim
Environment="PATH=/opt/safeclaim/venv/bin"

ExecStart=/opt/safeclaim/venv/bin/python /opt/safeclaim/API_Automobilista.py
ExecStart=/opt/safeclaim/venv/bin/python /opt/safeclaim/API_ChatBot.py

[Install]
WantedBy=multi-user.target

# 2. Abilita e avvia
sudo systemctl enable safeclaim
sudo systemctl start safeclaim
sudo systemctl status safeclaim
```

#### Opzione 2: Docker (Consigliato)
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000 5001

CMD ["python", "API_Automobilista.py"] && \
    ["python", "API_ChatBot.py"]
```

```bash
docker build -t safeclaim-backend .
docker run -p 5000:5000 -p 5001:5001 safeclaim-backend
```

### Monitoraggio e Logging

#### Log Locations
```
API Soccorsi:  /var/log/safeclaim/api_automobilista.log
API ChatBot:   /var/log/safeclaim/api_chatbot.log
MongoDB:       Monitor da MongoDB Atlas Dashboard
```

#### Metriche da Monitorare
- 📊 Numero richieste /soccorso (volume)
- ⏱️ Tempo risposta medio (latenza)
- 🔴 Errori 5xx (problemi server)
- 🟡 Errori 4xx (problemi input)
- 💬 Sessioni ChatBot attive
- 🗄️ Dimensione database MongoDB
- 📧 Email inviate/fallite

#### Health Check Endpoint (Da aggiungere)
```python
@app.route('/health', methods=['GET'])
def health_check():
    try:
        mongo_client.admin.command('ping')
        return jsonify({"status": "healthy", "timestamp": datetime.utcnow()}), 200
    except:
        return jsonify({"status": "unhealthy"}), 503
```

---

## 🔧 Troubleshooting

### ❌ Problema: MongoDB Connection Timeout

**Sintomi**: `serverSelectionTimeoutMS exceeded`

**Soluzioni**
```python
# 1. Aumenta timeout in API_Automobilista.py linea 12
mongo_client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=10000)

# 2. Verifica IP whitelist MongoDB Atlas
#    → mongodb.com → Network Access → Add IP Address

# 3. Verifica credenziali connectionString completa
#    mongodb+srv://user:password@cluster.mongodb.net/

# 4. Test connessione con mongo shell
python -c "import pymongo; c = pymongo.MongoClient('...'); c.admin.command('ping')"
```

---

### ❌ Problema: Email Non Viene Spedita

**Sintomi**: `Error 535` o messaggio non arriva

**Soluzioni**
```python
# 1. Verifica password app Gmail (16 caratteri SENZA SPAZI)
#    Scarica da: myaccount.google.com/apppasswords

# 2. Abilita accesso meno sicuro (sconsigliato)
#    myaccount.google.com → Security → Less secure access → ON

# 3. Test connessione SMTP
python -c "
import smtplib
server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login('your-email@gmail.com', 'app-password')
print('✅ SMTP OK')
"

# 4. Verifica porta 465 non bloccata da firewall
telnet smtp.gmail.com 465
```

---

### ❌ Problema: Coordinate GPS Errate

**Sintomi**: Mappa mostra posizione sbagliata

**Soluzioni**
```python
# Ricordi standard GeoJSON: [longitude, latitude] NON [latitude, longitude]

# ❌ SBAGLIATO
"coordinates": [45.4642, 9.19]  # Questo è [lat, lon]

# ✅ CORRETTO
"coordinates": [9.19, 45.4642]  # Questo è [lon, lat]

# Test rapido
import json
data = {
    "type": "Point",
    "coordinates": [9.19, 45.4642]  # Milano
}
print(json.dumps(data, indent=2))
```

---

### ❌ Problema: ChatBot Non Generà Risposte

**Sintomi**: POST /chat restituisce errore, risposta vuota

**Soluzioni**
```python
# 1. Verifica token Hugging Face API
#    Controlla API_URL: "https://api-inference.huggingface.co/models/..."
#    Genera token da huggingface.co/settings/tokens

# 2. Verifica modello disponibile
#    curl "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct" \
#    -H "Authorization: Bearer YOUR_TOKEN"

# 3. Aumenta timeout richiesta AI
requests.post(url, json=payload, timeout=30)  # Aumenta da 5 a 30 secondi
```

---

## 📚 Risorse Utili

### Link Importanti
- 🔗 [MongoDB Documentation](https://docs.mongodb.com/)
- 🔗 [Flask Documentation](https://flask.palletsprojects.com/)
- 🔗 [Hugging Face Models](https://huggingface.co/models)
- 🔗 [GeoJSON Spec](https://geojson.org/)
- 🔗 [Gmail App Passwords](https://myaccount.google.com/apppasswords)

### Tools Raccomandati
- **Postman**: GUI per testare API
- **MongoDB Compass**: Client desktop per MongoDB
- **VS Code**: Editor con Python extension
- **git**: Versionamento codice

---

**Ultima Aggiornamento**: Maggio 2024
**Version**: 2.0
**Responsabile**: Team SafeClaim Backend
