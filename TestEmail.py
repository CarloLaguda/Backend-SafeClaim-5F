import smtplib  # Importa la libreria per gestire il protocollo SMTP (invio mail)
from email.mime.text import MIMEText  # Serve per creare la parte testuale della mail
from email.mime.multipart import MIMEMultipart  # Serve per creare una mail con più parti (es. testo + allegati)

# CONFIGURAZIONE SMTP 
# Creiamo un dizionario che contiene i dati necessari per connettersi al server di Google
EMAIL_CONFIG = {
    "sender": "mattioni.tommaso@iisgalvanimi.edu.it",  # L'indirizzo email che invia il messaggio
    # Password specifica generata da Google (App Password)
    "password": "faefkrzmkeoizviw", 
    "smtp_server": "smtp.gmail.com",  # L'indirizzo del server di posta in uscita di Google
    "port": 465  # La porta standard per connessioni sicure SSL
}

def test_invio_isolato(destinatario):
    """
    Funzione per testare esclusivamente il server SMTP.
    """
    print("---  AVVIO TEST SMTP SAFECLAIM ---") # Messaggio a video per l'utente
    
    try:
        # Creazione dell'oggetto messaggio che conterrà mittente, destinatario e corpo
        msg = MIMEMultipart() 
        msg['From'] = EMAIL_CONFIG["sender"]  # Imposta il mittente nell'intestazione della mail
        msg['To'] = destinatario  # Imposta il destinatario nell'intestazione
        msg['Subject'] = "SAFECLAIM: Verifica Integrazione SMTP"  # Imposta l'oggetto della mail
        
        # Definiamo il testo del messaggio
        corpo = "Test riuscito! Il server SMTP risponde correttamente alle credenziali fornite."
        # Trasformiamo il testo semplice in un oggetto MIMEText e lo "agganciamo" alla mail
        msg.attach(MIMEText(corpo, 'plain'))

        # Tentativo di connessione
        print(f" Tentativo di connessione a {EMAIL_CONFIG['smtp_server']}...")
        
        # Apre una connessione sicura (SMTP_SSL) verso il server
        # Il comando 'with' assicura che la connessione venga chiusa automaticamente alla fine
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:
            
            print(" Autenticazione in corso...")
            # Effettua il login usando l'indirizzo email e la password dell'app
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            
            print(f" Invio mail in corso a {destinatario}...")
            # Spedisce la mail trasformando l'oggetto 'msg' in una stringa leggibile dai server
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())
            
        # Se tutto va bene, stampa il successo
        print(" EMAIL INVIATA CON SUCCESSO!")
        return True

    # Gestione specifica dell'errore di login (es. password sbagliata)
    except smtplib.SMTPAuthenticationError:
        print(" ERRORE: Credenziali rifiutate.")
        print(" Assicurati di usare una 'Password per le App' e di aver rimosso gli spazi.")
    
    # Gestione di qualsiasi altro errore (es. mancanza di internet o server irraggiungibile)
    except Exception as e:
        print(f" ERRORE IMPREVISTO: {e}")
    
    return False # Ritorna falso se qualcosa è andato storto

# Punto di ingresso del programma
if __name__ == "__main__":
    # Chiama la funzione passando l'indirizzo del tuo compagno
    test_invio_isolato("mihali.sebastian@iisgalvanimi.edu.it")