#!/bin/bash

# ============================================================
#  SafeClaim – Avvio automatico di tutti gli endpoint Flask
# ============================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

echo -e "${YELLOW}=============================="
echo -e " SafeClaim – Avvio endpoint"
echo -e "==============================${NC}"

# --- MARIADB: INSTALLAZIONE E AVVIO ---
echo -e "\n${CYAN}[1/4] Controllo MariaDB...${NC}"

if ! command -v mariadb &>/dev/null; then
    echo -e "${YELLOW}    MariaDB non trovata – installo...${NC}"
    sudo apt-get update -qq --allow-insecure-repositories 2>/dev/null || true
    sudo apt-get install -y mariadb-server -qq 2>/dev/null
fi

if command -v mariadb &>/dev/null; then
    sudo service mariadb start 2>/dev/null
    sleep 2
    echo -e "${GREEN}[✓] MariaDB in esecuzione${NC}"

    sudo mariadb -e "CREATE USER IF NOT EXISTS 'pythonuser'@'localhost' IDENTIFIED BY 'password123';" 2>/dev/null
    sudo mariadb -e "GRANT ALL PRIVILEGES ON *.* TO 'pythonuser'@'localhost' WITH GRANT OPTION;" 2>/dev/null
    sudo mariadb -e "FLUSH PRIVILEGES;" 2>/dev/null

    DB_CHECK_PENDING=true
else
    echo -e "${RED}[✗] Impossibile installare MariaDB – gli endpoint MySQL non funzioneranno${NC}"
    DB_CHECK_PENDING=false
fi

# --- INSTALLAZIONE DIPENDENZE PYTHON ---
echo -e "\n${CYAN}[2/4] Installo le dipendenze Python...${NC}"

# Pacchetti necessari (aggiornati con cloudinary e gradio_client per Storage.py)
PACKAGES=(
    "flask"
    "flask-cors"
    "mysql-connector-python"
    "pymongo[srv]"
    "dnspython"
    "requests"
    "cloudinary"           # Storage immagini sinistri (Storage.py)
    "google-generativeai"  # Gemini Vision (analisi immagini) + RAG assistente
    "scikit-learn"         # TF-IDF per la RAG
)

# Tenta installazione con --break-system-packages (per ambienti di sistema), poi senza
pip install "${PACKAGES[@]}" --quiet --break-system-packages 2>/dev/null \
    || pip install "${PACKAGES[@]}" --quiet 2>/dev/null

# Verifica che i moduli critici siano importabili
MISSING_MODULES=()
for mod in flask pymongo cloudinary google.generativeai sklearn; do
    if ! python3 -c "import $mod" 2>/dev/null; then
        MISSING_MODULES+=("$mod")
    fi
done

