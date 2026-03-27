# Piano di Miglioramento — SafeClaim Backend

## TL;DR
Il backend SafeClaim ha una struttura di base funzionante (CRUD sinistri, polizze, veicoli, periti, login/registrazione), ma mancano diverse funzionalità documentate nel file `SafeClaim.md` o comunque necessarie per un sistema realistico. Il piano propone miglioramenti concreti suddivisi per priorità: funzionalità mancanti critiche, miglioramenti di qualità, e funzionalità avanzate.

---

## Fase 1 — Funzionalità mancanti critiche

### 1.1 Autenticazione JWT (non implementata)
- **Stato attuale**: il login restituisce i dati utente ma NON genera alcun token JWT. La documentazione (§7) descrive esplicitamente un flusso stateless con JWT, RBAC e refresh token.
- **Da fare**: implementare generazione di Access Token + Refresh Token al login, middleware di verifica JWT su tutti gli endpoint protetti, e decoratore `@ruolo_richiesto(...)` per RBAC.
- **File coinvolti**: `endpoint_5F_log_reg.py` (login/registrazione), tutti gli altri file per il middleware.

### 1.2 Ricerca e filtri per data / stato sui sinistri
- **Stato attuale**: `GET /sinistri` in `endpoint_5F_Assicurazione.py` restituisce tutti i sinistri senza filtri. La tabella API nella doc (§5) prevede `?stato=aperto` e altri filtri.
- **Da fare**: aggiungere query parameters: `?stato=`, `?data_da=`, `?data_a=`, `?targa=`, `?automobilista_id=` sull'endpoint GET sinistri.
- **File coinvolti**: `endpoint_5F_Assicurazione.py`, `endpoint_5F_Sinistri_User.py`.

### 1.3 Endpoint profilo utente (`GET /users/me`)
- **Stato attuale**: la doc (§5) prevede `GET /api/v1/users/me` per tutti gli attori. Non esiste.
- **Da fare**: creare endpoint che, a partire dal token JWT, restituisce i dati dell'utente autenticato.
- **File coinvolti**: `endpoint_5F_log_reg.py`.

### 1.4 Password hashing (vulnerabilità di sicurezza)
- **Stato attuale**: le password vengono salvate in chiaro nel database MySQL. Il login confronta in chiaro (`WHERE email = %s AND psw = %s`).
- **Da fare**: usare `bcrypt` o `werkzeug.security` per hash delle password alla registrazione e verifica al login.
- **File coinvolti**: `endpoint_5F_log_reg.py`, `db_locale.py` (seed data).

### 1.5 Unificazione della configurazione DB (duplicazione codice)
- **Stato attuale**: ogni file endpoint ripete la stessa configurazione MySQL e MongoDB (credenziali hardcoded, connessione duplicata). Ci sono anche inconsistenze: `get_mysql_connection()` vs `get_db_connection()` vs `get_mysql()`.
- **Da fare**: creare un file `config.py` o `db.py` centralizzato che esporta connessioni e configurazioni. Usare variabili d'ambiente per le credenziali.
- **File coinvolti**: tutti i file endpoint + nuovo file `config.py`.

---

## Fase 2 — Funzionalità previste dalla doc ma non implementate

### 2.1 Upload e gestione documenti/immagini (`POST /api/v1/files`)
- **Stato attuale**: esiste solo `POST /sinistro/ultimo/immagini` che salva immagini in base64 nel campo `immagini` del sinistro MongoDB. Non esiste un vero endpoint di upload file, né gestione tramite Object Storage.
- **Da fare**: creare endpoint `POST /files` per upload sicuro di file (foto, CAI, PDF) con salvataggio su file system o cloud storage e metadati su MySQL (tabella `Documenti_Anagrafica`/`Polizza_Documenti`).
- **File coinvolti**: nuovo file `endpoint_5F_Documenti.py`.

