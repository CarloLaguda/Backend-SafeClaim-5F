import re
from datetime import datetime

def check_exit(testo):
    """Controlla se l'utente vuole uscire dalla chat."""
    if testo.lower().strip() == 'esci':
        print("\n🛑 Segnalazione annullata. Arrivederci!")
        return True
    return False

def richiedi_data_ora():
    while True:
        risposta = input("🗓️ Quando è avvenuto l'incidente? (Formato: GG/MM/AAAA HH:MM)\n> ")
        if check_exit(risposta): return None
        
        try:
            data_validata = datetime.strptime(risposta, "%d/%m/%Y %H:%M")
            # Controllo extra: la data non può essere nel futuro
            if data_validata > datetime.now():
                print("⚠️ Errore: Non puoi inserire una data futura! Riprova.\n")
                continue
            return data_validata.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            print("⚠️ Errore: Data o ora non valida. Usa il formato GG/MM/AAAA HH:MM.\n")

def richiedi_luogo():
    while True:
        risposta = input("\n📍 Dove è avvenuto esattamente l'impatto? (es. Via Roma 10, Milano)\n> ")
        if check_exit(risposta): return None
        
        # Il luogo deve avere almeno 5 caratteri per evitare risposte come "qui" o "Boh"
        if len(risposta.strip()) > 4:
            return risposta.strip()
        print("⚠️ Errore: L'indirizzo inserito è troppo corto. Sii più specifico.\n")

def richiedi_targhe():
    while True:
        risposta = input("\n🚗 Inserisci le targhe dei veicoli (separate da virgola, es. AB123CD, EF456GH):\n> ")
        if check_exit(risposta): return None
        
        # Separo le targhe in una lista, rimuovendo gli spazi extra e mettendo tutto in maiuscolo
        targhe = [t.strip().upper() for t in risposta.split(',')]
        targhe_valide = []
        errore = False
        
        for targa in targhe:
            # Espressione regolare: la targa deve contenere solo lettere e numeri ed essere lunga da 5 a 8 caratteri
            if re.match(r"^[A-Z0-9]{5,8}$", targa):
                targhe_valide.append(targa)
            else:
                errore = True
                break
        
        if not errore and len(targhe_valide) > 0:
            return ", ".join(targhe_valide)
        else:
            print("⚠️ Errore: Formato targa non valido. Usa solo lettere e numeri senza spazi per ogni targa.\n")

def richiedi_feriti():
    while True:
        risposta = input("\n🚑 Ci sono feriti che necessitano di intervento medico? (Sì/No)\n> ")
        if check_exit(risposta): return None
        
        risp_pulita = risposta.strip().lower()
        if risp_pulita in ['sì', 'si', 's']:
            return "Sì"
        elif risp_pulita in ['no', 'n']:
            return "No"
        print("⚠️ Errore: Per favore, rispondi solamente con 'Sì' o 'No'.\n")

def richiedi_dinamica():
    while True:
        risposta = input("\n📝 Descrivi brevemente come è avvenuto l'incidente:\n> ")
        if check_exit(risposta): return None
        
        # La descrizione deve avere almeno 15 caratteri per essere considerata valida
        if len(risposta.strip()) >= 15:
            return risposta.strip()
        print("⚠️ Errore: La descrizione è troppo breve. Fornisci qualche dettaglio in più.\n")

def bot_sinistri():
    print("🤖 Ciao! Sono l'assistente virtuale per la segnalazione dei sinistri stradali.")
    print("Ti farò qualche domanda per raccogliere i dati necessari per la tua pratica.")
    print("(Scrivi 'esci' in qualsiasi momento per interrompere la procedura)\n")

    dati_sinistro = {}

    # Esecuzione in sequenza delle funzioni di validazione
    # Se una qualsiasi funzione restituisce None (utente digita 'esci'), il programma si ferma
    
    data_ora = richiedi_data_ora()
    if not data_ora: return
    dati_sinistro['Data e Ora'] = data_ora

    luogo = richiedi_luogo()
    if not luogo: return
    dati_sinistro['Luogo'] = luogo

    targhe = richiedi_targhe()
    if not targhe: return
    dati_sinistro['Targhe'] = targhe

    feriti = richiedi_feriti()
    if not feriti: return
    dati_sinistro['Feriti'] = feriti

    dinamica = richiedi_dinamica()
    if not dinamica: return
    dati_sinistro['Dinamica'] = dinamica

    # Riepilogo finale
    print("\n" + "="*40)
    print("✅ Perfetto, ho raccolto e validato tutte le informazioni.")
    print("Ecco un riepilogo della tua segnalazione:")
    print("-" * 40)
    for chiave, valore in dati_sinistro.items():
        print(f"🔹 **{chiave}**: {valore}")
    print("=" * 40)
    print("\nDati pronti per essere salvati nel database. Grazie!")

if __name__ == "__main__":
    bot_sinistri()