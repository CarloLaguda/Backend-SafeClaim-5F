from flask import Flask, request, jsonify

app = Flask(__name__)

# --- ENDPOINTS ASSICURATORE (Compiti di Toci & Sbarra) ---

# 3.1 Gestione Polizze (CRUD)
# L'assicuratore gestisce le polizze; un utente senza polizza non può aprire un sinistro.
@app.route('/polizze', methods=['GET', 'POST', 'PUT', 'DELETE'])
def gestisci_polizze():
    if request.method == 'GET':
        # Recupera l'elenco delle polizze [cite: 1, 5]
        return jsonify({"messaggio": "Elenco polizze recuperato"}), 200
    
    if request.method == 'POST':
        # Creazione di una nuova polizza [cite: 1, 5]
        data = request.json
        return jsonify({"messaggio": "Polizza creata", "data": data}), 201

# 3.2 Aggiornamento Stato Sinistro
# L'assicuratore cambia lo stato del sinistro in "presa in carico".
@app.route('/sinistro/<int:id_sinistro>', methods=['PUT'])
def aggiorna_stato_sinistro(id_sinistro):
    data = request.json
    # Logica per aggiornare o integrare informazioni sul sinistro 
    return jsonify({
        "id_sinistro": id_sinistro, 
        "nuovo_stato": data.get('stato', 'presa in carico')
    }), 200

# 3.3 Assegnazione Perito
# L'assicuratore assegna un perito a un sinistro specifico[cite: 1, 25].
@app.route('/sinistro/<int:id_sinistro>/perito', methods=['POST'])
def assegna_perito(id_sinistro):
    data = request.json
    perito_id = data.get('id_perito')
    # Invia mandato di perizia a un perito disponibile [cite: 25]
    return jsonify({
        "messaggio": f"Perito {perito_id} assegnato al sinistro {id_sinistro}"
    }), 200

# --- ENDPOINTS COMUNI / SUPPORTO ---

# Validazione Token JWT (Tutti gli attori)
# Necessario per la sicurezza di ogni chiamata.
@app.route('/validate', methods=['GET'])
def validate_token():
    return jsonify({"valid": True}), 200

# Recupero dati sinistro (Accessibile a tutti) 
@app.route('/sinistro/<int:id_sinistro>', methods=['GET'])
def get_sinistro(id_sinistro):
    return jsonify({"id": id_sinistro, "descrizione": "Dettagli sinistro"}), 200

if __name__ == '__main__':
    app.run(debug=True)
