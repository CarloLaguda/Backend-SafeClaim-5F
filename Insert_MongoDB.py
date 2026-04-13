import mysql.connector
from mysql.connector import Error
from pymongo import MongoClient
from datetime import datetime
import urllib.parse

def popola_database_corposo():
    connection = None
    
    # --- 1. CONFIGURAZIONE MONGODB ATLAS (Allineata alla tua API) ---
    user = "dbFakeClaim"
    password = "xxx123##" # Usa la tua password reale qui
    encoded_password = urllib.parse.quote_plus(password)
    # Uso la stessa stringa della tua API
    CONNECTION_STRING = f"mongodb+srv://{user}:{encoded_password}@cluster0.zgw1jft.mongodb.net/?appName=Cluster0"
    DB_NAME = "FakeClaim"

    try:
        mongo_client = MongoClient(CONNECTION_STRING)
        db_mongo = mongo_client[DB_NAME]
        col_sinistri = db_mongo['sinistri']
        print("🍃 Connesso a MongoDB Atlas!")
    except Exception as e:
        print(f"❌ Errore connessione MongoDB: {e}")
        return

    try:
        # --- 2. CONNESSIONE MYSQL ---
        connection = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            user='pythonuser',
            password='password123',
            database='Locale_DB'
        )

        if connection.is_connected():
            cursor = connection.cursor()
            print("🔗 Connessione a MySQL stabilita.")

            # --- 3. PULIZIA E INSERIMENTO MYSQL (Tuo codice originale) ---
            print("🧹 Pulizia tabelle MySQL...")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cursor.execute("TRUNCATE TABLE Veicolo;")
            cursor.execute("TRUNCATE TABLE Perito;")
            cursor.execute("TRUNCATE TABLE Automobilista;")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

            # Automobilisti
            sql_auto = "INSERT INTO Automobilista (id, nome, cognome, cf, email, psw) VALUES (%s, %s, %s, %s, %s, %s)"
            dati_auto = [
                (1, 'Luca', 'Bianchi', 'BNCLCU80M12H501K', 'luca.bianchi@email.it', 'hash1'),
                (2, 'Anna', 'Verdi', 'VRDNNA90F45F205P', 'anna.verdi@email.it', 'hash2')
            ]
            cursor.executemany(sql_auto, dati_auto)

            # Periti
            sql_perito = "INSERT INTO Perito (id, nome, cognome, cf, email, psw, latitudine, longitudine) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            dati_periti = [
                (1, 'Mario', 'Rossi', 'RSSMRA80A01H501Z', 'mario.rossi@safeclaim.it', 'hash_p1', 45.4642, 9.1900),
                (2, 'Laura', 'Gialli', 'GLLLRA85M45H501Y', 'laura.gialli@safeclaim.it', 'hash_p2', 41.9027, 12.4963)
            ]
            cursor.executemany(sql_perito, dati_periti)

            # Veicoli
            sql_veicolo = "INSERT INTO Veicolo (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id) VALUES (%s, %s, %s, %s, %s, %s)"
            dati_veicoli = [
                ('AB123CD', 'ZAR12345678901234', 'Alfa Romeo', 'Giulia', 2020, 1),
                ('EF456GH', 'ZFA98765432109876', 'Fiat', '500X', 2019, 2)
            ]
            cursor.executemany(sql_veicolo, dati_veicoli)
            
            connection.commit()
            print(f"✅ MySQL popolato.")

            # --- 4. POPOLAMENTO MONGODB (Sinistri cercabili) ---
            print("🍃 Svuotamento e popolamento collezione 'sinistri' su Atlas...")
            col_sinistri.delete_many({}) 

            dati_mongo_sinistri = [
                {
                    "targa": "AB123CD",
                    "id_perito": 1,
                    "data_perizia": "2024-05-10", # DATA PER TEST RICERCA
                    "ora_perizia": "14:00",
                    "stato": "in_perizia",
                    "note_tecniche": "Danno esteso fiancata.",
                    "data_aggiornamento": datetime.utcnow()
                },
                {
                    "targa": "EF456GH",
                    "id_perito": 2,
                    "data_perizia": "2024-05-15",
                    "ora_perizia": "09:00",
                    "stato": "in_perizia",
                    "note_tecniche": "Rilevamento danni grandine.",
                    "data_aggiornamento": datetime.utcnow()
                }
            ]
            
            col_sinistri.insert_many(dati_mongo_sinistri)
            print(f"✅ MongoDB Atlas popolato con {len(dati_mongo_sinistri)} documenti.")

    except Exception as e:
        print(f"❌ Errore durante l'operazione: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔌 Connessione MySQL chiusa.")

if __name__ == "__main__":
    popola_database_corposo()