## Struttura del progetto

Backend-SafeClaim-5F/
│
├── avvia_tutti.sh                  # Script per avviare tutti gli endpoint insieme
├── db_locale.py                    # Script per creare il DB MySQL e popolare i dati iniziali
│
├── endpoint_5F_Assicurazione.py    # Porta 5000 – Sinistri (MongoDB) e Veicoli utente
├── endpoint_5F_log_reg.py          # Porta 6000 – Registrazione e Login
├── endpoint_5F_Sinistri_User.py    # Porta 7000 – Apertura sinistri, soccorso, veicoli
├── endpoint_5F_Periti.py           # Porta 8000 – Perizie, rimborsi, interventi officina
├── endpoint_5F_Polizze.py          # Porta 9000 – CRUD Polizze
├── endpoint_5F_Veicoli.py          # Porta 10000 – Lettura veicoli
├── endpoint_5F_Mail.py             # Porta 11000 – Invio email via SMTP
├── endpoint_5F_RAG_Assistente.py   # Porta 11000 – Chatbot con RAG
├── logs/                           # Cartella creata automaticamente con i log di ogni endpoint
└── .devcontainer/
    └── devcontainer.json           # Configurazione Codespaces (porte pubbliche automatiche)

## Endpoint e porte

| File | Porta | Funzione principale |
|---|---|---|
| `endpoint_5F_log_reg.py` | 6000 | Registrazione e login automobilisti/periti/assicuratori |
| `endpoint_5F_Assicurazione.py` | 5000 | Gestione sinistri su MongoDB, veicoli per utente |
| `endpoint_5F_Sinistri_User.py` | 7000 | Apertura sinistri, aggiunta immagini, richiesta soccorso |
| `endpoint_5F_Periti.py` | 8000 | Creazione perizie, rimborsi, assegnazione officina |
| `endpoint_5F_Polizze.py` | 9000 | Creazione, lettura, modifica, eliminazione polizze |
| `endpoint_5F_Veicoli.py` | 10000 | Lettura veicoli (tutti o per ID) |
| `endpoint_5F_Mail.py` | 11000 | Invio email tramite Gmail SMTP |
| `endpoint_5F_RAG_Assistente.py` | 12000 | Chatbot con RAG |

## Avvio rapido

bash avvia_tutti.sh

Lo script fa in automatico:
- Installa tutte le dipendenze Python necessarie
- Termina eventuali processi già in esecuzione sulle stesse porte
- Avvia ogni endpoint Flask in background
- Salva i log di ogni endpoint nella cartella `logs/`
- Su GitHub Codespaces, imposta le porte come **pubbliche** automaticamente

Per fermare tutto: `CTRL + C`


## Risoluzione errori comuni

pip install flask flask-cors mysql-connector-python "pymongo[srv]" dnspython requests

pip3 install flask flask-cors mysql-connector-python "pymongo[srv]" dnspython requests --break-system-packages

fuser -k 6000/tcp
fuser -k 5000/tcp 6000/tcp 7000/tcp 8000/tcp 9000/tcp 10000/tcp 11000/tcp

sudo service mariadb start

sudo service mariadb status

cat logs/endpoint_5F_Periti.log

tail -f logs/*.log

gh codespace ports visibility 5000:public 6000:public 7000:public 8000:public 9000:public 10000:public 11000:public
