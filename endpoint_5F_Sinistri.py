from flask import Flask, request, jsonify
import pymysql
import pymongo
from datetime import datetime
from bson import ObjectId
from urllib.parse import quote_plus

app = Flask(__name__)

# --- CONFIGURAZIONE UNIFICATA ---

# MySQL
mysql_config = {
    'host': 'mysql-safeclaim.aevorastudios.com',
    'port': 3306,
    'user': 'safeclaim',
    'password': '0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
    'database': 'safeclaim_db',
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 10
}

# MongoDB
mongo_uri = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
mongo_client = pymongo.MongoClient(mongo_uri)
mongo_db = mongo_client["safeclaim_mongo"]
sinistri_col = mongo_db['sinistri'] # Collezione principale sinistri

def get_db_connection():
    return pymysql.connect(**mysql_config)

# --- UTILS ---
def serializza_mongo(doc):
    """Converte ObjectId e Datetime in formati JSON serializzabili"""
    if not doc: return None
    doc['_id'] = str(doc['_id'])
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc

# --- ENDPOINTS SOCCORSO ---
@app.route('/soccorso', methods=['POST'])
def crea_richiesta_soccorso():
    data = request.json
    targa = data.get('targa')
    if not targa:
        return jsonify({"error": "La targa è obbligatoria"}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 1. Verifica Veicolo su MySQL
            cursor.execute("SELECT id FROM Veicolo WHERE targa = %s", (targa,))
            veicolo = cursor.fetchone()
            if not veicolo:
                return jsonify({"error": "Veicolo non censito"}), 404

            # 2. Inserimento su MongoDB (Collezione Sinistro/Soccorso)
            nuovo_soccorso = {
                "veicolo_id": veicolo['id'],
                "targa": targa,
                "posizione": {"lat": data.get('lat'), "lon": data.get('lon')},
                "stato": "RICHIESTO",
                "tipo": "SOCCORSO_STRADALE",
                "dettagli": data.get('descrizione', ""),
                "data_inserimento": datetime.utcnow()
            }
            res = sinistri_col.insert_one(nuovo_soccorso)
            mongo_id = str(res.inserted_id)

            # 3. Log su MySQL
            sql = "INSERT INTO Documenti_Anagrafica (entita_tipo, entita_id, mongo_doc_id, tipo_documento) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, ('soccorso', veicolo['id'], mongo_id, 'intervento_stradale'))
            connection.commit()

            return jsonify({"status": "success", "id": mongo_id}), 201
    except Exception as e:
        if connection: connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if connection: connection.close()

@app.route('/soccorso/<string:identificatore>', methods=['GET'])
def get_dettaglio_soccorso(identificatore):
    connection = None
    try:
        # A. Ricerca su MongoDB
        if ObjectId.is_valid(identificatore):
            mongo_data = sinistri_col.find_one({"_id": ObjectId(identificatore)})
        else:
            # Se non è un ID valido, cerchiamo per targa prendendo l'ultimo
            mongo_data = sinistri_col.find_one(
                {"targa": identificatore}, 
                sort=[("data_inserimento", -1)]
            )
        
        if not mongo_data:
            return jsonify({"error": "Intervento non trovato"}), 404
        
        # B. Arricchimento dati da MySQL
        veicolo_data = None
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                # Usiamo l'ID veicolo salvato nel documento Mongo
                sql = "SELECT targa, marca, modello, anno_immatricolazione FROM Veicolo WHERE id = %s"
                cursor.execute(sql, (mongo_data.get('veicolo_id'),))
                veicolo_data = cursor.fetchone()
        except Exception:
            veicolo_data = "Errore connessione MySQL"
        finally:
            if connection: connection.close()

        return jsonify({
            "soccorso_info": serializza_mongo(mongo_data),
            "veicolo_certificato": veicolo_data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ENDPOINTS GESTIONE SINISTRI ---
@app.route('/sinistro', methods=['POST'])
def apri_sinistro():
    data = request.json
    required = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    if not all(k in data for k in required):
        return jsonify({"error": "Dati incompleti"}), 400

    try:
        nuovo_sinistro = {
            **data,
            "stato": "APERTO",
            "immagini": [],
            "data_inserimento": datetime.utcnow()
        }
        risultato = sinistri_col.insert_one(nuovo_sinistro)
        return jsonify({"status": "success", "mongo_id": str(risultato.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sinistro/<id>/immagini', methods=['POST'])
def aggiungi_immagine(id):
    data = request.json
    if 'immagine_base64' not in data:
        return jsonify({"error": "Immagine mancante"}), 400

    try:
        res = sinistri_col.update_one(
            {"_id": ObjectId(id)},
            {"$push": {"immagini": data['immagine_base64']}}
        )
        if res.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ENDPOINTS RICERCA (INTEGRATI) ---

@app.route('/sinistri', methods=['GET'])
@app.route('/sinistri/<id_sinistro>', methods=['GET'])
def ottieni_sinistri(id_sinistro=None):
    try:
        if id_sinistro:
            # Dettaglio singolo con arricchimento dati veicolo da MySQL
            doc = sinistri_col.find_one({"_id": ObjectId(id_sinistro)})
            if not doc: return jsonify({"error": "Non trovato"}), 404
            
            serializzato = serializza_mongo(doc)
            
            # Arricchimento opzionale da MySQL
            try:
                conn = get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM Veicolo WHERE targa = %s", (doc['targa'],))
                    serializzato['veicolo_dettagli'] = cursor.fetchone()
                conn.close()
            except: pass # Se MySQL fallisce, restituiamo comunque i dati Mongo
            
            return jsonify(serializzato), 200
        else:
            # Lista completa
            cursor = sinistri_col.find().sort("data_inserimento", -1)
            lista = [serializza_mongo(d) for d in cursor]
            return jsonify({"count": len(lista), "data": lista}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)