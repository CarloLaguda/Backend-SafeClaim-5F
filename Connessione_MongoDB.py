import mysql.connector
from mysql.connector import Error
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

mydb = None
client = None

try:
    mydb = mysql.connector.connect(
        host="mysql-safeclaim.aevorastudios.com",
        port=3306,
        user="safeclaim",
        password="0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
        database="safeclaim_db"
    )

    if mydb.is_connected():
        mycursor = mydb.cursor()
        print("MySQL: Connessione riuscita a mysql-safeclaim.aevorastudios.com")

    uri = "mongodb://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE%2BtM%3D@mongo-safeclaim.aevorastudios.com:27017/"
    
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    db_nosql = client['safeclaim_mongo']
    print("MongoDB: Connessione riuscita a mongo-safeclaim.aevorastudios.com")

except ServerSelectionTimeoutError:
    print("MongoDB: Errore di connessione (Timeout).")
except Error as e:
    print(f"MySQL Error: {e}")
except Exception as e:
    print(f"Errore generico: {e}")

finally:
    if mydb and mydb.is_connected():
        mycursor.close()
        mydb.close()
        print("MySQL: Connessione chiusa.")
    if client:
        client.close()
        print("MongoDB: Connessione chiusa.")