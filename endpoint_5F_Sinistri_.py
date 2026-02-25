from flask import Flask, request, jsonify
from datetime import datetime
import mysql.connector
import pymongo
from bson.objectid import ObjectId

app = Flask(__name__)

# ==========================================================
# CONFIGURAZIONE DATABASE
# ==========================================================

# ---------- MySQL (Dati strutturati) ----------
mysql_config = {
    'host': 'mysql-safeclaim.aevorastudios.com',
    'port': 3306,
    'user': 'safeclaim',
    'password': '0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
    'database': 'safeclaim_db',
    'connect_timeout': 10
}

def get_db_connection():
    return mysql.connector.connect(**mysql_config)


# ---------- MongoDB (Sinistri, GPS, Immagini) ----------
MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
mongo_client = pymongo.MongoClient(MONGO_URI)
mongo_db = mongo_client["safeclaim_mongo"]

sinistri_col = mongo_db["sinistri"]
soccorso_col = mongo_db["Sinistro"]


# ==========================================================
# 1️⃣  SINISTRI - CREAZIONE
# ==========================================================

@app.route('/sinistro', methods=['POST'])
def apri_sinistro():
    data = request.json

    required_fields = ['automobilista_id', 'targa', 'data_evento', 'descrizione']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Campo mancante: {field}"}), 400

    try:
        nuovo_sinistro = {
            "automobilista_id": data['automobilista_id'],
            "targa": data['targa'],
            "data_evento": data['data_evento'],
            "descrizione": data['descrizione'],
            "stato": "APERTO",
            "data_inserimento": datetime.utcnow()
        }

        result = sinistri_col.insert_one(nuovo_sinistro)

        return jsonify({
            "status": "success",
            "mongo_id": str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================================
# 2️⃣  CARICAMENTO IMMAGINE SU SINISTRO SPECIFICO
# ==========================================================

@app.route('/sinistro/<id>/immagini', methods=['POST'])
def aggiungi_immagine(id):
    data = request.json

    if not data or 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        result = sinistri_col.update_one(
            {"_id": ObjectId(id)},
            {"$push": {"immagini": data['immagine_base64']}}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Sinistro non trovato"}), 404

        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================================
# 3️⃣  CARICAMENTO IMMAGINE SU ULTIMO SINISTRO
# ==========================================================

@app.route('/sinistro/ultimo/immagini', methods=['POST'])
def aggiungi_immagine_ultimo():
    data = request.json

    if not data or 'immagine_base64' not in data:
        return jsonify({"error": "Dati immagine mancanti"}), 400

    try:
        ultimo = sinistri_col.find_one(sort=[("data_inserimento", -1)])

        if not ultimo:
            return jsonify({"error": "Nessun sinistro trovato"}), 404

        sinistri_col.update_one(
            {"_id": ultimo["_id"]},
            {"$push": {"immagini": data['immagine_base64']}}
        )

        return jsonify({
            "status": "success",
            "id_usato": str(ultimo["_id"])
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================================
# 4️⃣  GET SINISTRI (UNO O TUTTI)
# ==========================================================

@app.route('/sinistri', defaults={'id_sinistro': None}, methods=['GET'])
@app.route('/sinistri/<id_sinistro>', methods=['GET'])
def ottieni_sinistri(id_sinistro):
    try:
        if id_sinistro:
            sinistro = sinistri_col.find_one({"_id": ObjectId(id_sinistro)})
            if not sinistro:
                return jsonify({"error": "Sinistro non trovato"}), 404

            sinistro['_id'] = str(sinistro['_id'])
            if 'data_inserimento' in sinistro:
                sinistro['data_inserimento'] = sinistro['data_inserimento'].isoformat()

            return jsonify(sinistro), 200

        else:
            cursor = sinistri_col.find()
            lista = []

            for s in cursor:
                s['_id'] = str(s['_id'])
                if 'data_inserimento' in s:
                    s['data_inserimento'] = s['data_inserimento'].isoformat()
                lista.append(s)

            return jsonify({
                "count": len(lista),
                "data": lista
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================================
# 5️⃣  POST /SOCCORSO (MYSQL + MONGODB)
# ==========================================================

@app.route('/soccorso', methods=['POST'])
def crea_richiesta_soccorso():
    data = request.json

    if not data:
        return jsonify({"error": "Corpo richiesta mancante"}), 400

    targa = data.get('targa')
    descrizione = data.get('descrizione', "Richiesta soccorso")
    lat = data.get('lat')
    lon = data.get('lon')

    if not targa:
        return jsonify({"error": "Targa obbligatoria"}), 400

    connection = None

    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM Veicolo WHERE targa = %s", (targa,))
            veicolo = cursor.fetchone()

            if not veicolo:
                return jsonify({"error": "Veicolo non trovato"}), 404

            nuovo_soccorso = {
                "veicolo_id": veicolo['id'],
                "targa": targa,
                "posizione": {"lat": lat, "lon": lon},
                "stato": "Richiesto",
                "dettagli": descrizione,
                "data_richiesta": datetime.utcnow()
            }

            result = soccorso_col.insert_one(nuovo_soccorso)
            mongo_id = str(result.inserted_id)

            sql = """
                INSERT INTO Documenti_Anagrafica
                (entita_tipo, entita_id, mongo_doc_id, tipo_documento, descrizione)
                VALUES ('soccorso', %s, %s, 'intervento_stradale', %s)
            """
            cursor.execute(sql, (veicolo['id'], mongo_id, descrizione))

            connection.commit()

            return jsonify({
                "intervento_id": mongo_id,
                "stato": "In attesa"
            }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if connection:
            connection.close()


# ==========================================================
# 6️⃣  GET /SOCCORSO/<ID o TARGA>
# ==========================================================

@app.route('/soccorso/<string:identificatore>', methods=['GET'])
def get_dettaglio_soccorso(identificatore):

    connection = None

    try:
        if ObjectId.is_valid(identificatore):
            mongo_data = soccorso_col.find_one({"_id": ObjectId(identificatore)})
        else:
            mongo_data = soccorso_col.find_one(
                {"targa": identificatore},
                sort=[("data_richiesta", -1)]
            )

        if not mongo_data:
            return jsonify({"error": "Intervento non trovato"}), 404

        mongo_data['_id'] = str(mongo_data['_id'])

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT targa, marca, modello, anno_immatricolazione
                FROM Veicolo WHERE id = %s
            """, (mongo_data['veicolo_id'],))

            veicolo = cursor.fetchone()

        return jsonify({
            "soccorso_info": mongo_data,
            "veicolo_certificato": veicolo
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if connection:
            connection.close()


# ==========================================================
# AVVIO SERVER
# ==========================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6000)