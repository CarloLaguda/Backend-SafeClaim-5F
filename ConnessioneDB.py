from pymongo import MongoClient
import mysql.connector
# Dati forniti
mongo_uri = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"

try:
    # Inizializzazione client
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    
    # Selezione del database
    db = client['safeclaim_mongo']
    
    # Test della connessione
    client.admin.command('ping')
    print("✅ Connessione a MongoDB riuscita!")
    
except Exception as e:
    print(f"❌ Errore di connessione a MongoDB: {e}")

import mysql.connector

config = {
    'user': 'safeclaim',
    'password': '0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
    'host': 'mysql-safeclaim.aevorastudios.com', # <--- Corretto qui
    'port': 3306,
    'database': 'safeclaim_db'
}

try:
    conn = mysql.connector.connect(**config)
    if conn.is_connected():
        print("✅ Connessione a MySQL riuscita!")
except Exception as e:
    print(f"❌ Errore di connessione a MySQL: {e}")