# safe_claim_emails.py

class SafeClaimTemplates:
    """Template per le email del servizio SafeClaim"""

    # --- EMAIL DI BENVENUTO ---
    WELCOME_SUBJECT = "Benvenuto su SafeClaim: La tua serenità è al sicuro 🛡️"
    
    WELCOME_HTML = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #1a73e8; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">SafeClaim</h1>
            </div>
            <div style="padding: 20px;">
                <h2>Ciao {user_name},</h2>
                <p>Ti diamo ufficialmente il benvenuto in <strong>SafeClaim</strong>!</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{dashboard_url}" style="background-color: #1a73e8; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Accedi alla Dashboard</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    # --- EMAIL RICEZIONE PRATICA ---
    CLAIM_RECEIVED_SUBJECT = "Abbiamo ricevuto la tua richiesta SafeClaim (Pratica #{claim_id})"
    
    CLAIM_RECEIVED_HTML = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #2c3e50; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">SafeClaim</h1>
            </div>
            <div style="padding: 20px;">
                <h2>Conferma Ricezione Pratica</h2>
                <p>Ciao {user_name}, ti confermiamo di aver ricevuto correttamente la tua documentazione.</p>
                <div style="background-color: #f1f3f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>ID Pratica:</strong> #{claim_id}</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    # --- EMAIL SEGNALAZIONE NUOVO SINISTRO ---
    NEW_CLAIM_SUBJECT = "Segnalazione Nuovo Sinistro: Pratica avviata con successo"
    
    NEW_CLAIM_HTML = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #f39c12; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">SafeClaim - Nuovo Sinistro</h1>
            </div>
            <div style="padding: 20px;">
                <h2>Ciao {user_name},</h2>
                <p>La segnalazione del tuo nuovo sinistro è stata registrata correttamente.</p>
                <div style="background-color: #fff9f0; border-left: 4px solid #f39c12; padding: 15px; margin: 20px 0;">
                    <p><strong>Tipo:</strong> {claim_type}</p>
                    <p><strong>Data:</strong> {incident_date}</p>
                </div>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{claim_detail_url}" style="background-color: #f39c12; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Vedi Dettagli</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# --- ESEMPIO DI UTILIZZO ---
if __name__ == "__main__":
    # Esempio di generazione stringa (senza creare file)
    test_email = SafeClaimTemplates.NEW_CLAIM_HTML.format(
        user_name="Mario Rossi",
        claim_type="Danno da allagamento",
        incident_date="28/04/2024",
        description="Perdita acqua",
        claim_detail_url="https://app.safeclaim.it/claims/1"
    )

    print("Programma avviato: I template sono pronti per essere utilizzati.")
    # Il comando 'with open...' è stato rimosso. Nessun file verrà creato.