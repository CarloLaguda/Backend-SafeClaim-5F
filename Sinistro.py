from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime

# Creiamo l'oggetto 'app' che rappresenta il nostro server web
app = Flask(__name__)

# --- CONFIGURAZIONE MONGODB ---
# Usiamo la stringa URL di connessione per collegarci al server
MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
# Apriamo la connessione vera e propria verso il server MongoDB
client = MongoClient(MONGO_URI)
# Entriamo dentro il database chiamato 'safeclaim_mongo'
db = client['safeclaim_mongo']
# Entriamo nella collezione (il cassetto) 'sinistri'. 
# Useremo questa variabile 'sinistri_col' per aggiungere o cercare dati.
sinistri_col = db['sinistri']  #variabile che serve a interagire con la collezione di MongoDB

# Diciamo al server di ascoltare quando qualcuno vuole entrare all'indirizzo '/apri-sinistro'
# Usiamo il metodo POST perché stiamo inviando dei nuovi dati da salvare
@app.route('/apri-sinistro', methods=['POST'])
def apri_sinistro():
    data = request.json  # Prendiamo i dati che l'utente ci ha inviato 

    # 1. Validazione semplice dei dati
    # Verifichiamo che ci siano tutte le informazioni fondamentali
    required_fields = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    for field in required_fields:
        if field not in data:
            # Se ne manca anche solo uno, rispondiamo con un errore e ci fermiamo qui
            return jsonify({"error": f"Campo mancante: {field}"}), 400

    try:
        # 2. Preparazione del documento da inserire nella collezione MongoDB
        # Creiamo un "pacchetto" con i dati ricevuti
        nuovo_sinistro = {
            "automobilista_id": data['automobilista_id'],
            "targa": data['targa'],
            "data_evento": data['data_evento'],
            "descrizione": data['descrizione'],
            "stato": "APERTO",
            "data_inserimento": datetime.now()
        }

        # 3. Salvataggio in MongoDB
        # Diciamo alla nostra collezione di inserire questo pacchetto nel database
        risultato = sinistri_col.insert_one(nuovo_sinistro)
        
        # 4. RISPOSTA DEL SERVER AL CLIENT
        # Se tutto è andato bene, rispondiamo con un messaggio di conferma 
        # e includiamo l'ID unico che MongoDB ha assegnato a questo sinistro.
        return jsonify({
            "status": "success",
            "message": "Sinistro salvato correttamente su MongoDB",
            "mongo_id": str(risultato.inserted_id)
        }), 201

    except Exception as e:
        # Se succede qualcosa di imprevisto (es. il database è spento), 
        # inviamo un messaggio di errore 
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Lanciamo il server sulla porta 5000. 
    # debug=True serve a farlo riavviare da solo se modifichi il codice.
    app.run(debug=True, port=5000)