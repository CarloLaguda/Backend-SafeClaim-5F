import mysql.connector

# Connessione iniziale
mydb = mysql.connector.connect(
  host="localhost",
  user="pythonuser",
  password="password123"
)

mycursor = mydb.cursor()

# Creazione e selezione del Database
mycursor.execute("CREATE DATABASE IF NOT EXISTS mydatabase")
mycursor.execute("USE mydatabase")

# --- DEFINIZIONE DELLE TABELLE ---
tables = {}

tables['Assicuratore'] = (
    "CREATE TABLE IF NOT EXISTS Assicuratore ("
    "  id INT PRIMARY KEY AUTO_INCREMENT,"
    "  nome VARCHAR(50) NOT NULL,"
    "  cognome VARCHAR(50) NOT NULL,"
    "  cf VARCHAR(16) UNIQUE NOT NULL,"
    "  email VARCHAR(100) UNIQUE NOT NULL,"
    "  psw VARCHAR(255) NOT NULL"
    ")"
)

tables['Assicurazione'] = (
    "CREATE TABLE IF NOT EXISTS Assicurazione ("
    "  id INT PRIMARY KEY AUTO_INCREMENT,"
    "  ragione_sociale VARCHAR(100) NOT NULL,"
    "  nome VARCHAR(100),"
    "  telefono VARCHAR(20)"
    ")"
)

tables['Automobilista'] = (
    "CREATE TABLE IF NOT EXISTS Automobilista ("
    "  id INT PRIMARY KEY AUTO_INCREMENT,"
    "  nome VARCHAR(50) NOT NULL,"
    "  cognome VARCHAR(50) NOT NULL,"
    "  cf VARCHAR(16) UNIQUE NOT NULL,"
    "  email VARCHAR(100) UNIQUE NOT NULL,"
    "  psw VARCHAR(255) NOT NULL"
    ")"
)

tables['Azienda'] = (
    "CREATE TABLE IF NOT EXISTS Azienda ("
    "  id INT PRIMARY KEY AUTO_INCREMENT,"
    "  ragione_sociale VARCHAR(100) NOT NULL,"
    "  partita_iva VARCHAR(11) UNIQUE NOT NULL,"
    "  sede_legale VARCHAR(200),"
    "  email VARCHAR(100),"
    "  telefono VARCHAR(20)"
    ")"
)

tables['Officina'] = (
    "CREATE TABLE IF NOT EXISTS Officina ("
    "  id INT PRIMARY KEY AUTO_INCREMENT,"
    "  ragione_sociale VARCHAR(100) NOT NULL,"
    "  citta VARCHAR(50),"
    "  indirizzo VARCHAR(200),"
    "  telefono VARCHAR(20),"
    "  email VARCHAR(100),"
    "  latitudine DECIMAL(10, 8),"
    "  longitudine DECIMAL(11, 8)"
    ")"
)

tables['Perito'] = (
    "CREATE TABLE IF NOT EXISTS Perito ("
    "  id INT PRIMARY KEY AUTO_INCREMENT,"
    "  nome VARCHAR(50) NOT NULL,"
    "  cognome VARCHAR(50) NOT NULL,"
    "  cf VARCHAR(16) UNIQUE,"
    "  email VARCHAR(100) UNIQUE NOT NULL,"
    "  psw VARCHAR(255),"
    "  latitudine DECIMAL(10, 8),"
    "  longitudine DECIMAL(11, 8)"
    ")"
)

tables['Veicolo'] = (
    "CREATE TABLE IF NOT EXISTS Veicolo ("
    "  id INT PRIMARY KEY AUTO_INCREMENT,"
    "  targa VARCHAR(10) UNIQUE NOT NULL,"
    "  n_telaio VARCHAR(17) UNIQUE,"
    "  marca VARCHAR(50),"
    "  modello VARCHAR(50),"
    "  anno_immatricolazione YEAR,"
    "  automobilista_id INT,"
    "  azienda_id INT"
    ")"
)

tables['Polizza'] = (
    "CREATE TABLE IF NOT EXISTS Polizza ("
    "  id INT PRIMARY KEY AUTO_INCREMENT,"
    "  n_polizza VARCHAR(50) UNIQUE NOT NULL,"
    "  compagnia_assicurativa VARCHAR(100),"
    "  data_inizio DATE NOT NULL,"
    "  data_scadenza DATE NOT NULL,"
    "  massimale DECIMAL(12, 2),"
    "  tipo_copertura ENUM('RCA', 'Kasko', 'Full') DEFAULT 'RCA',"
    "  veicolo_id INT,"
    "  assicuratore_id INT,"
    "  documento_mongo_id VARCHAR(24)"
    ")"
)

tables['Documenti_Anagrafica'] = (
    "CREATE TABLE IF NOT EXISTS Documenti_Anagrafica ("
    "  id INT PRIMARY KEY AUTO_INCREMENT,"
    "  entita_tipo ENUM('automobilista', 'perito', 'officina', 'assicuratore', 'soccorso') NOT NULL,"
    "  entita_id INT NOT NULL,"
    "  mongo_doc_id VARCHAR(24) NOT NULL,"
    "  tipo_documento VARCHAR(50) NOT NULL,"
    "  descrizione VARCHAR(255),"
    "  data_inserimento DATETIME DEFAULT CURRENT_TIMESTAMP,"
    "  data_scadenza DATE"
    ")"
)

tables['Polizza_Documenti'] = (
    "CREATE TABLE IF NOT EXISTS Polizza_Documenti ("
    "  id INT PRIMARY KEY AUTO_INCREMENT,"
    "  polizza_id INT NOT NULL,"
    "  mongo_doc_id VARCHAR(24) NOT NULL,"
    "  tipo_documento ENUM('polizza_pdf', 'quietanza') NOT NULL,"
    "  descrizione VARCHAR(255),"
    "  data_inserimento DATETIME DEFAULT CURRENT_TIMESTAMP"
    ")"
)

# --- ESECUZIONE CREAZIONE TABELLE ---
for table_name in tables:
    table_description = tables[table_name]
    try:
        print(f"Creazione tabella {table_name}: ", end="")
        mycursor.execute(table_description)
        print("OK")
    except mysql.connector.Error as err:
        print(f"ERRORE: {err}")

# Chiusura
mycursor.close()
mydb.close()