### 2.2 Invio email / notifiche
- **Stato attuale**: nessun sistema di notifica. Non esiste alcun endpoint per inviare comunicazioni all'utente.
- **Da fare**: creare un servizio email (es. con `Flask-Mail` o SMTP diretto) per: conferma registrazione, aggiornamento stato sinistro, assegnazione perito, esito perizia.
- **File coinvolti**: nuovo file `endpoint_5F_Notifiche.py` o `services/email_service.py`.

### 2.3 Endpoint eventi/audit sinistro (`GET /sinistri/{id}/eventi`)
- **Stato attuale**: previsto dalla doc (§5), non implementato. Ogni cambio di stato del sinistro dovrebbe generare un evento tracciabile.
- **Da fare**: creare collezione MongoDB `Evento_Sinistro`, inserire un log ogni volta che lo stato di un sinistro cambia, esporre endpoint GET per lo storico.
- **File coinvolti**: `endpoint_5F_Assicurazione.py`, `endpoint_5F_Periti.py`, `endpoint_5F_Sinistri_User.py`.

### 2.4 Endpoint AI (`POST /ai/analyze`, `GET /documenti-ai/{id}`)
- **Stato attuale**: previsti dalla doc (§5), non implementati.
- **Da fare**: creare almeno uno stub/mock per l'analisi automatica delle immagini e il recupero del risultato. Può essere simulato con logica semplice o chiamata a API esterna.
- **File coinvolti**: nuovo file `endpoint_5F_AI.py`.

### 2.5 Gestione preventivi carrozzeria
- **Stato attuale**: la doc (§5) prevede `POST /preventivi` (Carrozzeria) e `PUT /preventivi/{id}` (Assicurazione). Non esiste.
- **Da fare**: creare endpoint CRUD preventivi, collegati a sinistro e officina.
- **File coinvolti**: nuovo file `endpoint_5F_Preventivi.py` o estensione di `endpoint_5F_Periti.py`.

---

## Fase 3 — Miglioramenti di qualità e robustezza

### 3.1 Unificazione in un'unica applicazione Flask
- **Stato attuale**: ci sono 6 file Flask separati, ognuno con la propria `app = Flask(__name__)` e porta diversa (5000, 6000, 7000, 8000, 9000, 10000). Non possono funzionare come sistema unico.
- **Da fare**: usare Flask Blueprints per registrare tutti gli endpoint su un'unica app Flask che gira su una sola porta. Creare un `app.py` principale.
- **File coinvolti**: tutti i file endpoint → conversione a Blueprint, nuovo `app.py`.

### 3.2 Versioning API (`/api/v1/...`)
- **Stato attuale**: la doc (§5) specifica il prefisso `/api/v1/` per tutti gli endpoint. Nessun endpoint attuale lo usa.
- **Da fare**: aggiungere prefisso `/api/v1` tramite Blueprint o `url_prefix`.
- **File coinvolti**: tutti i file endpoint.

### 3.3 Validazione input consistente
- **Stato attuale**: la validazione è presente solo nella registrazione. Molti endpoint POST non validano i campi obbligatori o i tipi.
- **Da fare**: aggiungere validazione dei campi obbligatori e dei formati su tutti gli endpoint POST/PUT.
- **File coinvolti**: tutti i file endpoint.

### 3.4 Gestione errori strutturata
- **Stato attuale**: la doc (§5.1) definisce un formato di errore standard con `timestamp`, `status`, `error`, `message`, `risorsa`, `path`. Gli endpoint attuali restituiscono errori in formato diverso e inconsistente.
- **Da fare**: creare un error handler centralizzato che restituisce il formato documentato.
- **File coinvolti**: tutti i file endpoint + nuovo handler.

### 3.5 Bug: riferimento a funzione inesistente in `endpoint_5F_Veicoli.py`
- **Stato attuale**: `endpoint_5F_Veicoli.py` chiama `get_mysql_connection()` ma definisce solo `get_db_connection()`. L'endpoint è rotto.
- **Da fare**: correggere il riferimento.
- **File coinvolti**: `endpoint_5F_Veicoli.py`.

