from flask import Flask, request, jsonify
import re
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# Configurazione Database MySQL
db_config = {
    'host': 'mysql-safeclaim.aevorastudios.com',
    'port': 3306,
    'user': 'safeclaim',
    'password': '0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
    'database': 'safeclaim_db'
}

def valida_password(password):
    """Verifica che la password abbia 8 caratteri, lettere e numeri."""
    if len(password) < 8:
        return False, "La password deve essere lunga almeno 8 caratteri."
    if not re.search(r"[a-zA-Z]", password):
        return False, "La password deve contenere almeno una lettera."
    if not re.search(r"\d", password):
        return False, "La password deve contenere almeno un numero."
    return True, None

def valida_dati_utente(data):
    """Esegue tutti i controlli di robustezza sui dati ricevuti."""
    pattern_nomi = r"^[a-zA-Zàáâäãåèéêëìíîïòóôöùúûüç \s']+$"
    
    if not re.match(pattern_nomi, data.get('nome', '')):
        return False, "Il nome non è valido o contiene numeri."
    
    if not re.match(pattern_nomi, data.get('cognome', '')):
        return False, "Il cognome non è valido o contiene numeri."
    
    if not re.match(r'^[A-Z0-9]{16}$', data.get('cf', '').upper()):
        return False, "Il CF deve essere di esattamente 16 caratteri alfanumerici."
    
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data.get('email', '')):
        return False, "Formato email non valido."
    
    # Validazione password
    valida_psw, err_psw = valida_password(data.get('psw', ''))
    if not valida_psw:
        return False, err_psw
        
    return True, None

@app.route('/registrazione', methods=['POST'])
def registrazione():
    # Ricezione dei dati JSON
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400

    # 1. Validazione Robustezza (quella che abbiamo testato in console)
    is_valid, error_message = valida_dati_utente(data)
    if not is_valid:
        return jsonify({"error": error_message}), 400

    # 2. Inserimento nel Database
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        query = """
        INSERT INTO Automobilista (nome, cognome, cf, email, psw) 
        VALUES (%s, %s, %s, %s, %s)
        """
        
        # Pulizia e formattazione finale
        values = (
            data['nome'].strip().title(), 
            data['cognome'].strip().title(), 
            data['cf'].strip().upper(), 
            data['email'].strip().lower(), 
            data['psw'] # Salvata in chiaro come richiesto
        )

        cursor.execute(query, values)
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Automobilista registrato con successo",
            "id": cursor.lastrowid
        }), 201

    except mysql.connector.IntegrityError:
        return jsonify({"error": "Email o Codice Fiscale già registrati."}), 409
    except Error as e:
        return jsonify({"error": f"Errore del database: {str(e)}"}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == '__main__':
    # Avvia il server sulla porta 5000
    app.run(debug=True, port=5000)