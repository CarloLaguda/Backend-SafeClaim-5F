import mysql.connector
from mysql.connector import Error

def create_connection():
    try:
        # Configura qui i tuoi parametri di accesso
        connection = mysql.connector.connect(
            host="localhost",
            user="pythonuser",
            password="password123"

        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS gestione_assicurazioni")
            cursor.execute("USE gestione_assicurazioni")
            return connection, cursor
    except Error as e:
        print(f"Errore durante la connessione: {e}")
        return None, None

def setup_database():
    conn, cursor = create_connection()
    if not conn: return

    # Lista delle query DDL fornite
    tables = [
        """CREATE TABLE IF NOT EXISTS Assicuratore (
            id INT PRIMARY KEY AUTO_INCREMENT, nome VARCHAR(50) NOT NULL, cognome VARCHAR(50) NOT NULL,
            cf VARCHAR(16) UNIQUE NOT NULL, email VARCHAR(100) UNIQUE NOT NULL, psw VARCHAR(255) NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS Assicurazione (
            id INT PRIMARY KEY AUTO_INCREMENT, ragione_sociale VARCHAR(100) NOT NULL, nome VARCHAR(100), telefono VARCHAR(20)
        )""",
        """CREATE TABLE IF NOT EXISTS Automobilista (
            id INT PRIMARY KEY AUTO_INCREMENT, nome VARCHAR(50) NOT NULL, cognome VARCHAR(50) NOT NULL,
            cf VARCHAR(16) UNIQUE NOT NULL, email VARCHAR(100) UNIQUE NOT NULL, psw VARCHAR(255) NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS Azienda (
            id INT PRIMARY KEY AUTO_INCREMENT, ragione_sociale VARCHAR(100) NOT NULL, partita_iva VARCHAR(11) UNIQUE NOT NULL,
            sede_legale VARCHAR(200), email VARCHAR(100), telefono VARCHAR(20)
        )""",
        """CREATE TABLE IF NOT EXISTS Documenti_Anagrafica (
            id INT PRIMARY KEY AUTO_INCREMENT, entita_tipo ENUM('automobilista', 'perito', 'officina', 'assicurazione', 'soccorso') NOT NULL,
            entita_id INT NOT NULL, mongo_doc_id VARCHAR(24) NOT NULL, tipo_documento VARCHAR(50) NOT NULL,
            descrizione VARCHAR(255), data_inserimento DATETIME DEFAULT CURRENT_TIMESTAMP, data_scadenza DATE
        )""",
        """CREATE TABLE IF NOT EXISTS Officina (
            id INT PRIMARY KEY AUTO_INCREMENT, ragione_sociale VARCHAR(100) NOT NULL, citta VARCHAR(50),
            indirizzo VARCHAR(200), telefono VARCHAR(20), email VARCHAR(100), latitudine DECIMAL(10, 8), longitudine DECIMAL(11, 8)
        )""",
        """CREATE TABLE IF NOT EXISTS Perito (
            id INT PRIMARY KEY AUTO_INCREMENT, nome VARCHAR(50) NOT NULL, cognome VARCHAR(50) NOT NULL,
            cf VARCHAR(16) UNIQUE, email VARCHAR(100) UNIQUE NOT NULL, psw VARCHAR(255), latitudine DECIMAL(10, 8), longitudine DECIMAL(11, 8)
        )""",
        """CREATE TABLE IF NOT EXISTS Veicolo (
            id INT PRIMARY KEY AUTO_INCREMENT, targa VARCHAR(10) UNIQUE NOT NULL, n_telaio VARCHAR(17) UNIQUE,
            marca VARCHAR(50), modello VARCHAR(50), anno_immatricolazione YEAR, automobilista_id INT, azienda_id INT,
            CONSTRAINT fk_veicolo_automobilista FOREIGN KEY (automobilista_id) REFERENCES Automobilista(id) ON DELETE SET NULL ON UPDATE CASCADE,
            CONSTRAINT fk_veicolo_azienda FOREIGN KEY (azienda_id) REFERENCES Azienda(id) ON DELETE SET NULL ON UPDATE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS Polizza (
            id INT PRIMARY KEY AUTO_INCREMENT, n_polizza VARCHAR(50) UNIQUE NOT NULL, compagnia_assicurativa VARCHAR(100),
            data_inizio DATE NOT NULL, data_scadenza DATE NOT NULL, massimale DECIMAL(12, 2),
            tipo_copertura ENUM('RCA', 'Kasko', 'Full') DEFAULT 'RCA', veicolo_id INT, assicuratore_id INT,
            documento_mongo_id VARCHAR(24),
            CONSTRAINT fk_polizza_veicolo FOREIGN KEY (veicolo_id) REFERENCES Veicolo(id) ON DELETE SET NULL ON UPDATE CASCADE,
            CONSTRAINT fk_polizza_assicuratore FOREIGN KEY (assicuratore_id) REFERENCES Assicuratore(id) ON DELETE SET NULL ON UPDATE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS Polizza_Documenti (
            id INT PRIMARY KEY AUTO_INCREMENT, polizza_id INT NOT NULL, mongo_doc_id VARCHAR(24) NOT NULL,
            tipo_documento ENUM('polizza_pdf', 'quietanza') NOT NULL, descrizione VARCHAR(255),
            data_inserimento DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_polizza_documenti_polizza FOREIGN KEY (polizza_id) REFERENCES Polizza(id) ON DELETE CASCADE ON UPDATE CASCADE
        )"""
    ]

    for table in tables:
        cursor.execute(table)
    
    conn.commit()
    print("Database e tabelle create con successo.")
    
    # --- INSERT DATA ---
    
    inserts = {
        "Assicuratore": ("INSERT IGNORE INTO Assicuratore (nome, cognome, cf, email, psw) VALUES (%s,%s,%s,%s,%s)", [
            (f'NomeA{i}', f'CognomeA{i}', f'CFASSICURAT{i:05}', f'ass{i}@test.it', 'hash_psw') for i in range(1, 11)
        ]),
        "Assicurazione": ("INSERT IGNORE INTO Assicurazione (ragione_sociale, nome, telefono) VALUES (%s,%s,%s)", [
            (f'Assicura Spa {i}', f'Agenzia {i}', f'0200000{i}') for i in range(1, 11)
        ]),
        "Automobilista": ("INSERT IGNORE INTO Automobilista (nome, cognome, cf, email, psw) VALUES (%s,%s,%s,%s,%s)", [
            (f'Auto{i}', f'Cognome{i}', f'CFDRIVER{i:07}', f'driver{i}@test.it', 'hash_psw') for i in range(1, 11)
        ]),
        "Azienda": ("INSERT IGNORE INTO Azienda (ragione_sociale, partita_iva, sede_legale, email) VALUES (%s,%s,%s,%s)", [
            (f'Azienda Srl {i}', f'{i:011}', f'Via Roma {i}', f'info@azienda{i}.it') for i in range(1, 11)
        ]),
        "Officina": ("INSERT IGNORE INTO Officina (ragione_sociale, citta, telefono, latitudine, longitudine) VALUES (%s,%s,%s,%s,%s)", [
            (f'Garage {i}', 'Milano', f'0211111{i}', 45.4642, 9.1900) for i in range(1, 11)
        ]),
        "Perito": ("INSERT IGNORE INTO Perito (nome, cognome, cf, email, latitudine, longitudine) VALUES (%s,%s,%s,%s,%s,%s)", [
            (f'Perito{i}', f'Rossi{i}', f'CFPERITO{i:07}', f'perito{i}@studiovr.it', 45.0, 9.0) for i in range(1, 11)
        ]),
        "Veicolo": ("INSERT IGNORE INTO Veicolo (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id) VALUES (%s,%s,%s,%s,%s,%s)", [
            (f'AA{i:03}BB', f'VIN{i:014}', 'Fiat', 'Panda', 2020, i) for i in range(1, 11)
        ]),
        "Polizza": ("INSERT IGNORE INTO Polizza (n_polizza, compagnia_assicurativa, data_inizio, data_scadenza, massimale, veicolo_id, assicuratore_id) VALUES (%s,%s,%s,%s,%s,%s,%s)", [
            (f'POL-{i:05}', 'Generali', '2024-01-01', '2025-01-01', 5000000.00, i, i) for i in range(1, 11)
        ]),
        "Documenti_Anagrafica": ("INSERT IGNORE INTO Documenti_Anagrafica (entita_tipo, entita_id, mongo_doc_id, tipo_documento) VALUES (%s,%s,%s,%s)", [
            ('automobilista', i, f'mongoID_anag_{i:012}', 'CI') for i in range(1, 11)
        ]),
        "Polizza_Documenti": ("INSERT IGNORE INTO Polizza_Documenti (polizza_id, mongo_doc_id, tipo_documento) VALUES (%s,%s,%s)", [
            (i, f'mongoID_pol_{i:013}', 'polizza_pdf') for i in range(1, 11)
        ])
    }

    for table_name, (query, data) in inserts.items():
        cursor.executemany(query, data)
        print(f"Inseriti record in {table_name}")

    conn.commit()
    cursor.close()
    conn.close()
    print("\n✅ Setup completato con successo!")

if __name__ == "__main__":
    setup_database()