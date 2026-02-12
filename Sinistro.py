from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAZIONE MONGODB ---
# Usiamo la stringa di connessione che hai fornito per collegarci al server
MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
client = MongoClient(MONGO_URI)
# Selezioniamo il database e la collezione (che in Mongo funge da tabella)
db = client['safeclaim_mongo']
sinistri_col = db['sinistri'] 

@app.route('/apri-sinistro', methods=['POST'])
def apri_sinistro():
    # Recuperiamo i dati inviati dallo script di test
    data = request.json

    # 1. Validazione semplice dei dati
    required_fields = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Campo mancante: {field}"}), 400

    try:
        # 2. Preparazione del documento da inserire nella collezione MongoDB
        nuovo_sinistro = {
            "automobilista_id": data['automobilista_id'],
            "targa": data['targa'],
            "data_evento": data['data_evento'],
            "descrizione": data['descrizione'],
            "stato": "APERTO",
            "data_inserimento": datetime.now()
        }

        # 3. Inserimento effettivo in MongoDB
        risultato = sinistri_col.insert_one(nuovo_sinistro)
        
        # Rispondiamo al client con l'ID generato automaticamente da MongoDB
        return jsonify({
            "status": "success",
            "message": "Sinistro salvato correttamente su MongoDB",
            "mongo_id": str(risultato.inserted_id)
        }), 201

    except Exception as e:
        # Gestione di eventuali errori di connessione al database
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Avviamo il server sulla porta 5000
    app.run(debug=True, port=5000)