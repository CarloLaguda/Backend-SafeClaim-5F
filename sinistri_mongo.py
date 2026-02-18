from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)

# Configurazione MongoDB
MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
client = MongoClient(MONGO_URI)
db = client['safeclaim_mongo']
sinistri_col = db['Sinistro'] # Assicurati che il nome sia identico a quello su Compass

# --- TASK 3.3: ASSEGNAZIONE PERITO ---
@app.route('/sinistro/<id_sinistro>/perito', methods=['PUT'])
def assegna_perito(id_sinistro):
    try:
        data = request.get_json()
        id_perito = data.get('id_perito')
        
        # Validazione input
        if id_perito is None:
            return jsonify({"error": "Campo 'id_perito' mancante"}), 400

        # Eseguiamo l'aggiornamento (PUT) sul documento esistente
        result = sinistri_col.update_one(
            {"_id": ObjectId(id_sinistro)},
            {"$set": {
                "perito_id": id_perito,
                "stato": "assegnato_a_perito",
                "data_assegnazione": datetime.now()
            }}
        )

        # Verifica se il documento è stato trovato e aggiornato
        if result.matched_count > 0:
            return jsonify({
                "status": "success",
                "message": f"Il perito {id_perito} è stato assegnato al sinistro {id_sinistro}"
            }), 200
        else:
            return jsonify({"error": "Sinistro non trovato"}), 404

    except Exception as e:
        return jsonify({"error": "ID non valido o errore server", "details": str(e)}), 400

if __name__ == '__main__':
    app.run(port=5001, debug=True)
