from fastapi import FastAPI, HTTPException, Body
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="SafeClaim API")

# --- Configurazione MongoDB ---
URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
client = MongoClient(URI)
db = client['safeclaim_mongo']
collection = db['pratiche'] 

class PraticaSchema(BaseModel):
    titolo: str
    descrizione: Optional[str] = None
    stato: str = "In lavorazione"
    note_perito: Optional[str] = None

# --- API Endpoints ---
@app.get("/sinistro/{sinistro_id}/perito/{perito_id}/pratica")
async def get_pratica(sinistro_id: str, perito_id: str):
    """
    Recupera i dettagli di una pratica filtrando per ID Sinistro e ID Perito.
    """
    query = {
        "sinistro_id": sinistro_id,
        "perito_id": perito_id
    }
    
    pratica = collection.find_one(query)
    
    if not pratica:
        raise HTTPException(status_code=404, detail="Pratica non trovata per i parametri forniti")
    
    pratica["_id"] = str(pratica["_id"])
    return pratica

@app.put("/sinistro/{sinistro_id}/perito/{perito_id}/pratica")
async def update_pratica(sinistro_id: str, perito_id: str, data: PraticaSchema = Body(...)):
    """
    Aggiorna o crea (upsert) la pratica associata al sinistro e al perito.
    """
    query = {
        "sinistro_id": sinistro_id,
        "perito_id": perito_id
    }
    
    
    update_data = {"$set": data.dict()}
    
    result = collection.update_one(query, update_data, upsert=True)
    
    if result.matched_count > 0:
        return {"message": "Pratica aggiornata con successo"}
    else:
        return {"message": "Nuova pratica creata e associata"}

# --- Avvio ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)