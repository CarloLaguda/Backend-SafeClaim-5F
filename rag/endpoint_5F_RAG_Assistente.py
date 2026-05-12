"""
endpoint_5F_RAG_Assistente.py — Porta 12000
Assistente virtuale per l'automobilista SafeClaim.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from google import genai
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
#  CONFIGURAZIONE GEMINI
# ─────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL   = "gemini-2.5-flash"

client = None

def get_gemini_client():
    global client
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)
    return client

# ─────────────────────────────────────────────
#  KNOWLEDGE BASE — SafeClaim
# ─────────────────────────────────────────────

KNOWLEDGE_BASE = [
    {
        "titolo": "Come mi registro su SafeClaim",
        "contenuto": (
            "Per registrarsi su SafeClaim occorre andare nella pagina di registrazione "
            "e compilare il modulo con: nome, cognome, codice fiscale (16 caratteri), "
            "email e una password di almeno 8 caratteri contenente lettere e numeri. "
            "Una volta inviato il modulo, l'account viene creato immediatamente. "
            "Se email o codice fiscale sono già registrati, il sistema mostra un errore."
        )
    },
    {
        "titolo": "Come effettuo il login",
        "contenuto": (
            "Per accedere a SafeClaim bisogna inserire la propria email e password "
            "nella pagina di login. Esistono tre tipi di utente: automobilista, perito "
            "e assicuratore. Ciascuno viene reindirizzato alla propria dashboard dopo "
            "l'accesso. Se le credenziali non sono corrette, il sistema restituisce un errore."
        )
    },
    {
        "titolo": "Ho dimenticato la password",
        "contenuto": (
            "Se hai dimenticato la password, contatta il supporto SafeClaim via email. "
            "Al momento non è disponibile un sistema automatico di recupero password. "
            "Il team di supporto ti aiuterà a reimpostare le credenziali."
        )
    },
    {
        "titolo": "Come apro un sinistro",
        "contenuto": (
            "Per aprire un sinistro accedi alla tua area personale e clicca su 'Nuovo sinistro'. "
            "Dovrai fornire: la targa del veicolo coinvolto, la data dell'evento, "
            "una descrizione dettagliata dell'accaduto. "
            "Il sinistro viene creato con stato APERTO e riceve un ID univoco MongoDB. "
            "Potrai successivamente aggiungere fotografie del danno."
        )
    },
    {
        "titolo": "Come aggiungo foto al sinistro",
        "contenuto": (
            "Dopo aver aperto un sinistro puoi caricare fotografie del danno accedendo "
            "al dettaglio del sinistro. L'immagine viene analizzata automaticamente "
            "da un sistema di intelligenza artificiale (Gemini Vision) che identifica: "
            "il punto d'impatto principale, i componenti danneggiati (paraurti, gruppi ottici, cristalli), "
            "e l'entità del danno (graffi, ammaccature, deformazioni strutturali)."
        )
    },
    {
        "titolo": "Quali sono gli stati di un sinistro",
        "contenuto": (
            "Un sinistro SafeClaim passa attraverso questi stati: "
            "APERTO → il sinistro è stato creato dall'automobilista; "
            "assegnato_a_perito → un perito è stato assegnato al caso; "
            "in_perizia → il perito sta lavorando sulla pratica; "
            "in_riparazione → il veicolo è presso un'officina convenzionata; "
            "rimborso_proposto → il perito ha definito la stima del danno; "
            "CHIUSO → la pratica è conclusa."
        )
    },
    {
        "titolo": "Come vedo i miei sinistri",
        "contenuto": (
            "Dalla tua dashboard personale puoi vedere la lista di tutti i sinistri aperti "
            "e storici associati al tuo account. I sinistri sono ordinati per data dell'evento "
            "dal più recente al meno recente. Cliccando su un sinistro puoi vedere tutti i dettagli: "
            "immagini caricate, analisi AI, stato pratica, e informazioni sul perito assegnato."
        )
    },
    {
        "titolo": "Posso eliminare un sinistro",
        "contenuto": (
            "Sì, è possibile eliminare un sinistro dalla propria area personale. "
            "L'eliminazione rimuove anche tutte le perizie collegate al sinistro. "
            "Attenzione: questa operazione è irreversibile."
        )
    },
    {
        "titolo": "Quanto tempo ci vuole per la gestione del sinistro",
        "contenuto": (
            "I tempi di gestione dipendono dalla complessità del danno. "
            "Dopo l'apertura del sinistro, un perito viene assegnato dall'assicuratore. "
            "Il perito effettua la perizia e propone una stima del danno. "
            "In media il processo richiede da qualche giorno a qualche settimana."
        )
    },
    {
        "titolo": "Come aggiungo un veicolo al mio profilo",
        "contenuto": (
            "Puoi aggiungere un veicolo al tuo profilo dalla sezione 'I miei veicoli'. "
            "Devi inserire almeno la targa del veicolo. Opzionalmente puoi aggiungere: "
            "numero di telaio, marca, modello e anno di immatricolazione. "
            "La targa deve essere univoca nel sistema."
        )
    },
    {
        "titolo": "Come vedo i miei veicoli",
        "contenuto": (
            "Dalla sezione 'I miei veicoli' puoi visualizzare tutti i veicoli associati al tuo account. "
            "Per ciascun veicolo sono visibili: targa, marca, modello e anno di immatricolazione. "
            "Puoi aprire un sinistro direttamente da un veicolo nella lista."
        )
    },
    {
        "titolo": "Come richiedo il soccorso stradale",
        "contenuto": (
            "SafeClaim offre un servizio di soccorso stradale. Per richiedere il soccorso "
            "accedi alla sezione apposita e inserisci la targa del veicolo in panne. "
            "Puoi anche condividere la tua posizione GPS per facilitare l'intervento. "
            "La richiesta viene registrata con stato 'in_attesa'."
        )
    },
    {
        "titolo": "Come consulto la mia polizza",
        "contenuto": (
            "Dalla sezione 'Polizze' puoi visualizzare tutte le polizze associate ai tuoi veicoli. "
            "Per ogni polizza sono visibili: numero polizza, compagnia assicurativa, "
            "date di inizio e scadenza, massimale e tipo di copertura (es. RCA, Kasko)."
        )
    },
    {
        "titolo": "Cosa copre la polizza RCA",
        "contenuto": (
            "La polizza RCA (Responsabilità Civile Auto) è obbligatoria per legge in Italia "
            "e copre i danni causati a terzi in caso di incidente stradale. "
            "Non copre i danni al proprio veicolo. Per i danni al proprio mezzo "
            "sono necessarie coperture aggiuntive come la Kasko."
        )
    },
    {
        "titolo": "Cos'è una perizia",
        "contenuto": (
            "La perizia è la valutazione tecnica dei danni al veicolo effettuata da un perito "
            "assicurativo incaricato dalla compagnia. Il perito analizza le fotografie e la "
            "descrizione del sinistro, stima il costo dei danni e produce un documento ufficiale. "
            "In SafeClaim l'analisi AI di Gemini supporta il perito con una prima valutazione automatica."
        )
    },
    {
        "titolo": "Come funziona il rimborso",
        "contenuto": (
            "Dopo la perizia, il perito propone una stima del danno. "
            "La pratica passa allo stato 'rimborso_proposto'. "
            "L'assicuratore verifica la pratica e approva l'erogazione del rimborso. "
            "I tempi dipendono dalla compagnia assicurativa e dalla complessità del caso."
        )
    },
    {
        "titolo": "Il mio veicolo verrà riparato",
        "contenuto": (
            "Sì, in molti casi il veicolo viene inviato presso un'officina convenzionata. "
            "Il perito, dopo aver valutato il danno, può disporre la riparazione. "
            "In SafeClaim puoi seguire lo stato della riparazione dalla pagina del sinistro: "
            "quando il veicolo è in officina lo stato diventa 'in_riparazione'."
        )
    },
    {
        "titolo": "Come contatto l'assistenza SafeClaim",
        "contenuto": (
            "Per assistenza puoi contattare SafeClaim tramite la sezione 'Contatti' del sito. "
            "Il team di supporto è disponibile per problemi tecnici, domande sulle polizze, "
            "aggiornamenti sui sinistri e qualsiasi altra necessità."
        )
    },
    {
        "titolo": "SafeClaim è sicuro",
        "contenuto": (
            "SafeClaim utilizza connessioni sicure HTTPS per tutte le comunicazioni. "
            "I dati degli utenti sono memorizzati su database protetti. "
            "Le immagini dei sinistri vengono archiviate in modo sicuro su Cloudinary."
        )
    },
    {
        "titolo": "Come funziona l'analisi AI delle immagini",
        "contenuto": (
            "Quando carichi una foto del danno, SafeClaim utilizza Gemini Vision (Google AI) "
            "per analizzare automaticamente l'immagine. L'analisi identifica: "
            "il punto d'impatto principale, i componenti danneggiati, "
            "e la gravità del danno. Il referto viene messo a disposizione del perito."
        )
    },
    {
        "titolo": "L'analisi AI sostituisce il perito",
        "contenuto": (
            "No, l'analisi AI di SafeClaim è uno strumento di supporto e non sostituisce "
            "la valutazione del perito umano. L'AI fornisce una prima analisi tecnica "
            "per velocizzare il processo, ma la perizia ufficiale viene sempre effettuata "
            "da un perito assicurativo certificato."
        )
    },
]

# ─────────────────────────────────────────────
#  COSTRUZIONE INDICE TF-IDF
# ─────────────────────────────────────────────

print("Costruzione indice TF-IDF sulla Knowledge Base...")

corpus = [chunk["contenuto"] for chunk in KNOWLEDGE_BASE]

vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    min_df=1,
    strip_accents="unicode",
    lowercase=True
)

tfidf_matrix = vectorizer.fit_transform(corpus)
print(f"Indice TF-IDF pronto: {len(KNOWLEDGE_BASE)} chunk, {tfidf_matrix.shape[1]} termini")

# ─────────────────────────────────────────────
#  RETRIEVAL
# ─────────────────────────────────────────────

def recupera_chunk_rilevanti(domanda: str, top_k: int = 3) -> list[dict]:
    query_vec  = vectorizer.transform([domanda])
    similarita = cosine_similarity(query_vec, tfidf_matrix).flatten()
    indici_top = np.argsort(similarita)[::-1][:top_k]
    risultati  = []
    for idx in indici_top:
        if similarita[idx] > 0.01:
            risultati.append({
                "titolo":    KNOWLEDGE_BASE[idx]["titolo"],
                "contenuto": KNOWLEDGE_BASE[idx]["contenuto"],
                "score":     round(float(similarita[idx]), 4)
            })
    return risultati

# ─────────────────────────────────────────────
#  GENERAZIONE RISPOSTA GEMINI
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """Sei SafeBot, l'assistente virtuale di SafeClaim, una piattaforma italiana 
di gestione sinistri assicurativi. Il tuo compito è aiutare gli automobilisti a capire 
come funziona il sito e come utilizzarlo al meglio.

