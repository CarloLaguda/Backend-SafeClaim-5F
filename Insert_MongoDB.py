import mysql.connector
from mysql.connector import Error

def popola_database_corposo():
    connection = None
    try:
        # Connessione al server MySQL
        connection = mysql.connector.connect(
            host='mysql-safeclaim.aevorastudios.com',
            port=3306,
            user='safeclaim',
            password='0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=',
            database='safeclaim_db'
        )

        if connection.is_connected():
            cursor = connection.cursor()
            print("🔗 Connessione a MySQL stabilita. Inizio l'inserimento massivo...")

            # --- 1. AUTOMOBILISTA (10 record) ---
            sql_automobilista = """
                INSERT INTO Automobilista (nome, cognome, cf, email, psw) 
                VALUES (%s, %s, %s, %s, %s)
            """
            dati_automobilisti = [
                ('Luca', 'Bianchi', 'BNCLCU80M12H501K', 'luca.bianchi@email.it', 'hash_auto1'),
                ('Anna', 'Verdi', 'VRDNNA90F45F205P', 'anna.verdi@email.it', 'hash_auto2'),
                ('Marco', 'Neri', 'NRIMRC85C14D612Z', 'marco.neri@email.it', 'hash_auto3'),
                ('Giulia', 'Romano', 'RMNGLI88M45H501T', 'giulia.romano@email.it', 'hash_auto4'),
                ('Francesco', 'Colombo', 'CLBFNC75C12F205W', 'francesco.colombo@email.it', 'hash_auto5'),
                ('Chiara', 'Ricci', 'RCCCHR92D45F205K', 'chiara.ricci@email.it', 'hash_auto6'),
                ('Alessandro', 'Marino', 'MRNLSN80A01H501Z', 'alessandro.marino@email.it', 'hash_auto7'),
                ('Martina', 'Greco', 'GRCMTN85M45H501Y', 'martina.greco@email.it', 'hash_auto8'),
                ('Roberto', 'Conti', 'CNTRRT70C12F205X', 'roberto.conti@email.it', 'hash_auto9'),
                ('Elena', 'Gallo', 'GLLLNE95D45F205J', 'elena.gallo@email.it', 'hash_auto10')
            ]
            cursor.executemany(sql_automobilista, dati_automobilisti)
            print(f"✅ Inseriti {cursor.rowcount} Automobilisti.")

            # --- 2. PERITO (8 record con coordinate varie in Italia) ---
            sql_perito = """
                INSERT INTO Perito (nome, cognome, cf, email, psw, latitudine, longitudine) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            dati_periti = [
                ('Mario', 'Rossi', 'RSSMRA80A01H501Z', 'mario.rossi@safeclaim.it', 'hash_perito1', 45.46420000, 9.19000000),   # Milano
                ('Laura', 'Gialli', 'GLLLRA85M45H501Y', 'laura.gialli@safeclaim.it', 'hash_perito2', 41.90278350, 12.49636550), # Roma
                ('Giuseppe', 'Marrone', 'MRRGPP75C12F205X', 'giuseppe.marrone@safeclaim.it', 'hash_perito3', 40.85179830, 14.26811000), # Napoli
                ('Paolo', 'Costa', 'CSTPLA82A01H501Q', 'paolo.costa@safeclaim.it', 'hash_perito4', 45.07030000, 7.68690000),   # Torino
                ('Silvia', 'Fontana', 'FNTSLV88M45H501W', 'silvia.fontana@safeclaim.it', 'hash_perito5', 44.49490000, 11.34260000), # Bologna
                ('Andrea', 'Rizzo', 'RZZNDR79C12F205E', 'andrea.rizzo@safeclaim.it', 'hash_perito6', 38.11570000, 13.36150000),  # Palermo
                ('Francesca', 'Lombardi', 'LMBFNC85D45F205R', 'francesca.lombardi@safeclaim.it', 'hash_perito7', 43.76960000, 11.25580000), # Firenze
                ('Matteo', 'Moretti', 'MRTTMT91A01H501T', 'matteo.moretti@safeclaim.it', 'hash_perito8', 45.43840000, 10.99160000)   # Verona
            ]
            cursor.executemany(sql_perito, dati_periti)
            print(f"✅ Inseriti {cursor.rowcount} Periti.")

            # --- 3. VEICOLO (12 record, misti tra privati, flotte aziendali fittizie e non assegnati) ---
            sql_veicolo = """
                INSERT INTO Veicolo (targa, n_telaio, marca, modello, anno_immatricolazione, automobilista_id, azienda_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            dati_veicoli = [
                # Assegnati agli automobilisti 1-8
                ('AB123CD', 'ZAR12345678901234', 'Alfa Romeo', 'Giulia', 2020, 1, None),
                ('EF456GH', 'ZFA98765432109876', 'Fiat', '500X', 2019, 2, None),
                ('LM789OP', 'WBA1234567890ABCD', 'BMW', 'Serie 1', 2021, 3, None),
                ('QR456ST', 'WVWZZZ123456789EF', 'Volkswagen', 'Golf', 2018, 4, None),
                ('UV123WX', 'ZLA0987654321QWER', 'Lancia', 'Ypsilon', 2022, 5, None),
                ('YZ987AB', 'WDC1234567890ASDF', 'Mercedes', 'Classe A', 2023, 6, None),
                ('CD654EF', 'VF11234567890ZXCV', 'Renault', 'Clio', 2017, 7, None),
                ('GH321IL', 'ZCF1234567890BNMQ', 'Dacia', 'Duster', 2021, 8, None),
                
                # Assegnati ad aziende (ID fittizi 1 e 2, MySQL non si lamenta perché non c'è FK)
                ('MN111PP', 'VSS1234567890TYUI', 'Ford', 'Transit', 2020, None, 1),
                ('QQ222RR', 'TRU1234567890PLKJ', 'Fiat', 'Ducato', 2019, None, 2),
                
                # Non assegnati (ad esempio in concessionaria o in transito)
                ('GG777KK', 'ZLA0000000321QWER', 'Peugeot', '208', 2024, None, None),
                ('ZZ999XX', 'ZAR99999998901234', 'Alfa Romeo', 'Stelvio', 2023, None, None)
            ]
            cursor.executemany(sql_veicolo, dati_veicoli)
            print(f"✅ Inseriti {cursor.rowcount} Veicoli.")

            # Commit finale
            connection.commit()
            print("🎉 Operazione completata! Tutti i dati massivi sono stati salvati.")

    except Error as e:
        if connection and connection.is_connected():
            connection.rollback()
        print(f"❌ Errore durante l'esecuzione: {e}")
        
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔌 Connessione chiusa.")

if __name__ == "__main__":
    popola_database_corposo()