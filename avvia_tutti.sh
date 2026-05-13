#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

echo -e "${YELLOW}==============================\n SafeClaim – Avvio endpoint\n==============================${NC}"

echo -e "\n${CYAN}[1/3] Installo le dipendenze Python...${NC}"
PACKAGES=("flask" "flask-cors" "mysql-connector-python" "pymongo[srv]" "dnspython" "requests" "cloudinary" "google-generativeai" "scikit-learn" "google-genai" "numpy" "python-dotenv" "PyJWT")
pip install "${PACKAGES[@]}" --quiet --break-system-packages 2>/dev/null || pip install "${PACKAGES[@]}" --quiet 2>/dev/null

MISSING_MODULES=()
for mod in flask pymongo cloudinary google.generativeai sklearn; do
    python3 -c "import $mod" 2>/dev/null || MISSING_MODULES+=("$mod")
done

if [ ${#MISSING_MODULES[@]} -eq 0 ]; then
    echo -e "${GREEN}[✓] Tutte le dipendenze installate${NC}"
else
    echo -e "${RED}[✗] Moduli mancanti: ${MISSING_MODULES[*]}${NC}"
    for mod in "${MISSING_MODULES[@]}"; do
        pip install "$mod" --quiet --break-system-packages 2>/dev/null || pip install "$mod" --quiet 2>/dev/null
    done
fi

echo -e "\n${CYAN}[2/3] Controllo file necessari...${NC}"
[ -f "Storage.py" ] && echo -e "${GREEN}[✓] Storage.py presente${NC}" || echo -e "${RED}[✗] Storage.py non trovato${NC}"
[ -f "endpoint_5F_RAG_Assistente.py" ] && echo -e "${GREEN}[✓] RAG presente${NC}" || echo -e "${RED}[✗] RAG non trovato${NC}"

echo -e "\n${CYAN}[3/3] Avvio endpoint Flask...${NC}"
for port in 5000 6000 7000 8000 9000 10000 11000 12000; do fuser -k "${port}/tcp" 2>/dev/null; done
sleep 1

declare -A ENDPOINTS=(["endpoint_5F_Assicurazione.py"]=5000 ["endpoint_5F_log_reg.py"]=6000 ["endpoint_5F_Sinistri_User.py"]=7000 ["endpoint_5F_Periti.py"]=8000 ["endpoint_5F_Polizze.py"]=9000 ["endpoint_5F_Veicoli.py"]=10000 ["endpoint_5F_Mail.py"]=11000 ["endpoint_5F_RAG_Assistente.py"]=12000)

STARTED=0; FAILED=0
for file in "${!ENDPOINTS[@]}"; do
    port="${ENDPOINTS[$file]}"; log="$LOG_DIR/${file%.py}.log"
    [ ! -f "$file" ] && echo -e "${RED}[✗] $file non trovato${NC}" && (( FAILED++ )) && continue
    [ "$file" = "endpoint_5F_RAG_Assistente.py" ] && WAIT=4 || WAIT=1.5
    python3 "$file" > "$log" 2>&1 &
    PID=$!; sleep "$WAIT"
    kill -0 "$PID" 2>/dev/null && echo -e "${GREEN}[✓] $file → porta $port (PID $PID)${NC}" && (( STARTED++ )) \
        || { echo -e "${RED}[✗] $file → avvio fallito${NC}"; tail -n 5 "$log" | sed 's/^/    /'; (( FAILED++ )); }
done

# --- PORTE PUBBLICHE SU CODESPACES ---
echo -e "\n${CYAN}[*] Imposto le porte come pubbliche...${NC}"
for port in 5000 6000 7000 8000 9000 10000 11000 12000; do
    gh codespace ports visibility "${port}:public" -c "$CODESPACE_NAME" 2>/dev/null \
        && echo -e "${GREEN}    [✓] porta $port → pubblica${NC}" \
        || echo -e "${YELLOW}    [!] porta $port → impostala manualmente dal pannello Ports${NC}"
done

echo -e "\n${GREEN}==============================\n Avviati: ${STARTED} | Falliti: ${FAILED}\n==============================${NC}"

trap 'fuser -k 5000/tcp 6000/tcp 7000/tcp 8000/tcp 9000/tcp 10000/tcp 11000/tcp 12000/tcp 2>/dev/null; exit 0' INT TERM
tail -f $LOG_DIR/*.log
