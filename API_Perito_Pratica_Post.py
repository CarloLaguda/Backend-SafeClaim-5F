import mysql.connector
from mysql.connector import Error
from pymongo import MongoClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Configurazione MySQL locale
mysql_config = {
    "host": "localhost",
    "user": "pythonuser",
    "password": "password123",
    "database": "Locale_DB"
}

# Configurazione MongoDB Remoto (dati dal tuo file)
mongo_uri = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+@mongo-safeclaim.aevorastudios.com:27017/"

class PraticaSchema(BaseModel):
    codice_pratica: str

@app.post("/sinistro/{sinistro_id}/perito/{perito_id}/pratica")
def crea_pratica(sinistro_id: str, perito_id: int, data: PraticaSchema):
    db_mysql = None
    client_mongo = None
    
    try:
        # Connessione MySQL
        db_mysql = mysql.connector.connect(**mysql_config)
        cursor = db_mysql.cursor()

        # Inserimento record Pratica
        query = "INSERT INTO Pratica (codice_pratica, sinistro_id, perito_id) VALUES (%s, %s, %s)"
        cursor.execute(query, (data.codice_pratica, sinistro_id, perito_id))
        db_mysql.commit()
        
        nuovo_id = cursor.lastrowid

        # Connessione MongoDB per verifica/operatività
        client_mongo = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client_mongo.admin.command('ping')
        
        return {
            "status": "success",
            "id_sql": nuovo_id,
            "sinistro_mongo": sinistro_id,
            "perito_sql": perito_id
        }

    except Error as e:
        raise HTTPException(status_code=400, detail=f"Errore DB Locale: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore Sistema/Mongo: {e}")
    
    finally:
        if db_mysql and db_mysql.is_connected():
            cursor.close()
            db_mysql.close()
        if client_mongo:
            client_mongo.close()