import requests
# Questo è l'indirizzo di casa del server Flask, dove è in ascolto per ricevere i dati dei sinistri.
url = "http://127.0.0.1:5000/apri-sinistro"
# Qui prepariamo il "pacco" con tutte le info del sinistro da spedire
dati_sinistro = {
    "automobilista_id": 1,
    "targa": "AA123BB",
    "data_evento": "2026-02-12",
    "descrizione": "Tamponamento lieve al semaforo"
}
# Spediamo il pacchetto al server usando il metodo POST. 
# Il parametro json= trasforma automaticamente il nostro dizionario in un formato che il web capisce.
response = requests.post(url, json=dati_sinistro)

# Dopo la spedizione, il server ci risponde. 
# Qui stampiamo il "codice di stato": 201 significa "Ottimo, creato!", 500 significa "C'è un errore nel server".
print(f"Stato Risposta: {response.status_code}")
# Infine, leggiamo il "corpo della risposta" che il server ci ha rimandato (il JSON)
print(f"Risposta JSON: {response.json()}")