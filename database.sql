-- Creazione del Database
CREATE DATABASE IF NOT EXISTS safeclaim_db;
USE safeclaim_db;

-- Tabella Automobilista (necessaria per la FK di Veicolo)
CREATE TABLE IF NOT EXISTS Automobilista (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(50) NOT NULL,
    cognome VARCHAR(50) NOT NULL,
    cf VARCHAR(16) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    psw VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

-- Tabella Azienda (necessaria per la FK di Veicolo)
CREATE TABLE IF NOT EXISTS Azienda (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ragione_sociale VARCHAR(100) NOT NULL,
    partita_iva VARCHAR(11) UNIQUE NOT NULL,
    sede_legale VARCHAR(200),
    email VARCHAR(100),
    telefono VARCHAR(20)
) ENGINE=InnoDB;

-- Tabella Veicolo (quella che stavi usando)
CREATE TABLE IF NOT EXISTS Veicolo (
    id INT PRIMARY KEY AUTO_INCREMENT,
    targa VARCHAR(10) UNIQUE NOT NULL,
    n_telaio VARCHAR(50) UNIQUE,
    marca VARCHAR(50),
    modello VARCHAR(50),
    anno_immatricolazione INT,
    automobilista_id INT,
    azienda_id INT,
    CONSTRAINT fk_veicolo_automobilista FOREIGN KEY (automobilista_id) 
        REFERENCES Automobilista(id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_veicolo_azienda FOREIGN KEY (azienda_id) 
        REFERENCES Azienda(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;