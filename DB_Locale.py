import mysql.connector
from mysql.connector import Error

try:
    # Connessione iniziale
    mydb = mysql.connector.connect(
        host="localhost",
        user="pythonuser",
        password="password123"
    )

    if mydb.is_connected():
        mycursor = mydb.cursor()

        # Creazione Database
        mycursor.execute("CREATE DATABASE IF NOT EXISTS Locale_DB")
        mycursor.execute("USE Locale_DB")

        # --- CREAZIONE TABELLE ---
        tables = {
            "Assicuratore": """
                CREATE TABLE IF NOT EXISTS Assicuratore (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    nome VARCHAR(50) NOT NULL,
                    cognome VARCHAR(50) NOT NULL,
                    cf VARCHAR(16) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    psw VARCHAR(255) NOT NULL
                )
            """,
            "Assicurazione": """
                CREATE TABLE IF NOT EXISTS Assicurazione (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    ragione_sociale VARCHAR(100) NOT NULL,
                    nome VARCHAR(100),
                    telefono VARCHAR(20)
                )
            """,
            "Automobilista": """
                CREATE TABLE IF NOT EXISTS Automobilista (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    nome VARCHAR(50) NOT NULL,
                    cognome VARCHAR(50) NOT NULL,
                    cf VARCHAR(16) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    psw VARCHAR(255) NOT NULL
                )
            """,
            "Azienda": """
                CREATE TABLE IF NOT EXISTS Azienda (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    ragione_sociale VARCHAR(100) NOT NULL,
                    partita_iva VARCHAR(11) UNIQUE NOT NULL,
                    sede_legale VARCHAR(200),
                    email VARCHAR(100),
                    telefono VARCHAR(20)
                )
            """,
            "Officina": """
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
            "Perito": """
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
            "Veicolo": """
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
            "Polizza": """
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
            "Polizza_Documenti": """
                CREATE TABLE IF NOT EXISTS Polizza_Documenti (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    polizza_id INT NOT NULL,
                    mongo_doc_id VARCHAR(24) NOT NULL,
                    tipo_documento ENUM('polizza_pdf', 'quietanza') NOT NULL,
                    descrizione VARCHAR(255),
                    data_inserimento DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "Documenti_Anagrafica": """
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
        }

        for table_name, query in tables.items():
            mycursor.execute(query)
        
        print("✅ Struttura database creata.")

        # --- POPOLAMENTO DATI (INSERT) ---
        # Usiamo IGNORE per evitare errori se i dati esistono già durante i test
        
        insert_queries = [
            # 1. Anagrafiche
            "INSERT IGNORE INTO Assicuratore (id, nome, cognome, cf, email, psw) VALUES (1, 'Marco', 'Longo', 'LNGMRC80A01H501U', 'm.longo@assicura.it', 'pbkdf2:sha256:250000$scrypt...'), (2, 'Sara', 'Neri', 'NRESRA85B41L219Z', 's.neri@assicura.it', 'pbkdf2:sha256:250000$scrypt...')",
            
            "INSERT IGNORE INTO Perito (id, nome, cognome, cf, email, psw, latitudine, longitudine) VALUES (1, 'Luca', 'Verdi', 'VRDLCU75R10F205H', 'luca.verdi@periti.it', 'psw_hashed_1', 45.4642, 9.1900), (2, 'Elena', 'Galli', 'GLLELN90S50H501A', 'elena.galli@periti.it', 'psw_hashed_2', 41.9028, 12.4964)",
            
            "INSERT IGNORE INTO Automobilista (id, nome, cognome, cf, email, psw) VALUES (1, 'Mario', 'Rossi', 'RSSMRA70M15F839V', 'mario.rossi@gmail.com', 'mario_psw'), (2, 'Anna', 'Bianchi', 'BNCNNA92E45L120Q', 'anna.b@outlook.it', 'anna_psw')",
            
            # 2. Aziende ed Enti
            "INSERT IGNORE INTO Azienda (id, ragione_sociale, partita_iva, sede_legale, email, telefono) VALUES (1, 'Logistica Italiana SPA', '01234567890', 'Via Roma 1, Milano', 'amministrazione@logita.it', '02998877'), (2, 'Noleggio SRL', '09876543210', 'Corso Italia 10, Roma', 'info@noleggiosrl.it', '06554433')",
            
            "INSERT IGNORE INTO Assicurazione (id, ragione_sociale, nome, telefono) VALUES (1, 'Generali Assicurazioni', 'Agenzia Milano 1', '02112233'), (2, 'UnipolSai', 'Agenzia Roma Nord', '06887766')",
            
            "INSERT IGNORE INTO Officina (id, ragione_sociale, citta, indirizzo, telefono, email, latitudine, longitudine) VALUES (1, 'Autofficina Centro', 'Milano', 'Via Milano 20', '02334455', 'officina.centro@gmail.com', 45.4700, 9.2000), (2, 'Carrozzeria Sud', 'Roma', 'Via Appia 100', '06112233', 'info@carrozzeriasud.it', 41.8900, 12.5000)",
            
            # 3. Veicoli
            "INSERT IGNORE INTO Veicolo (id, targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id, azienda_id) VALUES (1, 'AB123CD', 'ZFA12345678901234', 'Fiat', 'Panda', 2021, 1, NULL), (2, 'XY987WZ', 'WBA98765432109876', 'BMW', 'Serie 3', 2023, NULL, 1)",
            
            # 4. Polizze e Documenti
            "INSERT IGNORE INTO Polizza (id, n_polizza, compagnia_assicurativa, data_inizio, data_scadenza, massimale, tipo_copertura, veicolo_id, assicuratore_id, documento_mongo_id) VALUES (1, 'POL-100', 'Generali', '2024-01-01', '2025-01-01', 6000000.00, 'RCA', 1, 1, '65a1234567890abcdef12345'), (2, 'POL-200', 'Unipol', '2023-06-01', '2024-06-01', 10000000.00, 'Kasko', 2, 2, '65a9876543210fedcba54321')",
            
            "INSERT IGNORE INTO Polizza_Documenti (polizza_id, mongo_doc_id, tipo_documento, descrizione) VALUES (1, '65b111222333444555666777', 'polizza_pdf', 'Copia digitale firmata'), (1, '65b888999000aaabbbcccddd', 'quietanza', 'Ricevuta pagamento Gennaio')",
            
            "INSERT IGNORE INTO Documenti_Anagrafica (entita_tipo, entita_id, mongo_doc_id, tipo_documento, descrizione) VALUES ('automobilista', 1, '65c1234567890abc12345678', 'Carta Identità', 'Scansione fronte/retro'), ('perito', 1, '65c9876543210def87654321', 'Certificato Iscrizione', 'Iscrizione Albo Nazionale')"
        ]

        for query in insert_queries:
            mycursor.execute(query)
        
        mydb.commit()  # Conferma i dati inseriti
        print(f"✅ Popolamento completato: {mycursor.rowcount} record gestiti.")

except Error as e:
    print(f"❌ ERRORE: {e}")

finally:
    if 'mydb' in locals() and mydb.is_connected():
        mycursor.close()
        mydb.close()
        print("🔌 Connessione chiusa.")