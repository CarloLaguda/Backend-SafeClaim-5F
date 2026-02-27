from flask import Flask, request, jsonify
from flask_cors import CORS  # 1. Importa CORS
import mysql.connector

app = Flask(__name__)

# 2. Configura CORS per permettere le chiamate dal frontend
CORS(app)

# --- CONNESSIONE MYSQL ---
def get_db_connection():
    return mysql.connector.connect(
        host="mysql-safeclaim.aevorastudios.com",
        user="safeclaim",
        password="0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
        database="safeclaim_db"
    )

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email_in = data.get('email')
        psw_in = data.get('psw')

        if not email_in or not psw_in:
            return jsonify({"error": "Email e password obbligatorie"}), 400

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        
        # Lista delle tabelle in cui cercare l'utente
        tabelle = ["Assicuratore", "Automobilista", "Perito"]
        user_found = None
        ruolo_scoperto = ""

        for tabella in tabelle:
            # Cerchiamo nelle tabelle usando i nomi colonne corretti: email e psw
            query = f"SELECT id, nome, cognome, email FROM {tabella} WHERE email = %s AND psw = %s"
            cursor.execute(query, (email_in, psw_in))
            user_found = cursor.fetchone()
            
            if user_found:
                ruolo_scoperto = tabella.lower()
                break

        cursor.close()
        db.close()

        if user_found:
            # Aggiungiamo il ruolo al risultato per il frontend
            user_found['ruolo'] = ruolo_scoperto
            return jsonify({
                "status": "success",
                "message": f"Bentornato {user_found['nome']}",
                "user": user_found
            }), 200
        else:
            return jsonify({"status": "error", "message": "Credenziali non valide"}), 401

    except Exception as e:
        return jsonify({"error": "Errore server", "details": str(e)}), 500

if __name__ == '__main__':
    # Assicurati che flask-cors sia installato: pip install flask-cors
    app.run(port=5001, debug=True)