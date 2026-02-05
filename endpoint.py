from flask import Flask, request, jsonify

app = Flask(__name__)

# --- 3.1 SVILUPPO API ASSICURATORE: GESTIONE POLIZZE (CRUD) ---
# Compito assegnato a Toci 
# Nota: Un utenza senza polizza non può aprire sinistro 

@app.route('/polizze', methods=['GET'])
def elenco_polizze():
    # Recupera l'elenco completo per l'assicuratore 
    return jsonify({"status": "success", "data": []}), 200

@app.route('/polizze', methods=['POST'])
def crea_polizza():
    # Creazione nuova polizza (Task 3.1) 
    data = request.json
    return jsonify({"message": "Polizza creata", "id": 123}), 201

@app.route('/polizze/<int:id>', methods=['PUT', 'DELETE'])
def modifica_elimina_polizza(id):
    # Gestione completa CRUD [cite: 1, 5]
    return jsonify({"message": f"Polizza {id} gestita"}), 200


# --- 3.3 ASSEGNAZIONE PERITO ---
# Compito assegnato a Sbarra/Toci 

@app.route('/sinistro/<int:id_sinistro>/perito', methods=['POST'])
def assegna_perito(id_sinistro):
    # L'assicuratore invia il mandato di perizia a un perito [cite: 1, 25]
    data = request.json
    id_perito = data.get('id_perito')
    return jsonify({
        "messaggio": f"Mandato inviato al perito {id_perito} per il sinistro {id_sinistro}"
    }), 200


# --- FUNZIONE DI SUPPORTO PER REGISTRAZIONE AUTOMOBILISTA ---
# Verifica se l'automobilista è cliente prima della conferma registrazione 

@app.route('/verifica-cliente/<string:codice_fiscale>', methods=['GET'])
def verifica_cliente(codice_fiscale):
    # Richiesta necessaria per validare l'automobilista nel DB assicurazione 
    # Restituisce True se il cliente esiste, altrimenti False
    return jsonify({"is_cliente": True}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
