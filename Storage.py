import cloudinary
import cloudinary.uploader
import os

# ==========================================
# 1. CONFIGURAZIONE (Inserisci i tuoi dati)
# ==========================================
cloudinary.config( 
    cloud_name = "dulbwmi6t", 
    api_key = "875452392366737", 
    api_secret = "KuKkLNZXTzLSZ0i3E8G4VPKgHek"
)

# ==========================================
# 2. IL MOTORE DI STORAGE DI SAFECLAIM
# ==========================================

def safeclaim_upload(file_locale, tipo_documento, id_riferimento, nome_file_personalizzato=None):
    """
    Funzione universale per caricare file su SafeClaim.
    
    Parametri:
    - file_locale: Nome del file caricato nel Codespace (es. "documento.pdf")
    - tipo_documento: 'ID' (Anagrafica), 'SINISTRO' (Foto danni), 'KB' (Manuali)
    - id_riferimento: Codice Fiscale o Numero Sinistro (es. 'SIN_9988')
    - nome_file_personalizzato: Nome finale sul cloud (opzionale)
    """
    
    # Verifica se il file esiste nel Codespace
    if not os.path.exists(file_locale):
        print(f"❌ Errore: Il file '{file_locale}' non è stato trovato nel Codespace. Trascinalo nella colonna a sinistra!")
        return None

    # A) Determina la cartella di destinazione
    mapping_cartelle = {
        'ID': f"SafeClaim_Storage/Anagrafica/Automobilisti/{id_riferimento}",
        'SINISTRO': f"SafeClaim_Storage/Sinistri/{id_riferimento}/Foto_Danni",
        'KB': "SafeClaim_Storage/Knowledge_Base/Manuali_Tecnici"
    }
    cartella_destinazione = mapping_cartelle.get(tipo_documento, "SafeClaim_Storage/Varie")

    # B) Determina se è un'immagine o un file "raw" (PDF/JSON)
    estensione = file_locale.lower().split('.')[-1]
    is_image = estensione in ['jpg', 'jpeg', 'png', 'webp']
    r_type = "image" if is_image else "raw"

    # C) Crea il nome finale
    nome_finale = nome_file_personalizzato if nome_file_personalizzato else file_locale.split('.')[0]
    public_id_completo = f"{cartella_destinazione}/{nome_finale}"

    print(f"⏳ Caricamento in corso ({r_type}): {nome_finale}...")

    try:
        risultato = cloudinary.uploader.upload(
            file_locale,
            public_id=public_id_completo,
            resource_type=r_type,
            # Se è un PDF, forziamo il formato per migliorare la compatibilità
            format=estensione if estensione == 'pdf' else None 
        )
        
        url_finale = risultato['secure_url']
        
        # TRUCCO: Se è un PDF 'raw', aggiungiamo il flag per il download diretto per evitare l'errore "Impossibile caricare"
        if r_type == "raw" and estensione == "pdf":
            url_finale = url_finale.replace("/upload/", "/upload/fl_attachment/")

        print(f"✅ Caricamento completato!")
        print(f"🔗 URL: {url_finale}\n")
        return url_finale

    except Exception as e:
        print(f"❌ Errore durante l'upload: {e}")
        return None
    
# ==========================================
# 3. CARICAMENTO DELLA FOTO DI PROVA
# ==========================================

# Assicurati che il file si chiami esattamente "prova.png" nel tuo Codespace
url_foto = safeclaim_upload(
    file_locale="prova.png", 
    tipo_documento="SINISTRO", 
    id_riferimento="TEST_FOTO_01",
    nome_file_personalizzato="foto_test_danno"
)

# Verifica l'output
if url_foto:
    print(f"🚀 Foto caricata con successo!")