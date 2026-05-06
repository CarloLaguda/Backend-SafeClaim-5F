import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

# Configurazione connessione
MYSQL_CONFIG = {
    "host":     "db.giobra.com",
    "port":     3306,
    "user":     "user",
    "password": "xxx123##",
    "database": "Prototipo_SafeClaim",
}

try:
    # Connessione al database
    connection = mysql.connector.connect(**MYSQL_CONFIG)

    if connection.is_connected():
        print("Connessione avvenuta con successo!")

        cursor = connection.cursor()

        # 1. Elenco delle tabelle
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("\nTabelle presenti nel database:")
        for table in tables:
            print(f"- {table[0]}")

        # 2. Selezione dei dati per ogni tabella
        for table in tables:
            table_name = table[0]
            print(f"\nDati della tabella '{table_name}':")

            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            # Stampa i nomi delle colonne
            column_names = [desc[0] for desc in cursor.description]
            print("\t".join(column_names))

            # Stampa i dati
            for row in rows:
                print("\t".join(str(item) for item in row))

except Error as e:
    print(f"Errore durante la connessione al database: {e}")

finally:
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()
        print("\nConnessione chiusa.")