import cloudinary
import cloudinary.uploader
import os

# ==========================================
# 1. CONFIGURAZIONE
# ==========================================
cloudinary.config( 
    cloud_name = "dulbwmi6t", 
    api_key = "875452392366737", 
    api_secret = "KuKkLNZXTzLSZ0i3E8G4VPKgHek"
)

# ==========================================
# 2. IL MOTORE DI STORAGE DI SAFECLAIM
# ==========================================

def safeclaim_upload(file_locale, tipo_documento, id_riferimento):
    # Verifica se il file esiste localmente nel Codespace
    if not os.path.exists(file_locale):
        print(f"❌ Errore: Il file '{file_locale}' non è stato trovato!")
        return None

    # Rilevamento estensione e tipo risorsa
    estensione = file_locale.lower().split('.')[-1]
    is_image = estensione in ['jpg', 'jpeg', 'png', 'webp']
    r_type = "image" if is_image else "raw"

    # Definizione percorsi per dashboard e public_id
    cartella_logica = f"SafeClaim_Storage/{tipo_documento}/{id_riferimento}"
    nome_senza_ext = file_locale.split('.')[0]

    try:
        risultato = cloudinary.uploader.upload(
            file_locale,
            public_id=f"{cartella_logica}/{nome_senza_ext}",
            resource_type=r_type,
            # Forza la creazione visibile delle cartelle nella dashboard
            asset_folder=cartella_logica, 
            use_asset_folder_as_public_id_prefix=True,
            format=estensione if estensione == 'pdf' else None 
        )
        
        url_finale = risultato['secure_url']
        
        # Correzione link PDF per evitare errori di visualizzazione
        if estensione == "pdf":
            url_finale = url_finale.replace("/upload/", "/upload/fl_attachment/")

        print(f"✅ Caricamento riuscito in: {cartella_logica}")
        print(f"🔗 URL: {url_finale}")
        return url_finale

    except Exception as e:
        print(f"❌ Errore: {e}")
        return None
    
# ==========================================
# 3. ESECUZIONE
# ==========================================

# Eseguiamo il caricamento (assicurati che prova.png sia nel Codespace)
url_foto = safeclaim_upload(
    file_locale="prova.png", 
    tipo_documento="SINISTRO", 
    id_riferimento="TEST_FOTO_01"
)

if url_foto:
    print(f"🚀 Sistema di Storage SafeClaim Operativo!")