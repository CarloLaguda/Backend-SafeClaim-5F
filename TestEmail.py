import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================================
# CONFIGURAZIONE SMTP (Task 9.2 - Mihali)
# ============================================================
EMAIL_CONFIG = {
    "sender": "mattioni.tommaso@iisgalvanimi.edu.it",
    # IMPORTANTE: Inserisci la password di 16 lettere SENZA SPAZI.
    # Se la password era "abcd efgh ilmn opqr", scrivi "abcdefghilmnopqr"
    "password": "faefkrzmkeoizviw", 
    "smtp_server": "smtp.gmail.com",
    "port": 465  # Porta SSL sicura
}

def test_invio_isolato(destinatario):
    """
    Funzione per testare esclusivamente il server SMTP.
    """
    print("--- 🚀 AVVIO TEST SMTP SAFECLAIM ---")
    
    try:
        # Creazione del messaggio
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG["sender"]
        msg['To'] = destinatario
        msg['Subject'] = "SAFECLAIM: Verifica Integrazione SMTP"
        
        corpo = "Test riuscito! Il server SMTP risponde correttamente alle credenziali fornite."
        msg.attach(MIMEText(corpo, 'plain'))

        # Tentativo di connessione
        print(f"🔄 Tentativo di connessione a {EMAIL_CONFIG['smtp_server']}...")
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:
            
            print("🔐 Autenticazione in corso...")
            # Questo è il punto dove ricevi l'errore 535 se la password è errata
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            
            print(f"📤 Invio mail in corso a {destinatario}...")
            server.sendmail(EMAIL_CONFIG["sender"], destinatario, msg.as_string())
            
        print("✅ EMAIL INVIATA CON SUCCESSO!")
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ ERRORE: Credenziali rifiutate (535).")
        print("👉 Assicurati di usare una 'Password per le App' e di aver rimosso gli spazi.")
    except Exception as e:
        print(f"❌ ERRORE IMPREVISTO: {e}")
    
    return False

# Esecuzione del test
if __name__ == "__main__":
    test_invio_isolato("mihali.sebastian@iisgalvanimi.edu.it")