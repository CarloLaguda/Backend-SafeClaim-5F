import mysql.connector
from pymongo import MongoClient

# =========================
# CONFIGURAZIONE MYSQL
# =========================
MYSQL_CONFIG = {
    "host": "mysql-safeclaim.aevorastudios.com",
    "port": 3306,
    "user": "safeclaim",
    "password": "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
    "database": "safeclaim_db" # Assicurati che questo database esista
}

# =========================
# CONFIGURAZIONE MONGODB
# =========================
MONGO_URI = (
    "mongodb://safeclaim:"
    "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D"
    "@mongo-safeclaim.aevorastudios.com:27017/"
)
MONGO_DB_NAME = "safeclaim_mongo"

try:
    # =========================
    # CONNESSIONE MYSQL
    # =========================
    mydb = mysql.connector.connect(
        host=MYSQL_CONFIG["host"],
        port=MYSQL_CONFIG["port"],
        user=MYSQL_CONFIG["user"],
        password=MYSQL_CONFIG["password"],
        database=MYSQL_CONFIG["database"]  # <--- AGGIUNTO: Necessario per operare sul DB
    )

    if mydb.is_connected():
        cursor = mydb.cursor()
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()
        print(f"✅ MySQL: Connessione riuscita al database: {db_name[0]}")

    # =========================
    # CONNESSIONE MONGODB
    # =========================
    mongo_client = MongoClient(MONGO_URI)
    mongo_db = mongo_client[MONGO_DB_NAME]
    
    # Check connessione MongoDB (ping)
    mongo_client.admin.command('ping')
    print(f"✅ MongoDB: Connessione riuscita a '{MONGO_DB_NAME}'")

    # Operazioni MongoDB
    polizze_docs = mongo_db["polizze_documenti"]
    test_doc = {
        "tipo": "polizza_pdf",
        "descrizione": "Documento di test",
        "data": "2026-02-11"
    }

    inserted = polizze_docs.insert_one(test_doc)
    print(f"📄 MongoDB: Documento inserito con ID: {inserted.inserted_id}")

except mysql.connector.Error as err:
    print(f"❌ Errore MySQL: {err}")
except Exception as e:
    print(f"❌ Errore generale: {e}")

finally:
    # Chiusura pulita delle risorse
    if 'cursor' in locals() and cursor:
        cursor.close()
    if 'mydb' in locals() and mydb.is_connected():
        mydb.close()
    if 'mongo_client' in locals():
        mongo_client.close()
    print("🔒 Connessioni chiuse correttamente.")
