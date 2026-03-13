import cloudinary
import cloudinary.uploader
import os

# 1. CONFIGURAZIONE
cloudinary.config( 
    cloud_name = "dulbwmi6t", 
    api_key = "875452392366737", 
    api_secret = "KuKkLNZXTzLSZ0i3E8G4VPKgHek"
)

# 2. MOTORE DI STORAGE ORGANIZZATO
def safeclaim_upload(file_locale, macro_categoria, id_riferimento, sottocartella=None):
    """
    Gestisce l'upload rispettando l'albero delle cartelle di SafeClaim.
    
    Esempio per l'API /sinistro/{id}/immagini:
    safeclaim_upload("foto.jpg", "Sinistri", "SIN_001", "Foto_Danni")
    """
    if not os.path.exists(file_locale):
        print(f"❌ File '{file_locale}' non trovato.")
        return None

    estensione = file_locale.lower().split('.')[-1]
    r_type = "image" if estensione in ['jpg', 'jpeg', 'png', 'webp'] else "raw"

    # Costruzione del percorso basata sulla tua struttura
    # SafeClaim_Storage / MacroCategoria / ID / [Sottocartella opzionale]
    if sottocartella:
        percorso_cloud = f"SafeClaim_Storage/{macro_categoria}/{id_riferimento}/{sottocartella}"
    else:
        percorso_cloud = f"SafeClaim_Storage/{macro_categoria}/{id_riferimento}"

    nome_file = file_locale.split('.')[0]

    try:
        risultato = cloudinary.uploader.upload(
            file_locale,
            public_id=f"{percorso_cloud}/{nome_file}",
            resource_type=r_type,
            asset_folder=percorso_cloud,
            use_asset_folder_as_public_id_prefix=True,
            format=estensione if estensione == 'pdf' else None
        )
        
        url = risultato['secure_url']
        if estensione == "pdf":
            url = url.replace("/upload/", "/upload/fl_attachment/")

        print(f"✅ Archiviato in: {percorso_cloud}")
        print(f"🔗 URL: {url}")
        return url
    except Exception as e:
        print(f"❌ Errore: {e}")
        return None

# ==========================================
# 3. ESEMPIO PER L'API: /sinistro/{id}/immagini
# ==========================================

# Quando ricevi una chiamata a /sinistro/SIN_123/immagini:
id_sinistro_da_api = "SIN_123" # Questo verrebbe dall'URL dell'API
safeclaim_upload(
    file_locale="incidente.jpg", 
    macro_categoria="Sinistri", 
    id_riferimento=id_sinistro_da_api, 
    sottocartella="Foto_Danni"
)