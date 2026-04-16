#!/bin/bash

# ============================================================
#  SafeClaim – Avvio automatico di tutti gli endpoint Flask
# ============================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

echo -e "${YELLOW}=============================="
echo -e " SafeClaim – Avvio endpoint"
echo -e "==============================${NC}"

# --- MARIADB: INSTALLAZIONE E AVVIO ---
echo -e "${YELLOW}[*] Controllo MariaDB...${NC}"

if ! command -v mariadb &>/dev/null; then
    echo -e "${YELLOW}    MariaDB non trovata – installo...${NC}"
    # Ignora errori di repo non firmati (es. Yarn) e installa comunque
    sudo apt-get update -qq --allow-insecure-repositories 2>/dev/null || true
    sudo apt-get install -y mariadb-server -qq 2>/dev/null
fi

if command -v mariadb &>/dev/null; then
    sudo service mariadb start 2>/dev/null
    sleep 2
    echo -e "${GREEN}[✓] MariaDB in esecuzione${NC}"

    # Crea utente pythonuser se non esiste
    sudo mariadb -e "CREATE USER IF NOT EXISTS 'pythonuser'@'localhost' IDENTIFIED BY 'password123';" 2>/dev/null
    sudo mariadb -e "GRANT ALL PRIVILEGES ON *.* TO 'pythonuser'@'localhost' WITH GRANT OPTION;" 2>/dev/null
    sudo mariadb -e "FLUSH PRIVILEGES;" 2>/dev/null

    # Crea tabelle e dati solo se il DB non esiste ancora
    DB_EXISTS=$(sudo mariadb -u pythonuser -ppassword123 -e "SHOW DATABASES LIKE 'gestione_assicurazioni';" 2>/dev/null | grep -c "gestione_assicurazioni")
    if [ "$DB_EXISTS" -eq 0 ]; then
        echo -e "${YELLOW}    Prima installazione: creo il database...${NC}"
        python3 db_locale.py && echo -e "${GREEN}[✓] Database creato con successo${NC}"
    else
        echo -e "${GREEN}[✓] Database già esistente – salto la creazione${NC}"
    fi
else
    echo -e "${RED}[✗] Impossibile installare MariaDB – gli endpoint che usano MySQL non funzioneranno${NC}"
fi

# --- INSTALLAZIONE DIPENDENZE PYTHON ---
echo -e "${YELLOW}[*] Installo le dipendenze Python...${NC}"
pip install flask flask-cors mysql-connector-python "pymongo[srv]" dnspython requests --quiet --break-system-packages 2>/dev/null \
    || pip install flask flask-cors mysql-connector-python "pymongo[srv]" dnspython requests --quiet

if python3 -c "import flask, pymongo" 2>/dev/null; then
    echo -e "${GREEN}[✓] Dipendenze installate correttamente${NC}"
else
    echo -e "${RED}[✗] Errore installazione dipendenze – controlla la connessione${NC}"
    exit 1
fi

# --- CHIUDI PROCESSI PRECEDENTI ---
echo -e "${YELLOW}[*] Chiudo eventuali processi precedenti...${NC}"
for port in 5000 6000 7000 8000 9000 10000 11000; do
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
)

# --- AVVIO ENDPOINT ---
for file in "${!ENDPOINTS[@]}"; do
    port="${ENDPOINTS[$file]}"
    log="$LOG_DIR/${file%.py}.log"

    if [ ! -f "$file" ]; then
        echo -e "${RED}[✗] $file non trovato – salto${NC}"
        continue
    fi

    python3 "$file" > "$log" 2>&1 &
    PID=$!
    sleep 1

    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${GREEN}[✓] $file  →  porta $port  (PID $PID)${NC}"
    else
        echo -e "${RED}[✗] $file  →  avvio fallito – controlla $log${NC}"
        tail -n 3 "$log"
    fi
done

# --- PORTE PUBBLICHE SU CODESPACES ---
if command -v gh &>/dev/null && [ -n "$CODESPACE_NAME" ]; then
    echo -e "\n${YELLOW}[*] Imposto le porte come pubbliche su Codespaces...${NC}"
    for port in 5000 6000 7000 8000 9000 10000 11000; do
        gh codespace ports visibility "${port}:public" --codespace "$CODESPACE_NAME" 2>/dev/null \
            && echo -e "${GREEN}    porta $port → pubblica${NC}" \
            || echo -e "${YELLOW}    porta $port → imposta manualmente dal pannello Ports${NC}"
    done
fi

echo -e "\n${GREEN}=============================="
echo -e " Tutti gli endpoint avviati!"
echo -e " Log nella cartella: $LOG_DIR/"
echo -e "==============================${NC}"
echo -e "${YELLOW}[Premi CTRL+C per fermare tutto]\n${NC}"

trap "echo -e '\n${RED}Arresto in corso...${NC}'; fuser -k 5000/tcp 6000/tcp 7000/tcp 8000/tcp 9000/tcp 10000/tcp 11000/tcp 2>/dev/null; exit" INT

tail -f $LOG_DIR/*.log