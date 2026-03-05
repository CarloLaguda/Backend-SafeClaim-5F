# Backend-SafeClaim-5F

## 🤖 ChatBot Avanzato - Assistente IA per Sinistri Automobilistici

### ✨ Nuove Funzionalità

Il chatbot è stato migliorato con un sistema intelligente di supporto all'utente:

#### 1️⃣ **Memoria della Conversazione**
- Il bot mantiene lo storico completo di tutti i messaggi durante la sessione
- Considere i 6 ultimi messaggi per mantenere il contesto rilevante
- L'IA che comprende cosa è stato detto prima e risponde coerentemente

#### 2️⃣ **Suggerimenti Intelligenti**
- Dopo ogni risposta, il bot propone domande pertinenti
- I suggerimenti cambiano in base al contesto della conversazione
- L'utente può cliccare su un suggerimento per inviarlo direttamente

#### 3️⃣ **Sistema di Feedback**
- L'utente può valutare ogni risposta (1-5 stelle)
- Possibilità di aggiungere commenti
- I feedback vengono salvati con la conversazione per analisi future

#### 4️⃣ **Persistenza Permanente**
- Tutte le conversazioni vengono salvate automaticamente in MongoDB
- Ogni sessione include: messaggi, timestamp, feedback, durata
- Possibilità di recuperare lo storico delle conversazioni completate

---

## 🚀 Avvio Rapido

### 1. Installa le dipendenze
```bash
pip install flask flask-cors requests pymongo
```

### 2. Avvia il server
```bash
python API_ChatBot.py
```

Output atteso:
```
============================================================
🤖 Chatbot SafeClaim - Versione Avanzata
============================================================
✅ Funzionalità:
   - Gestione conversazione con storico
   - Suggerimenti intelligenti
   - Sistema di feedback
   - Salvataggio persistente in MongoDB
============================================================
🚀 Server avviato sulla porta 5001
============================================================
```

---

## 📚 Endpoint API

### Flusso di Utilizzo Consigliato

```
1️⃣ POST /chat/init          →  Crea una nuova sessione
2️⃣ POST /chat               →  Invia messaggi (ripetibile)
3️⃣ POST /chat/feedback      →  Valuta la risposta
4️⃣ GET  /chat/history/:id   →  Visualizza storico
5️⃣ POST /chat/end/:id       →  Termina e salva
```

### Esempi di Utilizzo

#### Inizializzare una sessione
```bash
curl -X POST http://localhost:5001/chat/init
```

**Risposta:**
```json
{
  "status": "success",
  "session_id": "a3b2c1d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p",
  "message": "Sessione di chat inizializzata"
}
```

#### Inviare un messaggio
```bash
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "a3b2c1d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p",
    "messaggio": "Come faccio un reclamo?"
  }'
```

**Risposta:**
```json
{
  "status": "success",
  "session_id": "a3b2c1d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p",
  "risposta": "Per facciano un reclamo...",
  "suggerimenti": [
    "Quali documenti mi servono?",
    "Quanto tempo ci vuole?",
    "Come contatto l'assistenza?"
  ],
  "numero_messaggi": 2
}
```

#### Inviare feedback
```bash
curl -X POST http://localhost:5001/chat/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "a3b2c1d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p",
    "rating": 5,
    "comment": "Molto utile!"
  }'
```

#### Terminare la sessione (salva in MongoDB)
```bash
curl -X POST http://localhost:5001/chat/end/a3b2c1d4-e5f6-4g7h-8i9j-0k1l2m3n4o5p
```

---

## 🧪 Test Automatici

Esegui la suite di test completa:

```bash
python test_chatbot.py
```

Questo verifica:
- ✅ Inizializzazione della sessione
- ✅ Invio di messaggi
- ✅ Memoria del contesto
- ✅ Suggerimenti
- ✅ Feedback
- ✅ Storico
- ✅ Salvataggio in MongoDB

---

## 🌐 Demo Interattiva

Apri il file `chatbot_demo.html` nel browser per testare l'interfaccia:

```bash
# Viene automaticamente servito se hai un server web
# Altrimenti copia il percorso nel tuo browser: file:///path/to/chatbot_demo.html
```

**Caratteristiche della demo:**
- Chat interattiva in tempo reale
- Visualizzazione grafica dei messaggi
- Sistema di rating con stelle
- Suggerimenti cliccabili

---

## 📖 Documentazione Completa

Per la documentazione dettagliata degli endpoint, vedi: [CHATBOT_ENDPOINTS.md](CHATBOT_ENDPOINTS.md)

Argomenti coperti:
- Endpoint dettagliati
- Codici di risposta HTTP
- Funzionalità avanzate
- Best practices
- Troubleshooting

---

## 🗂️ Struttura File

```
Backend-SafeClaim-5F/
├── API_ChatBot.py                 # 🤖 Server principale (AGGIORNATO)
├── CHATBOT_ENDPOINTS.md            # 📚 Documentazione endpoint
├── chatbot_demo.html               # 🌐 Interfaccia di test
├── test_chatbot.py                 # 🧪 Suite di test
├── API_Automobilista.py            # Auto API
├── DB_Creation.py                  # Configurazione database
├── TestEmail.py                    # Test email
├── RegoleSinistriChatBot.txt       # Regole AI (caricato dal bot)
├── db_mock.json                    # Dati mock
└── README.md                       # Questo file
```

---

## 🔧 Configurazione

### Variabili d'Ambiente Necessarie

Nel file `API_ChatBot.py`:
- `HF_TOKEN`: Token Hugging Face per l'accesso al modello Phi-3
- `MONGO_URI`: Connessione a MongoDB
- Porta: 5001 (modificabile)

### File Richiesti

- `RegoleSinistriChatBot.txt`: Contiene le informazioni nel quale il bot basa le risposte

---

## 💡 Suggerimenti di Utilizzo

### Per sviluppatori
1. Integra gli endpoint nel tuo frontend
2. Usa `session_id` per mantenere le conversazioni separate
3. Salva `session_id` nel localStorage per riprendere le conversazioni

### Per il supporto clienti
1. Ogni sessione è indipendente
2. I feedback aiutano a migliorare il sistema
3. Consulta le conversazioni salvate in MongoDB per analisi

### Per il machine learning
1. Analizza i feedback per migliorare le risposte
2. Usa i suggerimenti non cliccati per capire cosa è utile
3. Monitora i tempi di risposta media per ottimizzazioni

---

## ⚠️ Limitazioni Conosciute

- Timeout 30 secondi per le risposte AI (Hugging Face)
- Massimo 6 messaggi precedenti mantenuti in memoria (per token limit)
- MongoDB è opzionale (chat funziona anche offline, ma senza persistenza)

---

## 🎯 Roadmap Futura

- [ ] Integrazione con more modelli AI
- [ ] Multilanguage support
- [ ] Analytics dashboard
- [ ] Cache risposta frequenti
- [ ] WebSocket per chat real-time
- [ ] Integrazione CRM

---

## 📧 Supporto

Per questions o issue, contatta il team SafeClaim.

**Data ultimo aggiornamento:** Marzo 2026
**Versione:** 2.0 (Avanzata con memoria e feedback)

