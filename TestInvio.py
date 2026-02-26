import requests

# L'indirizzo del tuo nuovo endpoint (assicurati che il server sia acceso!)
url = "http://127.0.0.1:5000/sinistro"

# Il pacchetto JSON da inviare
dati_sinistro = {
    "automobilista_id": 101,
    "targa": "AB123CD",
    "data_evento": "2026-02-16",
    "descrizione": "Tamponamento a catena causato da frenata improvvisa al semaforo."
}

# Spediamo i dati
response = requests.post(url, json=dati_sinistro)

# Vediamo cosa ci risponde il server
print(f"Stato Risposta: {response.status_code}")
print(f"Risposta JSON: {response.json()}")