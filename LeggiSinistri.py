from pymongo import MongoClient

# Ci colleghiamo al database MongoDB 
MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
client = MongoClient(MONGO_URI) # Creiamo il 'client', ovvero il postino che porterà i nostri messaggi al database.
db = client['safeclaim_mongo'] # Scegliamo il database specifico su cui lavorare: 'safeclaim_mongo'.
sinistri_col = db['sinistri'] # Selezioniamo la collezione 'sinistri' all'interno del database, e li salviamo 
# Recuperiamo tutti i documenti, usiamo il comando .find() per dire a 'sinistri_col': "Prendimi tutto quello che hai dentro".
tutti_i_sinistri = sinistri_col.find()

print("--- ELENCO SINISTRI NEL DATABASE ---")
# Visto che i sinistri possono essere tanti, usiamo un ciclo 'for' per leggerli uno alla volta.
for s in tutti_i_sinistri:
    print(f"ID: {s['_id']} | Targa: {s['targa']} | Stato: {s['stato']}")