if [ ${#MISSING_MODULES[@]} -eq 0 ]; then
    echo -e "${GREEN}[✓] Tutte le dipendenze installate correttamente${NC}"
else
    echo -e "${RED}[✗] Moduli ancora mancanti: ${MISSING_MODULES[*]}${NC}"
    echo -e "${YELLOW}    Provo installazione singola dei moduli mancanti...${NC}"
    for mod in "${MISSING_MODULES[@]}"; do
        pip install "$mod" --quiet --break-system-packages 2>/dev/null \
            || pip install "$mod" --quiet 2>/dev/null \
            && echo -e "${GREEN}    [✓] $mod installato${NC}" \
            || echo -e "${RED}    [✗] $mod – installazione fallita${NC}"
    done
fi

# --- CREAZIONE DATABASE (dopo le dipendenze Python) ---
if [ "$DB_CHECK_PENDING" = true ]; then
    DB_EXISTS=$(sudo mariadb -u pythonuser -ppassword123 -e "SHOW DATABASES LIKE 'gestione_assicurazioni';" 2>/dev/null | grep -c "gestione_assicurazioni")
    if [ "$DB_EXISTS" -eq 0 ]; then
        echo -e "${YELLOW}    Prima installazione: creo il database...${NC}"
        python3 db_locale.py && echo -e "${GREEN}[✓] Database creato con successo${NC}" \
                             || echo -e "${RED}[✗] Errore creazione database – controlla db_locale.py${NC}"
    else
        echo -e "${GREEN}[✓] Database già esistente – salto la creazione${NC}"
    fi
fi

# --- CONTROLLO FILE NECESSARI ---
echo -e "\n${CYAN}[3/4] Controllo file necessari...${NC}"

# Storage.py è importato da endpoint_5F_Sinistri_User.py – deve essere presente
if [ ! -f "Storage.py" ]; then
    echo -e "${RED}[✗] Storage.py non trovato – endpoint_5F_Sinistri_User.py non potrà avviarsi${NC}"
else
    echo -e "${GREEN}[✓] Storage.py presente${NC}"
fi

# db_locale.py deve essere presente per la creazione del database
if [ ! -f "db_locale.py" ]; then
    echo -e "${RED}[✗] db_locale.py non trovato – il database non verrà inizializzato${NC}"
else
    echo -e "${GREEN}[✓] db_locale.py presente${NC}"
fi

# Verifica presenza endpoint RAG
if [ ! -f "endpoint_5F_RAG_Assistente.py" ]; then
    echo -e "${RED}[✗] endpoint_5F_RAG_Assistente.py non trovato${NC}"
else
    echo -e "${GREEN}[✓] endpoint_5F_RAG_Assistente.py presente${NC}"
fi

# --- CHIUDI PROCESSI PRECEDENTI ---
echo -e "\n${CYAN}[4/4] Avvio endpoint Flask...${NC}"
echo -e "${YELLOW}    Chiudo eventuali processi precedenti sulle porte...${NC}"
for port in 5000 6000 7000 8000 9000 10000 11000 12000; do
    fuser -k "${port}/tcp" 2>/dev/null
done
sleep 1

# --- MAPPA FILE → PORTA ---
declare -A ENDPOINTS=(
    ["endpoint_5F_Assicurazione.py"]=5000
    ["endpoint_5F_log_reg.py"]=6000
    ["endpoint_5F_Sinistri_User.py"]=7000
    ["endpoint_5F_Periti.py"]=8000
    ["endpoint_5F_Polizze.py"]=9000
    ["endpoint_5F_Veicoli.py"]=10000
    ["endpoint_5F_Mail.py"]=11000
    ["endpoint_5F_RAG_Assistente.py"]=12000
)

# --- AVVIO ENDPOINT ---
STARTED=0
FAILED=0

for file in "${!ENDPOINTS[@]}"; do
    port="${ENDPOINTS[$file]}"
    log="$LOG_DIR/${file%.py}.log"

    if [ ! -f "$file" ]; then
        echo -e "${RED}[✗] $file non trovato – salto${NC}"
        (( FAILED++ ))
        continue
    fi

    python3 "$file" > "$log" 2>&1 &
    PID=$!
    sleep 1.5  # Attesa per endpoint con import pesanti (google-generativeai, scikit-learn)

    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${GREEN}[✓] $file  →  porta $port  (PID $PID)${NC}"
        (( STARTED++ ))
    else
        echo -e "${RED}[✗] $file  →  avvio fallito (porta $port)${NC}"
        echo -e "${YELLOW}    Ultime righe del log:${NC}"
        tail -n 5 "$log" | sed 's/^/    /'
        (( FAILED++ ))
    fi
done

# --- PORTE PUBBLICHE SU CODESPACES ---
if command -v gh &>/dev/null && [ -n "$CODESPACE_NAME" ]; then
    echo -e "\n${YELLOW}[*] Imposto le porte come pubbliche su Codespaces...${NC}"
    for port in 5000 6000 7000 8000 9000 10000 11000 12000; do
        gh codespace ports visibility "${port}:public" --codespace "$CODESPACE_NAME" 2>/dev/null \
            && echo -e "${GREEN}    porta $port → pubblica${NC}" \
            || echo -e "${YELLOW}    porta $port → imposta manualmente dal pannello Ports${NC}"
    done
fi

# --- RIEPILOGO FINALE ---
echo -e "\n${GREEN}=============================="
echo -e " Riepilogo avvio SafeClaim"
echo -e "=============================="
echo -e " Avviati con successo : ${STARTED}"
echo -e " Falliti              : ${FAILED}"
echo -e " Log nella cartella   : ${LOG_DIR}/"
echo -e "==============================${NC}"

if [ "$STARTED" -gt 0 ]; then
    echo -e "\n${CYAN}Endpoint attivi:${NC}"
    echo -e "  5000  → Assicurazione (sinistri MongoDB + veicoli)"
    echo -e "  6000  → Login / Registrazione"
    echo -e "  7000  → Sinistri Utente (upload immagini + Gemini Vision)"
    echo -e "  8000  → Periti (perizie, rimborsi, officine)"
    echo -e "  9000  → Polizze (CRUD)"
    echo -e "  10000 → Veicoli"
    echo -e "  11000 → Mail (SMTP Gmail)"
    echo -e "  12000 → RAG Assistente Automobilista (SafeBot)"
fi

echo -e "\n${YELLOW}[Premi CTRL+C per fermare tutto]\n${NC}"

# --- GESTIONE USCITA ---
trap 'echo -e "\n${RED}Arresto in corso...${NC}"; \
      fuser -k 5000/tcp 6000/tcp 7000/tcp 8000/tcp 9000/tcp 10000/tcp 11000/tcp 12000/tcp 2>/dev/null; \
      echo -e "${GREEN}Tutti gli endpoint fermati.${NC}"; \
      exit 0' INT TERM

tail -f $LOG_DIR/*.log