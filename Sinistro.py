import os  # Serve per creare cartelle e gestire i file sul PC
import pymongo  # Importa la libreria per gestire il database MongoDB
import requests  # Importa la libreria per inviare messaggi via internet (all'AI)
from flask import Flask, request, jsonify  # Importa i componenti per creare il server web
from flask_cors import CORS  # Importa il modulo per evitare i blocchi di sicurezza del browser
from datetime import datetime  # Importa la gestione di date e orari
from bson.objectid import ObjectId  # Importa il traduttore per gli ID speciali di MongoDB


app = Flask(__name__)  # Crea l'applicazione server SafeClaim
CORS(app)  # Permette a programmi esterni di parlare con questo server

# CONFIGURAZIONE MONGODB ATLAS
# Questa è la stringa segreta per connettersi al database nel cloud
CONNECTION_STRING = "mongodb+srv://dbFakeClaim:xxx123##@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
DB_NAME = "FakeClaim"  # Definisce il nome del database

try:
    # Prova a stabilire il contatto con il server di MongoDB Atlas
    #configura client con l'indirizzo giusto CONNECTION_STRING
    client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000) 
    #Se il database è offline, il tuo programma restituirà un errore dopo soli 5 secondi.
    
    # Seleziona il database 'FakeClaim'
    db = client[DB_NAME]
    # Seleziona la collezione (tabella) chiamata 'sinistri e la mette nella variabile sinistri_col'
    sinistri_col = db['sinistri']

    # Qui salveremo ogni ricerca effettuata per monitorare lo storico
    log_ricerche_col = db['log_ricerche'] #il LOG e' un registro cronologico di eventi
    
    # Chiede al database se è davvero attivo (test di connessione)
    client.server_info()  #è il metodo per verificare che la comunicazione sia effettivamente stabilita
    print("Connessione a MongoDB Atlas (FakeClaim) riuscita!") # Messaggio di successo
except Exception as e:
    # Se qualcosa non va, stampa l'errore e mette la collezione a None
    print(f"Errore critico di connessione al database: {e}")
    sinistri_col = None

# ROTTA 1: CREAZIONE DI UN NUOVO SINISTRO (POST) 
@app.route('/sinistro', methods=['POST']) # Definisce l'indirizzo per aprire una pratica
def apri_sinistro():
    # Se il database non è connesso, restituisce errore 503 (Servizio non disponibile)
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    # Prende i dati JSON inviati dall'utente e li mette in una variabile 'data'
    data = request.json
    
    # Lista dei campi obbligatori che l'utente deve inviare per aprire un sinistro
    required_fields = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    # Controlla uno per uno se i campi richiesti ci sono
    for field in required_fields:
        if field not in data:
            # Se manca un campo, risponde con errore 400 (Richiesta sbagliata)
            return jsonify({"error": f"Campo mancante: {field}"}), 400

    try:
        # Prepara lo schema del documento da salvare nel database
        nuovo_sinistro = {
            "automobilista_id": data['automobilista_id'], # ID del guidatore
            "targa": data['targa'], # Targa dell'auto
            "data_evento": data['data_evento'], # Data dell'incidente
            "descrizione": data['descrizione'], # Cosa è successo
            "stato": "APERTO", # Imposta lo stato iniziale della pratica
            "immagini": [], # Crea uno spazio vuoto per le foto future
            "data_inserimento": datetime.now() # Segna il momento esatto della registrazione
        }

        # Inserisce fisicamente il documento nella collezione 'sinistri'
        risultato = sinistri_col.insert_one(nuovo_sinistro)
        
        # Risponde all'utente confermando il salvataggio e inviando l'ID unico creato
        return jsonify({
            "status": "success",
            "message": "Sinistro salvato correttamente",
            "mongo_id": str(risultato.inserted_id) # Converte l'ID di MongoDB in testo
        }), 201
    except Exception as e:
        # Se c'è un errore imprevisto, restituisce errore 500
        return jsonify({"status": "error", "message": str(e)}), 500

