from flask import Flask, request, jsonify  # Importa Flask per le API e moduli per gestire i dati JSON
import pymongo  # Libreria ufficiale per far comunicare Python con MongoDB
from datetime import datetime  # Ci serve per registrare l'ora esatta del soccorso
from bson import ObjectId  # Strumento per leggere e gestire gli ID unici di MongoDB

app = Flask(__name__)  # Inizializza l'applicazione web Flask

# --- CONFIGURAZIONE DATABASE ---

# Stringa di connessione a MongoDB Atlas (contiene credenziali e indirizzo)
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"  
DB_NAME = "FakeClaim"  # Specifica il nome del database che vogliamo usare

try:  # Blocco try-except per gestire eventuali cadute di connessione
    mongo_client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)  # Tenta la connessione con un timeout di 5 secondi
    mongo_db = mongo_client[DB_NAME]  # Seleziona il database specifico
    mongo_client.admin.command('ping')  # Lancia un "ping" per assicurarsi che il server risponda
    print("✅ Connessione a MongoDB Atlas riuscita!")  # Messaggio di successo in console
except Exception as e:  
    print(f"❌ Errore critico di connessione a MongoDB: {e}")  # Messaggio in caso di server irraggiungibile

# --- ENDPOINTS (LE ROTTE DELLA NOSTRA API) ---

### 1. POST /soccorso (Creazione di una nuova richiesta)
@app.route('/soccorso', methods=['POST'])  # Definisce l'URL e accetta solo richieste di tipo POST
def crea_richiesta_soccorso():  
    try:  
        data = request.json  # Estrae il corpo della richiesta in formato JSON (i dati dell'utente)
        if not data:  # Se l'utente non ha inviato nulla...
            return jsonify({"error": "Corpo della richiesta mancante"}), 400  # ...restituisce errore 400 (Bad Request)
        
        # Estrazione dei dati: se mancano nome o cognome, imposta "Sconosciuto" di default
        nome = data.get('nome', "Sconosciuto")
        cognome = data.get('cognome', "Sconosciuto")
        targa_veicolo = data.get('targa')  # Prende la targa
        descrizione_guasto = data.get('descrizione', "Richiesta soccorso stradale")  # Prende i dettagli del guasto
        
        # 1. Recuperiamo lat e lon inviate dall'utente (arrivano come testo/stringhe)
        lat_str = data.get('lat')  
        lon_str = data.get('lon')  
        
        if not targa_veicolo:  # Controllo di sicurezza: la targa è obbligatoria per procedere
            return jsonify({"error": "La targa del veicolo è obbligatoria"}), 400  

        # 2. Convertiamo le stringhe in numeri decimali per renderle compatibili con le mappe
        try:
            lat = float(lat_str)  # Converte la latitudine in numero (es. da "45.4" a 45.4)
            lon = float(lon_str)  # Converte la longitudine in numero
        except (TypeError, ValueError):  # Se l'utente ha inserito lettere invece di numeri...
            return jsonify({"error": "Latitudine e longitudine devono essere numeri validi"}), 400
        
        # 3. Creiamo la struttura dati (Dizionario) esatta che MongoDB si aspetta
        nuovo_soccorso_mongo = {  
            "nome": nome,  # Salva il nome
            "cognome": cognome,  # Salva il cognome
            "targa": targa_veicolo,  # Salva la targa
            # GeoJSON: standard internazionale per la geolocalizzazione
            "posizione": {
                "type": "Point",  # Specifica che stiamo salvando un singolo punto sulla mappa
                "coordinates": [lon, lat]  # ATTENZIONE: per standard, prima va la longitudine e poi la latitudine
            },
            "stato": "Richiesto",  # Imposta lo stato iniziale dell'intervento
            "dettagli": descrizione_guasto,  # Salva i dettagli del problema
            "data_richiesta": datetime.utcnow()  # Registra l'ora esatta universale (UTC)
        }
        
        # Inserisce fisicamente il documento nella collezione "Sinistro" del database
        result_mongo = mongo_db.Sinistro.insert_one(nuovo_soccorso_mongo)  
        mongo_id = str(result_mongo.inserted_id)  # Prende l'ID univoco appena generato e lo converte in testo
        
        # Risponde al client comunicando il successo e l'ID dell'intervento
        return jsonify({  
            "message": "Soccorso registrato con successo",
            "intervento_id": mongo_id,
            "database_utilizzato": DB_NAME,
            "stato": "Richiesto"
        }), 201  # Restituisce 201 (Created)
    
    except pymongo.errors.PyMongoError as e:  # Cattura errori specifici del database
        return jsonify({"error": f"Errore Database MongoDB: {str(e)}"}), 500  
    except Exception as e:  # Cattura qualsiasi altro errore imprevisto
        return jsonify({"error": f"Errore generico: {str(e)}"}), 500  


