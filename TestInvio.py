import requests

url = "http://127.0.0.1:5000/apri-sinistro"
dati_sinistro = {
    "automobilista_id": 1,
    "targa": "AA123BB",
    "data_evento": "2026-02-12",
    "descrizione": "Tamponamento lieve al semaforo"
}

response = requests.post(url, json=dati_sinistro)

print(f"Stato Risposta: {response.status_code}")
print(f"Risposta JSON: {response.json()}")