#  ROTTA 2: AGGIUNTA IMMAGINE TRAMITE ID SPECIFICO (POST)
@app.route('/sinistro/<id>/immagini', methods=['POST']) # Definisce l'indirizzo per aggiungere un'immagine a un sinistro specifico (es: /sinistro/12345/immagini)
# Definiamo la funzione 'aggiungi_immagine' che accetta solo il nome dell'immagine da salvare e l'ID del sinistro a cui aggiungerla
def aggiungi_immagine(id):
    
    # Controllo se la connessione esiste (se MongoDB è spento)
    if sinistri_col is None:
        # Restituisce un errore 503 indicando che il servizio database non è pronto
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    # Legge il corpo della richiesta HTTP  e lo converte in un json e lo mette nella variabile 'data'
    data = request.json
    
    # Verifica che nel pacchetto dati ricevuto ci sia almeno il campo 'nome'
    if 'nome' not in data:
        # Se il nome manca, risponde con errore 400 (Bad Request) spiegando il motivo
        return jsonify({"error": "Dati mancanti: assicurati di inviare il 'nome'"}), 400

    try:
        # Prepariamo l'oggetto da inserire nella lista 'immagini' del sinistro, con il nome del file e la data di caricamento
        nuova_foto = {
            "nome_file": data['nome'],         # Qui inseriamo il nome del file (es. "macchina.jpg")
            "data_caricamento": datetime.now()  # Registriamo data e ora esatta del salvataggio
        }

        # Esegue l'aggiornamento nel database MongoDB
        # EseguE l'operazione e scrive in 'risultato' com'è andata
        risultato = sinistri_col.update_one( #update_one è il comando di MongoDB per modificare il documento esistente aggiungendo un nuovo elemento alla lista 'immagini'
            # Cerca il documento che ha l'ID univoco specificato (convertito in formato MongoDB ObjectId)
            {"_id": ObjectId(id)}, 
            
            # Usa $push per "spingere" il nuovo oggetto 'nuova_foto' dentro la lista 'immagini'
            # Se la lista è già piena, aggiunge in coda; se non esiste, la crea da zero.
            {"$push": {"immagini": nuova_foto}}
        )

        # Controllo post-operazione: verifichiamo se l'ID cercato esisteva davvero
        if risultato.matched_count == 0:
            # Se matched_count è 0, MongoDB non ha trovato nessun sinistro con quell'ID
            return jsonify({"error": "Sinistro non trovato"}), 404

        # Risposta finale di successo se tutto è andato a buon fine
        return jsonify({
            "status": "success", 
            "message": "Nome immagine salvato con successo!",
            "nome_inserito": data['nome'] # Confermiamo all'utente quale nome abbiamo registrato
        }), 200

    # Gestione delle eccezioni: se succede un imprevisto (es. ID scritto male o bug nel codice)
    except Exception as e:
        # Restituisce il dettaglio dell'errore tecnico con codice 500 (Errore interno del server)
        return jsonify({"status": "error", "message": str(e)}), 500

