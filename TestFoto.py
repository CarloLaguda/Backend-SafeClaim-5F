import requests

# L'indirizzo della tua nuova rotta "scorciatoia"
url = "http://127.0.0.1:5000/sinistro/ultimo/immagini"

# Qui mettiamo il JSON che mi hai scritto, trasformato in dizionario Python
dati_foto = {
    "immagine_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
}

# Spediamo la foto al server
response = requests.post(url, json=dati_foto)

# Stampiamo il risultato
print(f"Stato: {response.status_code}")
print(f"Risposta: {response.json()}")