### 3.6 Bug: `endpoint_5F_Sinistri_User.py` usa `get_mysql_connection()` nel POST `/veicoli`
- **Stato attuale**: la funzione `add_veicolo()` chiama `get_mysql_connection()` ma la connessione è definita come `get_db_connection()`.
- **Da fare**: correggere il riferimento.
- **File coinvolti**: `endpoint_5F_Sinistri_User.py`.

---

## Fase 4 — Funzionalità avanzate (nice-to-have)

### 4.1 Endpoint geolocalizzazione officine vicine
- **Stato attuale**: la tabella `Officina` ha `latitudine` e `longitudine`, ma non esiste un endpoint per cercare officine vicine a una posizione.
- **Da fare**: creare `GET /officine?lat=...&lon=...&raggio=...` con calcolo distanza.

### 4.2 Registrazione perito / assicuratore
- **Stato attuale**: la registrazione (`POST /registrazione`) crea solo Automobilisti. Non è possibile registrare Periti o Assicuratori via API.
- **Da fare**: estendere o creare endpoint di registrazione per i diversi ruoli.

### 4.3 Swagger / OpenAPI documentation
- **Stato attuale**: la doc (§5) menziona Swagger come tool per la documentazione API. Non implementato.
- **Da fare**: integrare `flask-restx` o `flasgger` per documentazione automatica.

### 4.4 Endpoint DELETE sinistro
- **Stato attuale**: esiste solo creazione e aggiornamento sinistri. Nessun endpoint DELETE (neanche soft-delete).

### 4.5 Paginazione risultati
- **Stato attuale**: `GET /sinistri` e `GET /polizze` restituiscono tutti i risultati senza paginazione.
- **Da fare**: aggiungere `?page=&limit=` su tutti gli endpoint di lista.

---

## Riepilogo file coinvolti

| File | Azioni principali |
|------|-------------------|
| `endpoint_5F_log_reg.py` | JWT, password hashing, endpoint `/users/me`, registrazione multi-ruolo |
| `endpoint_5F_Sinistri_User.py` | Filtri data/stato, fix bug `get_mysql_connection`, audit trail |
| `endpoint_5F_Assicurazione.py` | Filtri sinistri, audit trail, versioning |
| `endpoint_5F_Polizze.py` | Validazione input, versioning, paginazione |
| `endpoint_5F_Periti.py` | Audit trail, validazione, versioning |
| `endpoint_5F_Veicoli.py` | Fix bug `get_mysql_connection`, versioning |
| `db_locale.py` | Aggiornamento seed con password hashate |
| Nuovi file | `config.py`, `app.py`, `endpoint_5F_Documenti.py`, `endpoint_5F_Notifiche.py`, `endpoint_5F_AI.py`, `endpoint_5F_Preventivi.py` |

---

## Verifica

1. **Fase 1**: testare login → verifica che restituisca token JWT; testare accesso endpoint senza token → deve restituire 401; testare filtri `GET /sinistri?stato=APERTO` → deve restituire solo sinistri aperti.
2. **Fase 2**: testare upload file → verifica che i metadati siano salvati in DB; testare invio email mock; testare endpoint audit.
3. **Fase 3**: avviare l'applicazione unificata con `python app.py` su una sola porta; verificare tutti gli endpoint con prefisso `/api/v1/`; verificare formato errori standard.
4. **Fase 4**: testare ricerca officine per coordinate; testare paginazione.

## Decisioni chiave

- Le credenziali DB hardcoded sono un rischio di sicurezza → spostarle in variabili d'ambiente (`.env`).
- Le password in chiaro sono una vulnerabilità critica da risolvere subito (Fase 1).
- L'architettura multi-processo (6 app Flask su 6 porte) non è scalabile → unificare con Blueprint (Fase 3).