# ROTTA 3: RECUPERO SINISTRI (GET)
@app.route('/sinistri', defaults={'id_sinistro': None}, methods=['GET']) # Indirizzo per tutti i sinistri
@app.route('/sinistri/<id_sinistro>', methods=['GET']) # Indirizzo per un sinistro singolo
def ottieni_sinistri(id_sinistro):
    # Controllo connessione database
    if sinistri_col is None:
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    try: 
        # Se l'utente ha chiesto un ID specifico
        if id_sinistro:
            # Cerca nel DB solo quel sinistro
            sinistro = sinistri_col.find_one({"_id": ObjectId(id_sinistro)}) #sinistri_col sta per collezione
                                                                             # è la variabile che punta alla "scatola" dove sono salvati tutti i sinistri.
                                                                             #Se lo trova, lo mette nella variabile 'sinistro'.
            #find_one Filtra tutti i documenti in base ai criteri che metti tra parentesi.
            #Si ferma al primo: Appena trova un documento che soddisfa la ricerca, te lo restituisce e smette di cercare

            # Se non lo trova, risponde 404
            if not sinistro:
                return jsonify({"status": "error", "message": "Sinistro non trovato"}), 404
            
            # Converte l'ID in testo per il JSON
            sinistro['_id'] = str(sinistro['_id'])
            # Converte la data in formato leggibile ISO
            if 'data_inserimento' in sinistro:
                sinistro['data_inserimento'] = sinistro['data_inserimento'].isoformat() 
                #isoformat è un metodo che trasforma la data in una stringa standard, 
                #Quando vuoi inviare questi dati a una pagina web tramite JSON, il formato JSON non sa cosa sia una data: lui capisce solo il testo.
                #Se non usassi .isoformat(), il tuo programma darebbe errore perché non saprebbe come "impacchettare" la data per spedirla.
                #ESEMPIO: datetime(2024, 6, 1, 12, 0, 0) diventa "2024-06-01T12:00:00" a
                #"2024-06-01T12:00:00", che è facile da leggere e usare nei programmi.
            
            # Invia i dati del sinistro trovato
            return jsonify({"status": "success", "data": sinistro}), 200
        
        # Se l'utente non ha messo ID, vuole tutta la lista
        else:
            # Prende tutti i documenti nella collezione
            cursor = sinistri_col.find() 
            lista_sinistri = [] # Crea una lista vuota dove metterli
            for s in cursor:
                # Per ogni elemento, converte ID e Data
                s['_id'] = str(s['_id'])
                if 'data_inserimento' in s:
                    s['data_inserimento'] = s['data_inserimento'].isoformat()
                # Aggiunge il sinistro sistemato alla lista finale
                lista_sinistri.append(s) # Aggiunge il sinistro sistemato alla lista finale
            
            # Invia tutta la lista dei sinistri
            return jsonify({
                "status": "success",
                "count": len(lista_sinistri), # Dice quanti ne ha trovati nella lista
                                              # len Serve a contare quanti elementi ci sono dentro una lista.
                "data": lista_sinistri
            }), 200
    except Exception as e:
        # Invia l'errore se qualcosa fallisce nel recupero dati
        return jsonify({"status": "error", "message": str(e)}), 500

