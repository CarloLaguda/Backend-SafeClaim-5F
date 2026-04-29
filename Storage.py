"""
Storage.py — Gestione upload/download immagini su Cloudinary
Usato da endpoint_5F_Sinistri_User.py per salvare le immagini dei sinistri.

Installazione:
    pip install cloudinary
"""

import cloudinary
import cloudinary.uploader
import cloudinary.api
import tempfile
import os

# --- CONFIGURAZIONE CLOUDINARY ---
cloudinary.config(
    cloud_name="dm6estjhs",
    api_key="281163362143651",
    api_secret="sOMrD7f2PNomO1JyTEobaGzyWkg",
    secure=True
)

# Cartella su Cloudinary dove verranno salvate le immagini
CARTELLA_SINISTRI = "safeclaim/sinistri"


def carica_immagine(immagine_bytes: bytes, sinistro_id: str) -> dict:
    """
    Carica un'immagine binaria (bytes) su Cloudinary.

    Args:
        immagine_bytes: immagine come bytes (da file.read())
        sinistro_id:    ID del sinistro MongoDB (usato come nome file)

    Returns:
        dict con:
            - url:        URL pubblico dell'immagine
            - public_id:  ID Cloudinary (serve per eliminarla)
            - secure_url: URL HTTPS
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    tmp.write(immagine_bytes)
    tmp.close()

    try:
        risultato = cloudinary.uploader.upload(
            tmp.name,
            folder=CARTELLA_SINISTRI,
            public_id=f"sinistro_{sinistro_id}",
            overwrite=True,
            resource_type="image"
        )
        return {
            "url":        risultato["url"],
            "secure_url": risultato["secure_url"],
            "public_id":  risultato["public_id"]
        }
    finally:
        # Pulizia file temporaneo locale
        if os.path.exists(tmp.name):
            os.remove(tmp.name)


def elimina_immagine(public_id: str) -> bool:
    """
    Elimina un'immagine da Cloudinary tramite il suo public_id.

    Returns:
        True se eliminata con successo, False altrimenti.
    """
    try:
        risultato = cloudinary.uploader.destroy(public_id)
        return risultato.get("result") == "ok"
    except Exception as e:
        print(f"❌ Errore eliminazione immagine Cloudinary: {e}")
        return False


def ottieni_url(public_id: str) -> str:
    """
    Restituisce l'URL HTTPS di un'immagine dato il suo public_id.
    """
    return cloudinary.CloudinaryImage(public_id).build_url(secure=True)