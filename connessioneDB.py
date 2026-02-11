import mysql.connector
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# --- PARAMETRI REMOTI ---
MYSQL_CONFIG = {
    'host': "mysql-safeclaim.aevorastudios.com",
    'port': 3306,
    'user': "safeclaim",
    'password': "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    'database': "safeclaim_db"
}

MONGO_URI = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
MONGO_DB_NAME = "safeclaim_mongo"

try:
    # 1. Connessione a MySQL Remoto
    print("Tentativo di connessione a MySQL Remoto...")
    mydb = mysql.connector.connect(**MYSQL_CONFIG)
    mycursor = mydb.cursor()
    print(f"Connessione a MySQL riuscita! Database: {MYSQL_CONFIG['database']}")

    # Esempio rapido: conta quante tabelle ci sono nel DB remoto
    mycursor.execute("SHOW TABLES")
    tabelle = mycursor.fetchall()
    print(f"Tabelle trovate nel DB MySQL: {len(tabelle)}")

    # 2. Connessione a MongoDB Remoto
    print("\nTentativo di connessione a MongoDB Remoto...")
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongodb = mongo_client[MONGO_DB_NAME]
    
    # Verifica effettiva della connessione
    mongo_client.admin.command('ping')
    print(f"Connessione a MongoDB riuscita! Database: {MONGO_DB_NAME}")

    # Ora puoi operare sui DB (es. mongodb.collezione.find())

except mysql.connector.Error as err:
    print(f"ERRORE MYSQL: {err}")
except ConnectionFailure:
    print("ERRORE MONGODB: Timeout o errore di connessione")
except Exception as e:
    print(f"ERRORE GENERICO: {e}")

finally:
    # Chiusura connessioni se aperte
    if 'mydb' in locals() and mydb.is_connected():
        mycursor.close()
        mydb.close()
        print("\nConnessione MySQL chiusa.")
    
    if 'mongo_client' in locals():
        mongo_client.close()
        print("Connessione MongoDB chiusa.")