Rispondi in modo chiaro, cordiale e professionale in italiano.
Usa le informazioni fornite nel contesto per rispondere.
Se la risposta non è nel contesto, dì onestamente che non hai questa informazione 
e suggerisci di contattare il supporto SafeClaim.
Non inventare informazioni.
Tieni le risposte concise ma complete (massimo 150 parole).
"""

def genera_risposta_gemini(domanda: str, chunk_rilevanti: list[dict]) -> str:
    import time

    if not chunk_rilevanti:
        contesto = "Non ho trovato informazioni specifiche su questo argomento nella Knowledge Base."
    else:
        parti = []
        for i, chunk in enumerate(chunk_rilevanti, 1):
            parti.append(f"[Informazione {i} - {chunk['titolo']}]\n{chunk['contenuto']}")
        contesto = "\n\n".join(parti)

    prompt_completo = f"""{SYSTEM_PROMPT}

CONTESTO:
{contesto}

DOMANDA DELL'UTENTE:
{domanda}

RISPOSTA:"""

    MAX_TENTATIVI = 3
    ATTESA_BASE   = 5

    for tentativo in range(1, MAX_TENTATIVI + 1):
        try:
            client   = get_gemini_client()
            risposta = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt_completo
            )
            return risposta.text.strip()
        except Exception as e:
            print(f"[ERRORE GEMINI] Tentativo {tentativo}/{MAX_TENTATIVI}: {e}")
            if tentativo < MAX_TENTATIVI:
                time.sleep(ATTESA_BASE * tentativo)
            else:
                return (
                    "Mi dispiace, si è verificato un errore nel generare la risposta. "
                    "Per assistenza contatta direttamente il supporto SafeClaim."
                )

# ─────────────────────────────────────────────
#  ENDPOINT
# ─────────────────────────────────────────────

@app.route('/assistente/chat', methods=['POST'])
def chat_assistente():
    data = request.get_json()
    if not data or 'domanda' not in data:
        return jsonify({"error": "Campo 'domanda' obbligatorio"}), 400

    domanda = data['domanda'].strip()
    if not domanda:
        return jsonify({"error": "La domanda non può essere vuota"}), 400
    if len(domanda) > 500:
        return jsonify({"error": "Domanda troppo lunga (max 500 caratteri)"}), 400

    print(f"\nDomanda ricevuta: '{domanda}'")
    chunk_rilevanti = recupera_chunk_rilevanti(domanda, top_k=3)
    print(f"Chunk recuperati: {[c['titolo'] for c in chunk_rilevanti]}")
    risposta = genera_risposta_gemini(domanda, chunk_rilevanti)
    print(f"Risposta generata ({len(risposta)} caratteri)")

    return jsonify({
        "risposta":    risposta,
        "chunk_usati": [{"titolo": c["titolo"], "score": c["score"]} for c in chunk_rilevanti],
        "status":      "ok"
    }), 200


@app.route('/assistente/health', methods=['GET'])
def health_check():
    return jsonify({
        "status":        "online",
        "modello":       GEMINI_MODEL,
        "kb_chunks":     len(KNOWLEDGE_BASE),
        "tfidf_termini": tfidf_matrix.shape[1]
    }), 200


@app.route('/assistente/argomenti', methods=['GET'])
def lista_argomenti():
    return jsonify({
        "argomenti": [chunk["titolo"] for chunk in KNOWLEDGE_BASE],
        "totale":    len(KNOWLEDGE_BASE)
    }), 200


if __name__ == '__main__':
    print("\nSafeBot RAG Assistente avviato su porta 12000")
    app.run(debug=True, host='0.0.0.0', port=12000)