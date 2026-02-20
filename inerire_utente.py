import mysql.connector

try:
    # Connessione al tuo DB MySQL
    db = mysql.connector.connect(
        host="mysql-safeclaim.aevorastudios.com",
        user="safeclaim",
        password="0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=",
        database="safeclaim_db"
    )
    cursor = db.cursor()

    # Query di inserimento
    sql = "INSERT INTO Assicuratore (nome, cognome, cf, email, psw) VALUES (%s, %s, %s, %s, %s)"
    val = ('Mario', 'Rossi', 'RSSMRA80A01H501U', 'mario@safeclaim.it', 'password123')

    cursor.execute(sql, val)
    db.commit() # Fondamentale per salvare i dati!

    print("Utente Mario Rossi inserito con successo!")

except mysql.connector.Error as err:
    print(f"❌ Errore: {err}")

finally:
    if 'db' in locals() and db.is_connected():
        cursor.close()
        db.close()