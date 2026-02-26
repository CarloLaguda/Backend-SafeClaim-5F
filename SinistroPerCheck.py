from flask import Flask, request, jsonify
from datetime import datetime
import uuid # Serve per generare ID unici finti

app = Flask(__name__)

# --- SIMULAZIONE DATABASE (LISTA IN MEMORIA) ---
# Invece di connetterci a MongoDB, salviamo i dati qui dentro.
# Attenzione: se riavvii il server, i dati spariranno (ma per i test è perfetto!)
db_finto = []

# --- 1. APERTURA SINISTRO ---
@app.route('/sinistro', methods=['POST'])
def apri_sinistro():
    data = request.json
    
    # Validazione campi obbligatori
    required_fields = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Campo mancante: {field}"}), 400

    try:
        # Creiamo il documento simulando quello che farebbe MongoDB
        nuovo_sinistro = {
            "_id": str(uuid.uuid4()), # Genera un ID finto tipo "550e8400-e29b..."
            "automobilista_id": data['automobilista_id'],
            "targa": data['targa'],
            "data_evento": data['data_evento'],
            "descrizione": data['descrizione'],
            "stato": "APERTO",
            "immagini": [], # Lista vuota pronta per le foto
            "data_inserimento": datetime.now().isoformat()
        }

        # Salviamo nella nostra lista locale
        db_finto.append(nuovo_sinistro)
        
        return jsonify({
            "status": "success",
            "message": "MODALITÀ OFFLINE: Sinistro salvato in memoria",
            "mongo_id": nuovo_sinistro["_id"]
        }), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 2. CARICAMENTO IMMAGINI (ULTIMO) ---
@app.route('/sinistro/ultimo/immagini', methods=['POST'])
def aggiungi_immagine_ultimo():
    data = request.json
    if 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    if not db_finto:
        return jsonify({"error": "Nessun sinistro trovato in memoria"}), 404

    try:
        # Prendiamo l'ultimo elemento della lista
        ultimo = db_finto[-1]
        ultimo['immagini'].append(data['immagine_base64'])

        return jsonify({
            "status": "success", 
            "message": "Immagine aggiunta all'ultimo sinistro (Offline)",
            "id_usato": ultimo["_id"]
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 3. VISUALIZZAZIONE TUTTI I SINISTRI ---
@app.route('/sinistri', methods=['GET'])
def ottieni_sinistri():
    return jsonify({
        "status": "success",
        "count": len(db_finto),
        "data": db_finto
    }), 200

if __name__ == '__main__':
    print("🚀 Server in MODALITÀ OFFLINE attivo sulla porta 5000")
    app.run(debug=True, port=5000)