# Definisce l'indirizzo (endpoint) per cercare i sinistri filtrando solo per targa
@app.route('/sinistri/ricerca/targa', methods=['GET'])
def ricerca_per_targa():
    # Verifica se la connessione al database MongoDB è funzionante
    if sinistri_col is None:
        # Se il database è offline, risponde con errore 503
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    # Recupera il valore della targa dall'URL (es: /targa?valore=AB123CD)
    targa_da_cercare = request.args.get('valore') #request.args.get è il modo per leggere i parametri che l'utente mette dopo il punto interrogativo nell'indirizzo.

    # Controlla se l'utente ha effettivamente scritto qualcosa come targa
    if not targa_da_cercare:
        # Se il parametro è vuoto, risponde con errore 400
        return jsonify({"error": "Inserire una targa per effettuare la ricerca"}), 400

    try:
        # dice a MongoDB di trovare tutti i documenti con quella targa 
        query = {"targa": targa_da_cercare} # La targa è il campo del documento che vogliamo filtrare, e targa_da_cercare è il valore che l'utente ha scritto.
        
        # Esegue la ricerca find() restituirà TUTTI i sinistri di quella targa
        cursor = sinistri_col.find(query) # La funzione find() è il comando di MongoDB che dice: "Vai a cercare tutti i documenti che soddisfano questo criterio (query) e restituiceli".
        
        
        # Prepara la lista vuota per contenere i risultati
        risultati = []
        
        # Esplora i risultati trovati nel database
        for s in cursor:
            # Converte l'ID tecnico di MongoDB in una stringa leggibile
            s['_id'] = str(s['_id'])
            
            # Se esiste la data di inserimento, la trasforma in formato testo ISO per poterla inviare via JSON
            if 'data_inserimento' in s:
                s['data_inserimento'] = s['data_inserimento'].isoformat()
            
            # Aggiunge il sinistro sistemato alla lista dei risultati
            risultati.append(s)

        #  Salviamo il la ricerca effettuata 
        # Ogni volta che qualcuno cerca una targa, aggiorniamo il log delle ricerche per quella targa specifica. 
        # Se è la prima volta che viene cercata, creiamo un nuovo record; se è già stata cercata, aggiorniamo il numero di ricerche e l'ultima data di ricerca.
        log_ricerche_col.update_one( #update_one è il comando di MongoDB che dice: 
        #"Cerca un documento che soddisfa questo criterio, e se lo trovi, aggiornalo così; se non lo trovi, creane uno nuovo con questi dati"
            {"targa_cercata": targa_da_cercare}, # Cerca se esiste già un log per questa targa
            {
                "$set": { "data_ultima_ricerca": datetime.now() }, # Sovrascrive l'orario con quello dell'ultimo click
                #set sovrascrive questo campo con il nuovo valore. In questo caso, aggiorna sempre la data dell'ultima ricerca.
                "$inc": { "numero_totale_ricerche": 1 },          # Incrementa di +1 il contatore delle ricerche fatte
                #inc Incrementa il campo numerico di questa quantità. Ogni volta che qualcuno cerca quella targa, aggiunge +1 al contatore totale delle ricerche.
                "$setOnInsert": { "tipo_ricerca": "targa" }       # Imposta il tipo di ricerca solo se il documento viene creato da zero
                #setOnInsert dice: Se devi creare un nuovo documento perché non ne esiste uno con questa targa, allora imposta questo campo con questo valore". 
                #In questo caso, se è la prima volta che viene cercata quella targa, crea un nuovo record e imposta il campo "tipo_ricerca" a "targa". 
                #Se invece il record esiste già, non tocca quel campo.
            },
            upsert=True # Se la targa non è mai stata cercata, crea un nuovo record; se esiste, lo aggiorna
            #upsert dice che "Se non trovi un documento che soddisfa il criterio, allora creane uno nuovo con questi dati".
        )

        # Invia la risposta finale al client 
        return jsonify({
            "status": "success",
            "targa_cercata": targa_da_cercare,
            "numero_sinistri": len(risultati), # Conta quanti incidenti ha fatto quell'auto
            "data": risultati
        }), 200

    # Gestisce eventuali errori improvvisi del server o del database
    except Exception as e:
        # Restituisce il dettaglio dell'errore con codice 500
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ROTTA 5: STORICO DELLE RICERCHE PER UNA TARGA 
@app.route('/sinistri/ricerca/targa/storico', methods=['GET'])
def visualizza_storico_targa():
    # Controlla se la connessione alla collezione 'log_ricerche' su MongoDB è attiva
    if log_ricerche_col is None:
        # Se il database non risponde, restituisce un errore 503 (Servizio Non Disponibile)
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    # Recupera il valore della targa dai parametri dell'URL (es. /storico?valore=ABC)
    targa_da_controllare = request.args.get('valore')

    # Se l'utente non ha inserito nessuna targa nella richiesta, blocca tutto
    if not targa_da_controllare:
        # Restituisce un errore 400 (Bad Request) chiedendo di specificare la targa
        return jsonify({"error": "Specificare una targa"}), 400

    try:
        # Cerca nel database UN SOLO documento (il record riassuntivo) per quella specifica targa
        # Usiamo find_one perché con la nuova logica ogni targa ha un'unica riga che si aggiorna
        log = log_ricerche_col.find_one({"targa_cercata": targa_da_controllare}) 

        # Se il documento esiste (ovvero se quella targa è stata cercata almeno una volta)
        if log:
            # Converte l'ID di MongoDB (che è un oggetto speciale) in una stringa leggibile
            log['_id'] = str(log['_id'])

            # Controlla se nel record è presente la data dell'ultima ricerca
            if 'data_ultima_ricerca' in log:
                # Trasforma la data da formato Python a formato testo ISO (standard per il JSON)
                log['data_ultima_ricerca'] = log['data_ultima_ricerca'].isoformat()

            # Restituisce il risultato all'utente con lo stato 200 (OK)
            return jsonify({"status": "success", "dati_ricerca": log}), 200

        # Se find_one non ha trovato nulla, significa che la targa non è mai stata cercata prima
        return jsonify({"status": "error", "message": "Nessuna ricerca trovata"}), 404

    except Exception as e:
        # In caso di errori imprevisti (es. crash del server), restituisce il messaggio d'errore
        return jsonify({"status": "error", "message": str(e)}), 500

