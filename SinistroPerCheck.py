from flask import Flask, request, jsonify  # Importa Flask per creare il server e gestire i JSON
from datetime import datetime  # Importa la gestione di date e orari
import uuid # Importa la libreria per generare codici ID casuali (universally unique identifier)

app = Flask(__name__) # Crea l'istanza dell'applicazione SafeClaim

# --- SIMULAZIONE DATABASE (LISTA IN MEMORIA) ---
# Creiamo una lista vuota: finché il server è acceso, i dati staranno qui dentro.
# Se riavvii il server, questa lista torna vuota (per questo è una simulazione).
db_finto = []

# --- 1. APERTURA SINISTRO (METODO POST) ---
@app.route('/sinistro', methods=['POST']) # Definisce l'indirizzo per creare una nuova pratica
def apri_sinistro():
    data = request.json # Legge il pacchetto di dati inviato (es. da Postman)
    
    # Elenco dei campi che l'utente DEVE obbligatoriamente inviare
    required_fields = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    for field in required_fields:
        if field not in data:
            # Se manca anche solo un campo, il server risponde con errore 400
            return jsonify({"error": f"Campo mancante: {field}"}), 400

    try:
        # Creiamo un "Dizionario" che rappresenta il nostro sinistro
        nuovo_sinistro = {
            "_id": str(uuid.uuid4()), # Genera un ID unico casuale per identificare la pratica
            "automobilista_id": data['automobilista_id'], # Prende l'ID dell'utente dai dati ricevuti
            "targa": data['targa'], # Prende la targa
            "data_evento": data['data_evento'], # Prende la data dell'incidente
            "descrizione": data['descrizione'], # Prende la descrizione
            "stato": "APERTO", # Stato predefinito per i nuovi sinistri
            "immagini": [], # Crea una lista vuota dove aggiungeremo le foto dopo
            "data_inserimento": datetime.now().isoformat() # Segna il momento della creazione in formato testo
        }

        # Aggiunge il sinistro appena creato alla nostra lista "db_finto"
        db_finto.append(nuovo_sinistro)
        
        # Risponde all'utente confermando il salvataggio in memoria
        return jsonify({
            "status": "success",
            "message": "MODALITÀ OFFLINE: Sinistro salvato in memoria",
            "mongo_id": nuovo_sinistro["_id"] # Restituisce l'ID generato per poterlo usare dopo
        }), 201

    except Exception as e:
        # Se succede un errore imprevisto, risponde con codice 500
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 2. CARICAMENTO IMMAGINI SULL'ULTIMO SINISTRO (METODO POST) ---
@app.route('/sinistro/ultimo/immagini', methods=['POST']) # Indirizzo per aggiungere foto all'ultima pratica
def aggiungi_immagine_ultimo():
    data = request.json # Legge i dati della foto
    # Controlla se il campo dell'immagine è presente
    if 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    # Se la lista db_finto è vuota, non possiamo aggiungere foto
    if not db_finto:
        return jsonify({"error": "Nessun sinistro trovato in memoria"}), 404

    try:
        # db_finto[-1] seleziona l'ultimo elemento inserito nella lista
        ultimo = db_finto[-1]
        # Aggiunge la stringa della foto alla lista 'immagini' di quel sinistro
        ultimo['immagini'].append(data['immagine_base64'])

        # Risponde confermando l'aggiunta della foto
        return jsonify({
            "status": "success", 
            "message": "Immagine aggiunta all'ultimo sinistro (Offline)",
            "id_usato": ultimo["_id"]
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 3. CARICAMENTO IMMAGINI TRAMITE ID SPECIFICO (METODO POST) ---
@app.route('/sinistro/<id_sinistro>/immagini', methods=['POST']) # L'ID viene passato direttamente nell'URL
def aggiungi_immagine_id(id_sinistro):
    data = request.json # Legge i dati JSON
    
    # Verifica che la foto sia presente
    if 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        # Cerca dentro db_finto il primo sinistro che ha lo stesso ID passato nell'URL
        sinistro_trovato = next((s for s in db_finto if s["_id"] == id_sinistro), None)

        if sinistro_trovato:
            # Se lo trova, aggiunge l'immagine alla lista di quel sinistro specifico
            sinistro_trovato['immagini'].append(data['immagine_base64'])
            return jsonify({
                "status": "success", 
                "message": f"Immagine aggiunta correttamente al sinistro {id_sinistro}"
            }), 200
        else:
            # Se dopo aver cercato in tutta la lista non lo trova, risponde 404
            return jsonify({"error": "Sinistro non trovato con questo ID"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 4. VISUALIZZAZIONE TUTTI I SINISTRI (METODO GET) ---
@app.route('/sinistri', methods=['GET']) # Indirizzo per leggere tutto il "database"
def ottieni_sinistri():
    # Restituisce l'intera lista db_finto trasformata in JSON
    return jsonify({
        "status": "success",
        "count": len(db_finto), # Indica quanti sinistri ci sono in memoria
        "data": db_finto # Invia la lista completa dei dati
    }), 200

# --- AVVIO DEL SERVER ---
if __name__ == '__main__':
    # Stampa un messaggio per avvisare che stiamo lavorando in RAM (Offline)
    print("🚀 Server in MODALITÀ OFFLINE attivo sulla porta 5000")
    # Avvia Flask in modalità debug
    app.run(debug=True, port=5000)