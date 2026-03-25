"""
test_automatico.py — Test completo del flusso asincrono con Cloudinary
Esegui con: python test_automatico.py
Assicurati che il server sia già avviato su porta 7000.
"""

import requests
import base64
import time
import json

BASE_URL  = "https://probable-space-winner-x55jj945vppqhp46w-7000.app.github.dev/"
IMAGE_PATH = "car_crash.jpg"  # Deve essere nella stessa cartella

def stampa_separatore(titolo):
    print(f"\n{'='*50}")
    print(f"  {titolo}")
    print('='*50)

# ── STEP 1: Crea un sinistro ──────────────────────────
stampa_separatore("STEP 1 — Creazione sinistro")

risposta = requests.post(f"{BASE_URL}/sinistro", json={
    "automobilista_id": "1",
    "targa": "AA001BB",
    "data_evento": "2026-03-25",
    "descrizione": "Tamponamento in autostrada - test automatico"
})

if risposta.status_code != 201:
    print(f"❌ Errore creazione sinistro: {risposta.text}")
    exit(1)

mongo_id = risposta.json()["mongo_id"]
print(f"✅ Sinistro creato con ID: {mongo_id}")

# ── STEP 2: Converti immagine in base64 ──────────────
stampa_separatore("STEP 2 — Conversione immagine in base64")

try:
    with open(IMAGE_PATH, "rb") as f:
        immagine_b64 = base64.b64encode(f.read()).decode("utf-8")
    print(f"✅ Immagine convertita ({len(immagine_b64)} caratteri)")
except FileNotFoundError:
    print(f"❌ File '{IMAGE_PATH}' non trovato. Mettilo nella stessa cartella dello script.")
    exit(1)

# ── STEP 3: Carica immagine → Cloudinary → avvia AI ──
stampa_separatore("STEP 3 — Upload su Cloudinary + avvio analisi AI")

risposta = requests.post(f"{BASE_URL}/sinistro/ultimo/immagini", json={
    "immagine_base64": immagine_b64
})

if risposta.status_code != 202:
    print(f"❌ Errore upload immagine: {risposta.text}")
    exit(1)

body = risposta.json()
print(f"✅ Risposta 202 ricevuta — AI avviata in background")
print(f"   Immagine su Cloudinary: {body.get('immagine_url')}")
print(f"   Messaggio: {body.get('messaggio')}")

# ── STEP 4: Polling finché l'analisi non è pronta ────
stampa_separatore("STEP 4 — Polling analisi AI (attendo risultato...)")

MAX_TENTATIVI = 30   # massimo ~5 minuti
INTERVALLO    = 10   # secondi tra un polling e l'altro

for tentativo in range(1, MAX_TENTATIVI + 1):
    time.sleep(INTERVALLO)

    risposta = requests.get(f"{BASE_URL}/sinistro/{mongo_id}/analisi")

    if risposta.status_code != 200:
        print(f"⚠️  Tentativo {tentativo}: errore polling ({risposta.status_code})")
        continue

    analisi = risposta.json()
    stato   = analisi.get("stato", "sconosciuto")

    print(f"🔄 Tentativo {tentativo}/{MAX_TENTATIVI} — stato: {stato}")

    if stato == "completata":
        stampa_separatore("✅ ANALISI AI COMPLETATA")
        print(json.dumps(analisi, indent=2, ensure_ascii=False))
        break

    elif stato == "errore":
        stampa_separatore("❌ ANALISI AI FALLITA")
        print(json.dumps(analisi, indent=2, ensure_ascii=False))
        break

else:
    print("\n⏰ Timeout: l'analisi AI non ha risposto entro il tempo massimo.")
    print("   Controlla i log del server Flask per dettagli.")