# Definisce l'indirizzo che useremo cercare i sinistri di un automobilista specifico
@app.route('/sinistri/ricerca/automobilista', methods=['GET'])
def ricerca_per_automobilista():
    # Controlla che il server sia effettivamente connesso a MongoDB 
    if sinistri_col is None:
        # Se non c'è connessione, restituisce un errore 503 (Servizio non disponibile)
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    # Legge il valore dopo il punto di domanda nell'URL (es: ...?nome=LUCA-VERDI)
    # request.args.get('nome') cerca proprio la parola 'nome' nella stringa dell'indirizzo
    nome_cercato = request.args.get('nome') #nome_cercato è la variabile che conterrà il valore che l'utente ha scritto dopo nome= nell'indirizzo.

    # Verifica se l'utente ha dimenticato di scrivere il nome nell'URL
    if not nome_cercato:
        # Se il nome è vuoto, restituisce errore 400 (Richiesta errata)
        return jsonify({"error": "Inserire un nome per la ricerca"}), 400

    try:
        # Prepara il filtro per MongoDB: "Cerca tutti i documenti dove il campo automobilista_id è uguale a nome_cercato"
        query = {"automobilista_id": nome_cercato}
        
        # Esegue la ricerca nella collezione. .find() ci restituisce un "cursore" per scorrere i risultati trovati
        cursor = sinistri_col.find(query)
        
        # Crea una lista vuota dove salveremo i sinistri trovati dal database
        risultati = []
        
        # Inizia a scorrere tutti i documenti trovati dal database uno per uno
        for s in cursor:
            # Trasforma l'ID speciale di MongoDB (_id) in una stringa di testo semplice
            # Questo è obbligatorio perché il formato JSON non accetta gli "ObjectId" nativi di MongoDB
            s['_id'] = str(s['_id'])
            
            # Controlla se il documento ha una data di registrazione
            if 'data_inserimento' in s:
                # Trasforma l'oggetto Data in una stringa di testo (formato ISO)
                # Serve a evitare che il server crashi quando prova a inviare la risposta
                s['data_inserimento'] = s['data_inserimento'].isoformat()
            
            # Aggiunge il sinistro sistemato alla nostra lista dei risultati
            risultati.append(s)
 
        # Ogni volta che qualcuno cerca un automobilista, aggiorniamo il log delle ricerche per quello specifico automobilista. 
        # Se è la prima volta che viene cercato, creiamo un nuovo record; se è già stato cercato, aggiorniamo il numero di ricerche e l'ultima data di ricerca.
        log_ricerche_col.update_one( #update_one è il comando di MongoDB che dice: 
        #"Cerca un documento che soddisfa questo criterio, e se lo trovi, aggiornalo così; se non lo trovi, creane uno nuovo con questi dati"
            {"nome_cercato": nome_cercato}, # Cerca se esiste già un log per questo automobilista
            {
                "$set": { "data_ultima_ricerca": datetime.now() }, # Aggiorna la data all'ultima ricerca effettuata e l'ora esatta
                # set è un operatore di MongoDB che dice: "Sovrascrivi questo campo con questo nuovo valore". In questo caso, aggiorna sempre la data dell'ultima ricerca.
                "$inc": { "numero_totale_ricerche": 1 },          # Aggiunge 1 al totale delle ricerche per questo nome e lo aggiorna nel database
                #inc Incrementa questo campo numerico di questa quantità. Ogni volta che qualcuno cerca quel nome, aggiunge +1 al contatore totale delle ricerche.
                "$setOnInsert": { "tipo_ricerca": "automobilista" }   # Imposta il tipo di ricerca solo se il documento viene creato da zero
                #setOnInsert dice: Se devi creare un nuovo documento perché non ne esiste uno con questo nome, allora imposta questo campo con questo valore". 
                #In questo caso, se è la prima volta che viene cercato quel nome, crea un nuovo record e imposta il campo "tipo_ricerca" a "automobilista". 
                #Se invece il record esiste già, non tocca quel campo.
            },
            upsert=True # Crea il record se non esiste, altrimenti aggiorna quello esistente
            #upsert dice che "Se non trovi un documento che soddisfa il criterio, allora creane uno nuovo con questi dati".
        )

        # Invia la risposta finale con lo stato di successo e la lista dei sinistri trovati
        return jsonify({
            "status": "success",
            "automobilista_id": nome_cercato,
            "numero_sinistri": len(risultati), # Conta quanti elementi ci sono nella lista
            "data": risultati                  # La lista effettiva dei sinistri
        }), 200 # Codice 200: Tutto OK

    # Se succede un errore imprevisto durante la comunicazione con il database
    except Exception as e:
        # Restituisce l'errore tecnico con codice 500 (Errore interno del server)
        return jsonify({"status": "error", "message": str(e)}), 500

