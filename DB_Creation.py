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
    "database": "safeclaim_db"
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
        password=MYSQL_CONFIG["password"]
    )

    cursor = mydb.cursor()

    # Creazione database
    cursor.execute("CREATE DATABASE IF NOT EXISTS safeclaim_db")
    cursor.execute("USE safeclaim_db")

    tables = [

        """
        CREATE TABLE IF NOT EXISTS Assicuratore (
            id INT PRIMARY KEY AUTO_INCREMENT,
            nome VARCHAR(50) NOT NULL,
            cognome VARCHAR(50) NOT NULL,
            cf VARCHAR(16) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            psw VARCHAR(255) NOT NULL
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS Assicurazione (
            id INT PRIMARY KEY AUTO_INCREMENT,
            ragione_sociale VARCHAR(100) NOT NULL,
            nome VARCHAR(100),
            telefono VARCHAR(20)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS Automobilista (
            id INT PRIMARY KEY AUTO_INCREMENT,
            nome VARCHAR(50) NOT NULL,
            cognome VARCHAR(50) NOT NULL,
            cf VARCHAR(16) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            psw VARCHAR(255) NOT NULL
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS Azienda (
            id INT PRIMARY KEY AUTO_INCREMENT,
            ragione_sociale VARCHAR(100) NOT NULL,
            partita_iva VARCHAR(11) UNIQUE NOT NULL,
            sede_legale VARCHAR(200),
            email VARCHAR(100),
            telefono VARCHAR(20)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS Officina (
            id INT PRIMARY KEY AUTO_INCREMENT,
            ragione_sociale VARCHAR(100) NOT NULL,
            citta VARCHAR(50),
            indirizzo VARCHAR(200),
            telefono VARCHAR(20),
            email VARCHAR(100),
            latitudine DECIMAL(10, 8),
            longitudine DECIMAL(11, 8)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS Perito (
            id INT PRIMARY KEY AUTO_INCREMENT,
            nome VARCHAR(50) NOT NULL,
            cognome VARCHAR(50) NOT NULL,
            cf VARCHAR(16) UNIQUE,
            email VARCHAR(100) UNIQUE NOT NULL,
            psw VARCHAR(255),
            latitudine DECIMAL(10, 8),
            longitudine DECIMAL(11, 8)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS Veicolo (
            id INT PRIMARY KEY AUTO_INCREMENT,
            targa VARCHAR(10) UNIQUE NOT NULL,
            n_telaio VARCHAR(17) UNIQUE,
            marca VARCHAR(50),
            modello VARCHAR(50),
            anno_immatricolazione YEAR,
            automobilista_id INT,
            azienda_id INT
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS Polizza (
            id INT PRIMARY KEY AUTO_INCREMENT,
            n_polizza VARCHAR(50) UNIQUE NOT NULL,
            compagnia_assicurativa VARCHAR(100),
            data_inizio DATE NOT NULL,
            data_scadenza DATE NOT NULL,
            massimale DECIMAL(12, 2),
            tipo_copertura ENUM('RCA', 'Kasko', 'Full') DEFAULT 'RCA',
            veicolo_id INT,
            assicuratore_id INT,
            documento_mongo_id VARCHAR(24)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS Polizza_Documenti (
            id INT PRIMARY KEY AUTO_INCREMENT,
            polizza_id INT NOT NULL,
            mongo_doc_id VARCHAR(24) NOT NULL,
            tipo_documento ENUM('polizza_pdf', 'quietanza') NOT NULL,
            descrizione VARCHAR(255),
            data_inserimento DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS Documenti_Anagrafica (
            id INT PRIMARY KEY AUTO_INCREMENT,
            entita_tipo ENUM('automobilista', 'perito', 'officina', 'assicuratore', 'soccorso') NOT NULL,
            entita_id INT NOT NULL,
            mongo_doc_id VARCHAR(24) NOT NULL,
            tipo_documento VARCHAR(50) NOT NULL,
            descrizione VARCHAR(255),
            data_inserimento DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_scadenza DATE
        )
        """
    ]

    for table in tables:
        cursor.execute(table)

    mydb.commit()
    print("✅ MySQL: database e tabelle create correttamente")

    # =========================
    # CONNESSIONE MONGODB
    # =========================
    mongo_client = MongoClient(MONGO_URI)
    mongo_db = mongo_client[MONGO_DB_NAME]

    print("✅ MongoDB: connessione riuscita")

    # Esempio collezioni
    polizze_docs = mongo_db["polizze_documenti"]
    anagrafica_docs = mongo_db["documenti_anagrafica"]

    # Test inserimento
    test_doc = {
        "tipo": "polizza_pdf",
        "descrizione": "Documento di test",
        "data": "2026-02-10"
    }

    inserted = polizze_docs.insert_one(test_doc)
    print(f"📄 Documento MongoDB inserito con ID: {inserted.inserted_id}")

except mysql.connector.Error as err:
    print(f"❌ Errore MySQL: {err}")

except Exception as e:
    print(f"❌ Errore generale: {e}")

finally:
    if 'cursor' in locals():
        cursor.close()
    if 'mydb' in locals() and mydb.is_connected():
        mydb.close()
    print("🔒 Connessioni chiuse")