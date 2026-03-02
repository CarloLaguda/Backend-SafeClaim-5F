# safeclaim_assistant.py
# -*- coding: utf-8 -*-

"""
SafeClaim - Assistente Virtuale
Chatbot di supporto per utenti che devono segnalare un incidente
"""

import os
from langchain_openai import ChatOpenAI


# =========================
# CONFIGURAZIONE
# =========================

MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.4


# =========================
# SETUP
# =========================

def setup_environment():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "⚠️ Devi impostare la variabile d'ambiente OPENAI_API_KEY prima di eseguire il programma."
        )

    print("✅ Ambiente configurato correttamente.")


def initialize_llm():
    return ChatOpenAI(
        model=MODEL_NAME,
        temperature=TEMPERATURE
    )


# =========================
# PROMPT SISTEMA SAFECLAIM
# =========================

SYSTEM_PROMPT = """
Sei l'assistente virtuale ufficiale dell'app SafeClaim.

Il tuo ruolo è aiutare gli utenti a:
- Segnalare un incidente stradale
- Compilare correttamente la pratica
- Caricare foto e documenti richiesti
- Capire lo stato della loro richiesta
- Sapere quali informazioni sono necessarie

COMPORTAMENTO:

- Rispondi sempre in italiano.
- Usa un tono professionale ma rassicurante.
- Guida l’utente passo passo.
- Se l’utente è in stato di emergenza, suggerisci di contattare immediatamente i soccorsi.
- Se mancano informazioni, chiedi chiarimenti.
- Non inventare policy legali specifiche.
- Non dare consulenza medica o legale.
- Mantieni le risposte concise ma chiare.

Quando l’utente vuole segnalare un incidente, raccogli in ordine:

1. Data e ora dell'incidente
2. Luogo
3. Targa dei veicoli coinvolti
4. Descrizione dinamica
5. Presenza di feriti
6. Foto disponibili
7. Eventuali testimoni

Guida sempre l’utente passo per passo senza sovraccaricarlo.
"""


# =========================
# CHATBOT
# =========================

def safeclaim_assistant():
    llm = initialize_llm()

    print("\n🤖 SafeClaim Assistant")
    print("Sono qui per aiutarti a segnalare un incidente o gestire la tua pratica.")
    print("Scrivi 'esci' per terminare.\n")

    # Manteniamo memoria conversazione
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    while True:
        user_input = input("👤 Tu: ")

        if user_input.lower() == "esci":
            print("👋 Grazie per aver utilizzato SafeClaim. A presto!")
            break

        messages.append({"role": "user", "content": user_input})

        response = llm.invoke(messages)

        assistant_reply = response.content

        messages.append({"role": "assistant", "content": assistant_reply})

        print("\n🤖 Assistente SafeClaim:")
        print(assistant_reply)
        print()


# =========================
# MAIN
# =========================

def main():
    setup_environment()
    safeclaim_assistant()


if __name__ == "__main__":
    main()