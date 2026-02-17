from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
# Importiamo l'utility per gestire gli ID di MongoDB
from bson.objectid import ObjectId

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

# Diciamo al server di ascoltare quando qualcuno vuole entrare all'indirizzo '/sinistro'
# Usiamo il metodo POST perché stiamo inviando dei nuovi dati da salvare
@app.route('/sinistro', methods=['POST'])
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

# --- 2. CARICAMENTO IMMAGINI ---

# Definiamo la rotta. <id> è una variabile
# Usiamo POST perché stiamo inviando dei nuovi dati (l'immagine) al server.
@app.route('/sinistro/<id>/immagini', methods=['POST'])
def aggiungi_immagine(id):
    # Recuperiamo il contenuto del pacchetto JSON che ci è arrivato
    data = request.json
    
    # Primo controllo: se nel JSON non c'è la chiave 'immagine_base64', inutile andare avanti.
    # Rispondiamo con un errore 400 (Bad Request).
    if 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        # 1. Cerchiamo il documento che ha l'ID uguale a quello passato nell'URL.
        #    Usiamo ObjectId(id) per convertire il testo in un formato che Mongo capisce.
        # 2. Usiamo $push per dire a Mongo: "Vai nel campo 'immagini' e aggiungi questa foto
        risultato = sinistri_col.update_one(
            {"_id": ObjectId(id)}, 
            {"$push": {"immagini": data['immagine_base64']}}
        )

        # Se matched_count è 0, vuol dire che Mongo non ha trovato nessun sinistro con quell'ID.
        if risultato.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404

        # Se tutto è andato bene, rispondiamo con un messaggio di conferma.
        return jsonify({"status": "success", "message": "Immagine caricata!"}), 200
        
    except Exception as e:
        # Se l'ID è scritto male (es. mancano caratteri) o il server crasha, 
        # restituiamo l'errore per capire cosa è successo.
        return jsonify({"status": "error", "message": str(e)}), 500
# --- ROTTA OTTIMIZZATA PER TEST (CARICA SULL'ULTIMO SINISTRO) ---

# Definiamo un URL fisso. Non serve più mettere <id> perché lo cercheremo noi nel DB.
@app.route('/sinistro/ultimo/immagini', methods=['POST'])
def aggiungi_immagine_ultimo():
    # Recuperiamo i dati (la stringa della foto) inviati nella richiesta
    data = request.json
    
    # Verifichiamo che l'utente non si sia dimenticato di allegare la foto nel JSON
    if 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        # 1. RICERCA AUTOMATICA DELL'ULTIMO SINISTRO
        # Usiamo .find_one() per prendere un solo documento.
        # sort=[("data_inserimento", -1)] dice a MongoDB: 
        # "Ordina i sinistri dal più recente al più vecchio e prendi il primo della lista".
        ultimo_sinistro = sinistri_col.find_one(sort=[("data_inserimento", -1)])

        # Se il database è vuoto, non troverà nulla. Gestiamo il caso per evitare crash.
        if not ultimo_sinistro:
            return jsonify({"error": "Nessun sinistro trovato nel database"}), 404

        # 2. AGGIORNAMENTO DELLA PRATICA TROVATA
        # Ora che abbiamo l'ID dell'ultimo sinistro (ultimo_sinistro["_id"]),
        # usiamo $push per inserire l'immagine nella sua lista di foto.
        sinistri_col.update_one(
            {"_id": ultimo_sinistro["_id"]}, 
            {"$push": {"immagini": data['immagine_base64']}}
        )

        # Rispondiamo con successo, restituendo anche l'ID che abbiamo usato 
        # così puoi verificare che sia quello corretto.
        return jsonify({
            "status": "success", 
            "message": "Immagine caricata sull'ultimo sinistro creato!",
            "id_usato": str(ultimo_sinistro["_id"])
        }), 200
        
    except Exception as e:
        # Gestione di eventuali errori tecnici (es. problemi di connessione al DB)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    # Lanciamo il server sulla porta 5000. 
    # debug=True serve a farlo riavviare da solo se modifichi il codice.
    app.run(debug=True, port=5000)