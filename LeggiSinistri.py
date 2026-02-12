from pymongo import MongoClient

# Stringa di connessione
MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
client = MongoClient(MONGO_URI)
db = client['safeclaim_mongo']
sinistri_col = db['sinistri']

# Recuperiamo tutti i documenti
tutti_i_sinistri = sinistri_col.find()

print("--- ELENCO SINISTRI NEL DATABASE ---")
for s in tutti_i_sinistri:
    print(f"ID: {s['_id']} | Targa: {s['targa']} | Stato: {s['stato']}")