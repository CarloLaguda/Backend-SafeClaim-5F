import smtplib  # Importa la libreria per gestire il protocollo SMTP (invio mail)
from email.mime.text import MIMEText  # Serve per creare la parte testuale della mail
from email.mime.multipart import MIMEMultipart  # Serve per creare una mail con più parti (es. testo + allegati)

# CONFIGURAZIONE SMTP
# Creiamo un dizionario che contiene i dati necessari per connettersi al server di Google
EMAIL_CONFIG = {  # Definisce un dizionario con le configurazioni email
    "sender": "mattioni.tommaso@iisgalvanimi.edu.it",  # L'indirizzo email che invia il messaggio
    # Password specifica generata da Google (App Password)
    "password": "faefkrzmkeoizviw",  # Password per l'app Gmail
    "smtp_server": "smtp.gmail.com",  # L'indirizzo del server di posta in uscita di Google
    "port": 465  # La porta standard per connessioni sicure SSL
}

def test_invio_isolato(destinatario):  # Definisce la funzione per testare l'invio email
                                       # Mettendo destinatario, la funzione diventa un modello universale: 
                                       # la puoi usare per testare l'invio a te stesso, domani per testarlo su un collega, dopodiché su un cliente
    """
    Funzione per testare esclusivamente il server SMTP.
    """
    print(" AVVIO TEST SMTP SAFECLAIM ")  # Messaggio per l'utente

    try:  # Inizia blocco try per gestire errori
        # Creazione dell'oggetto messaggio che conterrà mittente, destinatario e corpo
        msg = MIMEMultipart()  # Crea un oggetto messaggio multipart, perché un'email moderna può contenere più parti: testo, allegati.
        msg['From'] = EMAIL_CONFIG["sender"]  # Imposta il mittente nell'intestazione della mail
        msg['To'] = destinatario  # Imposta il destinatario nell'intestazione
        msg['Subject'] = "SAFECLAIM: Verifica Integrazione SMTP"  # Imposta l'oggetto della mail

        # Definiamo il testo del messaggio
        corpo = "Test riuscito! Il server SMTP risponde correttamente alle credenziali fornite."  # Testo del messaggio
        msg.attach(MIMEText(corpo, 'plain'))  # Converte la stringa di testo in un formato compatibile con gli standard delle email e lo allega al messaggio
                                              #Indica che il testo è "semplice"

        # Tentativo di connessione
        print(f" Tentativo di connessione a {EMAIL_CONFIG['smtp_server']}...")  # Stampa tentativo connessione

        # Apre una connessione sicura (SMTP_SSL) verso il server
        # Il comando 'with' assicura che la connessione venga chiusa automaticamente alla fine
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server: 
            # smtplibÈ la libreria standard di Python che contiene tutti gli strumenti per parlare con i server di posta
            #SMTP_SSL è una classe che stabilisce una connessione sicura usando SSL, garantendo che i dati (come la password) siano criptati durante la trasmissione.
        
            print(" Autenticazione in corso...")  # Stampa autenticazione in corso
            # Effettua il login usando l'indirizzo email e la password dell'app
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])  # Login al server

            print(f" Invio mail in corso a {destinatario}...")  # Stampa invio in corso
            # Spedisce la mail trasformando l'oggetto 'msg' in una stringa leggibile dai server
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())  #Consegna l'email al server, specificando mittente, destinatario e il contenuto convertito in testo
            # sendmail() Richiama il metodo standard di Python per trasmettere il messaggio al server SMTP 

        # Se tutto va bene, stampa il successo
        print(" EMAIL INVIATA CON SUCCESSO!")  # Messaggio di successo
        return True  # Ritorna True se riuscito

    # Gestione specifica dell'errore di login (es. password sbagliata)
    except smtplib.SMTPAuthenticationError:  # Cattura errore autenticazione
        print(" ERRORE: Credenziali rifiutate.")  # Messaggio errore credenziali
        print(" Assicurati di usare una 'Password per le App' e di aver rimosso gli spazi.")  # Suggerimento

    # Gestione di qualsiasi altro errore (es. mancanza di internet o server irraggiungibile)
    except Exception as e:  # Cattura qualsiasi altra eccezione
        print(f" ERRORE IMPREVISTO: {e}")  # Messaggio errore generico

    return False  # Ritorna False se fallito

# Punto di ingresso del programma
if __name__ == "__main__":  # Se il file è eseguito direttamente
    # Chiama la funzione passando l'indirizzo del tuo compagno
    test_invio_isolato("mihali.sebastian@iisgalvanimi.edu.it")  # Chiama la funzione di test con destinatario
    # Avvia il test pratico inviando un'email reale all'indirizzo specificato tra parentesi, ovvero il destinatario che abbiano scritto in precedenza nella funzione.
    #se ricevi la mail, il test è riuscito