# --- NUOVA ROTTA: STORICO RICERCHE PER NOME ---

# Definiamo l'indirizzo (endpoint) per consultare quante volte un guidatore è stato cercato
@app.route('/sinistri/ricerca/automobilista/storico', methods=['GET'])
def visualizza_storico_nome():
    # Verifica se la connessione alla collezione 'log_ricerche' nel database è attiva
    if log_ricerche_col is None:
        # Se non c'è connessione, restituisce un errore 503 (Servizio Non Disponibile)
        return jsonify({"status": "error", "message": "Database non disponibile"}), 503

    # Estrae il nome dell'automobilista dai parametri della richiesta (es. ?nome=MarioRossi)
    nome_da_controllare = request.args.get('nome')

    # Controlla se il parametro 'nome' è stato effettivamente inviato dall'utente
    if not nome_da_controllare:
        # Se il nome manca, restituisce un errore 400 (Richiesta errata)
        return jsonify({"error": "Specificare un nome"}), 400

    try:
        # Cerca nel database il documento unico associato a quel nome specifico
        # Con la logica 'update_one', troverà un solo record che contiene il totale delle ricerche
        log = log_ricerche_col.find_one({"nome_cercato": nome_da_controllare})

        # Se il record esiste (ovvero se quel nome è stato cercato almeno una volta)
        if log:
            # Trasforma l'ID tecnico di MongoDB in una stringa di testo semplice per il JSON
            log['_id'] = str(log['_id']) 

            # Verifica se nel record è presente il campo della data dell'ultimo click
            if 'data_ultima_ricerca' in log:
                # Converte la data dal formato database al formato testo ISO leggibile
                log['data_ultima_ricerca'] = log['data_ultima_ricerca'].isoformat()

            # Invia all'utente i dati trovati con successo (Stato 200 OK)
            return jsonify({"status": "success", "dati_ricerca": log}), 200

        # Se il nome non compare mai nel database dei log, informa l'utente
        return jsonify({"status": "error", "message": "Nessuna ricerca trovata"}), 404

    except Exception as e:
        # Gestisce eventuali errori improvvisi del codice restituendo il dettaglio dell'errore
        return jsonify({"status": "error", "message": str(e)}), 500

# AVVIO DEL SERVER 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)