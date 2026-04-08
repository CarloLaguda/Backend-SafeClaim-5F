from flask import Flask, request, jsonify  # Importa Flask per creare API web e gestire JSON
import pymongo  # Libreria per interagire con MongoDB
from datetime import datetime  # Per gestire timestamp
from bson import ObjectId  # Per lavorare con ID MongoDB

app = Flask(__name__)  # Crea app Flask

# --- CONFIGURAZIONE DATABASE ---

# Configurazione MongoDB Atlas
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"  # Stringa connessione MongoDB Atlas
DB_NAME = "FakeClaim"  # Nome database

try:  # Prova connessione
    mongo_client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)  # Crea client con timeout
    mongo_db = mongo_client[DB_NAME]  # Seleziona database
    mongo_client.admin.command('ping')  # Ping per verificare connessione
    print("✅ Connessione a MongoDB Atlas riuscita!")  
except Exception as e:  # Errore connessione
    print(f"❌ Errore critico di connessione a MongoDB: {e}") 

# --- ENDPOINTS ---

### 1. POST /soccorso
@app.route('/soccorso', methods=['POST'])  
def crea_richiesta_soccorso():  
    try:  
        data = request.json  
        if not data:  
            return jsonify({"error": "Corpo della richiesta mancante"}), 400  
        
        nome = data.get('nome', "Sconosciuto")
        cognome = data.get('cognome', "Sconosciuto")
        targa_veicolo = data.get('targa')  
        descrizione_guasto = data.get('descrizione', "Richiesta soccorso stradale")  
        
        # 1. Recuperiamo lat e lon
        lat_str = data.get('lat')  
        lon_str = data.get('lon')  
        
        if not targa_veicolo:  
            return jsonify({"error": "La targa del veicolo è obbligatoria"}), 400  

        # 2. Convertiamo le stringhe in numeri decimali (float) per MongoDB
        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except (TypeError, ValueError):
            return jsonify({"error": "Latitudine e longitudine devono essere numeri validi"}), 400
        
        # 3. Formattiamo la posizione secondo lo standard GeoJSON
        nuovo_soccorso_mongo = {  
            "nome": nome,
            "cognome": cognome,
            "targa": targa_veicolo,
            # ATTENZIONE: In GeoJSON l'ordine è sempre [Longitudine, Latitudine]
            "posizione": {
                "type": "Point",
                "coordinates": [lon, lat] 
            },
            "stato": "Richiesto",
            "dettagli": descrizione_guasto,
            "data_richiesta": datetime.utcnow()
        }
        
        result_mongo = mongo_db.Sinistro.insert_one(nuovo_soccorso_mongo)  
        mongo_id = str(result_mongo.inserted_id)  
        
        return jsonify({  
            "message": "Soccorso registrato con successo",
            "intervento_id": mongo_id,
            "database_utilizzato": DB_NAME,
            "stato": "Richiesto"
        }), 201  
    
    except pymongo.errors.PyMongoError as e:  
        return jsonify({"error": f"Errore Database MongoDB: {str(e)}"}), 500  
    except Exception as e:  
        return jsonify({"error": f"Errore generico: {str(e)}"}), 500  


### 2. GET /soccorso/<identificatore> (RICERCA ESATTA ORIGINALE)
@app.route('/soccorso/<string:identificatore>', methods=['GET'])  
def get_dettaglio_soccorso(identificatore):  
    try:  
        if ObjectId.is_valid(identificatore):  
            mongo_data = mongo_db.Sinistro.find_one({"_id": ObjectId(identificatore)})  
        else:  
            mongo_data = mongo_db.Sinistro.find_one(  
                {"targa": identificatore}, 
                sort=[("data_richiesta", -1)]
            )
        
        if not mongo_data:  
            return jsonify({"error": "Nessun intervento trovato"}), 404  
        
        mongo_data['_id'] = str(mongo_data['_id'])  
        
        return jsonify({"soccorso_info": mongo_data}), 200  
    
    except Exception as e:  
        return jsonify({"error": f"Errore nel recupero dati: {str(e)}"}), 500  


### 3. GET /soccorsi/ricerca (NUOVO ENDPOINT: RICERCA E CRONOLOGIA)
@app.route('/soccorsi/ricerca', methods=['GET'])
def ricerca_cronologia_soccorsi():
    """
    Questo endpoint serve agli operatori. Permette di cercare per nome, cognome o targa.
    Restituisce una CRONOLOGIA (lista ordinata per data) di tutti i soccorsi trovati.
    """
    try:
        # Recuperiamo i parametri passati nell'URL (es: ?nome=Mario&cognome=Rossi)
        nome = request.args.get('nome')
        cognome = request.args.get('cognome')
        targa = request.args.get('targa')

        # Costruiamo dinamicamente la query per MongoDB
        query = {}
        
        # Usiamo $regex per una ricerca parziale e $options: 'i' per ignorare maiuscole/minuscole
        if nome:
            query['nome'] = {'$regex': nome, '$options': 'i'}
        if cognome:
            query['cognome'] = {'$regex': cognome, '$options': 'i'}
        if targa:
            query['targa'] = {'$regex': targa, '$options': 'i'}

        # Se l'operatore non inserisce nessun parametro, restituiamo errore
        if not query:
            return jsonify({"error": "Fornire almeno un parametro di ricerca (?nome=... o ?cognome=... o ?targa=...)"}), 400

        # Eseguiamo la ricerca su MongoDB. 
        # .sort("data_richiesta", -1) ordina i risultati dal più recente al più vecchio (Cronologia)
        cursor = mongo_db.Sinistro.find(query).sort("data_richiesta", -1)
        risultati = list(cursor) # Trasforma il cursore in una lista Python

        if not risultati:
            return jsonify({
                "message": "Nessun soccorso trovato per i criteri inseriti", 
                "storico_incidenti": []
            }), 200

        # Convertiamo l'ObjectId in stringa per poterlo stampare nel JSON
        for res in risultati:
            res['_id'] = str(res['_id'])

        # Restituiamo il conteggio e l'intera cronologia
        return jsonify({
            "message": f"Trovati {len(risultati)} interventi",
            "storico_incidenti": risultati
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante la ricerca: {str(e)}"}), 500


if __name__ == '__main__':  
    app.run(debug=True, host='0.0.0.0', port=5000)