### 2. GET /soccorso/<identificatore> (Ricerca rapida singola)
@app.route('/soccorso/<string:identificatore>', methods=['GET'])  # Accetta un parametro variabile nell'URL
def get_dettaglio_soccorso(identificatore):  
    try:  
        if ObjectId.is_valid(identificatore):  # Se l'identificatore ha il formato di un ID MongoDB (24 caratteri)...
            mongo_data = mongo_db.Sinistro.find_one({"_id": ObjectId(identificatore)})  # ...cerca esattamente per quell'ID
        else:  # Altrimenti, assume che l'identificatore sia una targa
            mongo_data = mongo_db.Sinistro.find_one(  
                {"targa": identificatore},  # Cerca la targa
                sort=[("data_richiesta", -1)]  # Prende solo l'ultimo intervento in ordine di tempo (-1 = decrescente)
            )
        
        if not mongo_data:  # Se la ricerca non ha prodotto risultati...
            return jsonify({"error": "Nessun intervento trovato"}), 404  # ...restituisce 404 (Not Found)
        
        mongo_data['_id'] = str(mongo_data['_id'])  # Converte l'ObjectId in stringa per poterlo stampare nel JSON
        
        return jsonify({"soccorso_info": mongo_data}), 200  # Restituisce i dati trovati con codice 200 (OK)
    
    except Exception as e:  
        return jsonify({"error": f"Errore nel recupero dati: {str(e)}"}), 500  


### 3. GET /soccorsi/ricerca (Nuova funzione per operatori: Cronologia e Filtri)
@app.route('/soccorsi/ricerca', methods=['GET'])  # Rotta per le ricerche avanzate
def ricerca_cronologia_soccorsi():
    try:
        # Legge i parametri opzionali passati nell'URL (es: ?nome=Mario)
        nome = request.args.get('nome')
        cognome = request.args.get('cognome')
        targa = request.args.get('targa')

        # Dizionario vuoto che si riempirà man mano in base a cosa cerca l'operatore
        query = {}
        
        # Se c'è un nome, usa $regex (espressione regolare) per cercarlo anche in parte (es: "Mar" trova "Mario")
        # $options: 'i' serve a ignorare le maiuscole/minuscole (Case Insensitive)
        if nome:
            query['nome'] = {'$regex': nome, '$options': 'i'}
        if cognome:
            query['cognome'] = {'$regex': cognome, '$options': 'i'}
        if targa:
            query['targa'] = {'$regex': targa, '$options': 'i'}

        if not query:  # Blocca la ricerca se non è stato inserito nessun filtro
            return jsonify({"error": "Fornire almeno un parametro di ricerca (?nome=... o ?cognome=... o ?targa=...)"}), 400

        # Esegue la ricerca con i filtri creati e ordina tutto per data decrescente (dal più nuovo al più vecchio)
        cursor = mongo_db.Sinistro.find(query).sort("data_richiesta", -1)
        risultati = list(cursor)  # Converte i risultati trovati (Cursor) in una lista Python leggibile

        if not risultati:  # Se la lista è vuota (nessun soccorso passato)...
            return jsonify({
                "message": "Nessun soccorso trovato per i criteri inseriti", 
                "storico_incidenti": []  # Restituisce una lista vuota
            }), 200

        # Ciclo for per sistemare tutti i risultati: trasforma ogni ObjectId in una stringa normale
        for res in risultati:
            res['_id'] = str(res['_id'])

        # Restituisce all'operatore quanti interventi ha trovato e l'intera cronologia
        return jsonify({
            "message": f"Trovati {len(risultati)} interventi",
            "storico_incidenti": risultati
        }), 200

    except Exception as e:
        return jsonify({"error": f"Errore durante la ricerca: {str(e)}"}), 500

# Se il file viene avviato direttamente, accende il server di sviluppo Flask sulla porta 5000
if __name__ == '__main__':  
    app.run(debug=True, host='0.0.0.0', port=5000)