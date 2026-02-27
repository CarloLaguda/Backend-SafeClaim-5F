from gradio_client import Client, handle_file
import os

# Inserisci il tuo token di Hugging Face
MY_TOKEN = "il_tuo_token_qui" 

PROMPT_PERITO = (
    "Agisci come un perito assicurativo esperto. Analizza l'immagine e descrivi l'incidente "
    "identificando: 1. Punto d'impatto principale. 2. Componenti danneggiati (es. paraurti, "
    "gruppi ottici, cristalli). 3. Entità del danno (graffio, ammaccatura, deformazione strutturale). "
    "Usa un linguaggio tecnico."
)

def analizza_danni_ai(image_path):
    if not os.path.exists(image_path):
        return f"Errore: Il file '{image_path}' non trovato."

    try:
        # Usiamo 'token' come parametro corretto
        client = Client("fancyfeast/joy-caption-beta-one", token=MY_TOKEN)
        
        # Basandoci sul tuo output di view_api():
        # La funzione è "/chat_joycaption"
        # Parametri: input_image, prompt, temperature, top_p, max_new_tokens, log_prompt
        result = client.predict(
            input_image=handle_file(image_path),
            prompt=PROMPT_PERITO,
            temperature=0.5,      # Abbassiamo un po' per essere più precisi/tecnici
            top_p=0.9,
            max_new_tokens=512,
            log_prompt=True,
            api_name="/chat_joycaption" # <--- Nome esatto trovato col comando view_api
        )
        
        return result
    except Exception as e:
        return f"❌ Errore durante l'analisi AI: {str(e)}"

if __name__ == "__main__":
    # Assicurati che car_crash.jpg sia nella stessa cartella
    print("Avvio perizia tecnica con Joy-Caption...")
    perizia = analizza_danni_ai("car_crash.jpg")
    print("\n--- RISULTATO ---")
    print(perizia)