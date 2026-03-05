import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 





def carica_conoscenza():
    """Legge le regole"""
    try:
        with open("RegoleSinistriChatBot.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Info: Compilare modulo CAI."

@app.route('/chat', methods=['POST'])
def chat_bot():
    data = request.json
    messaggio = data.get('messaggio')
    if not messaggio:
        return jsonify({"error": "Manca il messaggio"}), 400

    context = carica_conoscenza()
    # Prompt specifico per Phi-3
    prompt = f"<|user|>\nSei l'assistente SafeClaim. Info: {context}\nDomanda: {messaggio}<|end|>\n<|assistant|>"

    try:
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 250, "temperature": 0.4, "return_full_text": False},
            "options": {"wait_for_model": True}
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            return jsonify({
                "error": "Errore server AI",
                "status_code": response.status_code,
                "details": response.text 
            }), response.status_code

        output = response.json()
        # Estraiamo la risposta finale
        risposta_ai = output[0]['generated_text'].strip()

        return jsonify({"status": "success", "risposta": risposta_ai}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Porta 5001 per evitare il blocco visto su Postman
    print("Chatbot SafeClaim pronto sulla porta 5001!")
    app.run(debug=True, port=5001)