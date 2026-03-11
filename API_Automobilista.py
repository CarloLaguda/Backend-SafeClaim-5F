from flask import Flask, request, jsonify  # Importa Flask per creare API web e gestire JSON
import pymongo  # Libreria per interagire con MongoDB
from datetime import datetime  # Per gestire timestamp
from bson import ObjectId  # Per lavorare con ID MongoDB

app = Flask(__name__)  # Crea app Flask

# --- CONFIGURAZIONE DATABASE ---

# Configurazione MongoDB Atlas
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"  # Stringa connessione MongoDB Atlas (include credenziali)
DB_NAME = "FakeClaim"  # Nome database

try:  # Prova connessione
    mongo_client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)  # Crea client con timeout
    mongo_db = mongo_client[DB_NAME]  # Seleziona database
    # Test connessione rapido
    mongo_client.admin.command('ping')  # Ping per verificare connessione
    print("Connessione a MongoDB Atlas riuscita!")  # Successo (stampa console)
except Exception as e:  # Errore connessione
    print(f"Errore critico di connessione a MongoDB: {e}")  # Errore (stampa console)

# --- ENDPOINTS ---

### 1. POST /soccorso
@app.route('/soccorso', methods=['POST'])  # Route per creare richiesta soccorso
def crea_richiesta_soccorso():  # Funzione handler
    try:  # Gestione errori
        data = request.json  # Ottiene dati JSON dalla richiesta (da client)
        if not data:  # Se no dati
            return jsonify({"error": "Corpo della richiesta mancante"}), 400  # Errore 400 (al client)
        
        targa_veicolo = data.get('targa')  # Estrae targa
        descrizione_guasto = data.get('descrizione', "Richiesta soccorso stradale")  # Estrae descrizione (default)
        lat = data.get('lat')  # Latitudine
        lon = data.get('lon')  # Longitudine
        
        if not targa_veicolo:  # Se no targa
            return jsonify({"error": "La targa del veicolo è obbligatoria"}), 400  # Errore (al client)
        
        # Inserimento dati dinamici direttamente su MongoDB (Senza verifica MySQL)
        nuovo_soccorso_mongo = {  # Crea documento per MongoDB
            "targa": targa_veicolo,
            "posizione": {"lat": lat, "lon": lon},
            "stato": "Richiesto",
            "dettagli": descrizione_guasto,
            "data_richiesta": datetime.utcnow()
        }
        
        # Usiamo la collezione 'Sinistro' nel DB 'FakeClaim'
        result_mongo = mongo_db.Sinistro.insert_one(nuovo_soccorso_mongo)  # Inserisce in MongoDB (dati vanno nella collezione Sinistro)
        mongo_id = str(result_mongo.inserted_id)  # Ottiene ID inserito
        
        return jsonify({  # Risposta JSON (al client)
            "message": "Soccorso registrato con successo",
            "intervento_id": mongo_id,
            "database_utilizzato": DB_NAME,
            "stato": "Richiesto"
        }), 201  # Codice 201 (creato)
    
    except pymongo.errors.PyMongoError as e:  # Errore MongoDB specifico
        return jsonify({"error": f"Errore Database MongoDB: {str(e)}"}), 500  # Errore 500 (al client)
    except Exception as e:  # Errore generico
        return jsonify({"error": f"Errore generico: {str(e)}"}), 500  # Errore 500 (al client)


### 2. GET /soccorso/<identificatore>
@app.route('/soccorso/<string:identificatore>', methods=['GET'])  # Route per ottenere dettaglio soccorso
def get_dettaglio_soccorso(identificatore):  # Funzione handler
    try:  # Gestione errori
        # Ricerca esclusiva su MongoDB (FakeClaim)
        if ObjectId.is_valid(identificatore):  # Se identificatore è ObjectId valido
            mongo_data = mongo_db.Sinistro.find_one({"_id": ObjectId(identificatore)})  # Cerca per ID (da MongoDB)
        else:  # Altrimenti cerca per targa
            mongo_data = mongo_db.Sinistro.find_one(  # Cerca per targa, ultimo per data
                {"targa": identificatore}, 
                sort=[("data_richiesta", -1)]
            )
        
        if not mongo_data:  # Se non trovato
            return jsonify({"error": "Nessun intervento trovato"}), 404  # Errore 404 (al client)
        
        # Convertiamo l'ID in formato leggibile per il JSON
        mongo_data['_id'] = str(mongo_data['_id'])  # Converte ID a stringa
        
        # Restituiamo solo le informazioni del soccorso (niente più dati veicolo da MySQL)
        return jsonify({  # Risposta JSON (al client)
            "soccorso_info": mongo_data
        }), 200  # Codice 200 (OK)
    
    except Exception as e:  # Errore generico
        return jsonify({"error": f"Errore nel recupero dati: {str(e)}"}), 500  # Errore 500 (al client)

if __name__ == '__main__':  # Se eseguito direttamente
    app.run(debug=True, host='0.0.0.0', port=5000)  # Avvia server su porta 5000 (ascolta richieste)