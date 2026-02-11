"""

import mysql.connector
from mysql.connector import Error
from pymongo import MongoClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

mysql_config = {
    "host": "mysql-safeclaim.aevorastudios.com",
    "port": 3306,
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db"
}

mongo_uri = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"

class PraticaSchema(BaseModel):
    codice_pratica: str

class RimborsoSchema(BaseModel):
    importo: float

class InterventoSchema(BaseModel):
    tipo_intervento: str
    descrizione: str
    costo_stimato: float

@app.post("/sinistro/{sinistro_id}/perito/{perito_id}/pratica")
def crea_pratica(sinistro_id: str, perito_id: int, data: PraticaSchema):
    db_mysql = None
    try:
        db_mysql = mysql.connector.connect(**mysql_config)
        cursor = db_mysql.cursor()
        query = "INSERT INTO Pratica (codice_pratica, sinistro_id, perito_id) VALUES (%s, %s, %s)"
        cursor.execute(query, (data.codice_pratica, sinistro_id, perito_id))
        db_mysql.commit()
        return {"status": "success", "id_pratica": cursor.lastrowid}
    except Error as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if db_mysql and db_mysql.is_connected():
            cursor.close()
            db_mysql.close()

@app.post("/sinistro/{sinistro_id}/perito/{perito_id}/pratica/{pratica_id}/rimborso")
def crea_rimborso(sinistro_id: str, perito_id: int, pratica_id: int, data: RimborsoSchema):
    db_mysql = None
    try:
        db_mysql = mysql.connector.connect(**mysql_config)
        cursor = db_mysql.cursor()
        query = "INSERT INTO Rimborso (pratica_id, importo) VALUES (%s, %s)"
        cursor.execute(query, (pratica_id, data.importo))
        db_mysql.commit()
        return {"status": "success", "id_rimborso": cursor.lastrowid}
    except Error as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if db_mysql and db_mysql.is_connected():
            cursor.close()
            db_mysql.close()

@app.post("/sinistro/{sinistro_id}/perito/{perito_id}/pratica/{pratica_id}/intervento")
def crea_intervento(sinistro_id: str, perito_id: int, pratica_id: int, data: InterventoSchema):
    db_mysql = None
    try:
        db_mysql = mysql.connector.connect(**mysql_config)
        cursor = db_mysql.cursor()
        query = "INSERT INTO Intervento (pratica_id, tipo_intervento, descrizione, costo_stimato) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (pratica_id, data.tipo_intervento, data.descrizione, data.costo_stimato))
        db_mysql.commit()
        return {"status": "success", "id_intervento": cursor.lastrowid}
    except Error as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if db_mysql and db_mysql.is_connected():
            cursor.close()
            db_mysql.close()
            
"""