"""
endpoint_5F_RAG_Assistente.py — Porta 12000
Assistente virtuale per l'automobilista SafeClaim.

Architettura RAG (Retrieval-Augmented Generation):
  1. L'utente manda una domanda
  2. TF-IDF trova i chunk più rilevanti dalla Knowledge Base
  3. I chunk vengono passati a Gemini come contesto
  4. Gemini genera una risposta naturale e contestualizzata

Dipendenze:
    pip install flask flask-cors scikit-learn google-genai
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from google import genai
import numpy as np
import os

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
#  CONFIGURAZIONE GEMINI
# ─────────────────────────────────────────────

GEMINI_API_KEY = "xxx123##"  # Sostituisci con la tua chiave API Gemini
GEMINI_MODEL = "gemini-2.0-flash"

# Client Gemini (lazy initialization)
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

    # ── REGISTRAZIONE E LOGIN ──────────────────────────────────────────────────
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

    # ── SINISTRI ───────────────────────────────────────────────────────────────
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
            "e l'entità del danno (graffi, ammaccature, deformazioni strutturali). "
            "L'analisi avviene in pochi secondi e il risultato viene salvato sul sinistro."
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
            "Il perito effettua la perizia e propone una stima del danno (rimborso). "
            "In media il processo richiede da qualche giorno a qualche settimana."
        )
    },

    # ── VEICOLI ────────────────────────────────────────────────────────────────
    {
        "titolo": "Come aggiungo un veicolo al mio profilo",
        "contenuto": (
            "Puoi aggiungere un veicolo al tuo profilo dalla sezione 'I miei veicoli'. "
            "Devi inserire almeno la targa del veicolo. Opzionalmente puoi aggiungere: "
            "numero di telaio, marca, modello e anno di immatricolazione. "
            "La targa deve essere univoca nel sistema: non puoi registrare una targa già esistente."
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

    # ── SOCCORSO STRADALE ─────────────────────────────────────────────────────
    {
        "titolo": "Come richiedo il soccorso stradale",
        "contenuto": (
            "SafeClaim offre un servizio di soccorso stradale. Per richiedere il soccorso "
            "accedi alla sezione apposita e inserisci la targa del veicolo in panne. "
            "Puoi anche condividere la tua posizione GPS (latitudine e longitudine) "
            "per facilitare l'intervento. La richiesta viene registrata con stato 'Richiesto' "
            "e l'intervento viene coordinato dalla compagnia assicurativa."
        )
    },
    {
        "titolo": "Stato della richiesta di soccorso",
        "contenuto": (
            "Dopo aver richiesto il soccorso, la richiesta assume lo stato 'Richiesto'. "
            "Riceverai aggiornamenti sullo stato dell'intervento. "
            "Per qualsiasi urgenza puoi contattare direttamente il numero di emergenza "
            "della tua compagnia assicurativa."
        )
    },

    # ── POLIZZE ────────────────────────────────────────────────────────────────
    {
        "titolo": "Come consulto la mia polizza",
        "contenuto": (
            "Dalla sezione 'Polizze' puoi visualizzare tutte le polizze associate ai tuoi veicoli. "
            "Per ogni polizza sono visibili: numero polizza, compagnia assicurativa, "
            "date di inizio e scadenza, massimale e tipo di copertura (es. RCA, Kasko). "
        )
    },
    {
        "titolo": "Cosa copre la polizza RCA",
        "contenuto": (
            "La polizza RCA (Responsabilità Civile Auto) è obbligatoria per legge in Italia "
            "e copre i danni causati a terzi in caso di incidente stradale. "
            "Non copre i danni al proprio veicolo. Per i danni al proprio mezzo "
            "sono necessarie coperture aggiuntive come la Kasko o la Collisione."
        )
    },

    # ── PERIZIA E RIMBORSO ────────────────────────────────────────────────────
    {
        "titolo": "Cos'è una perizia",
        "contenuto": (
            "La perizia è la valutazione tecnica dei danni al veicolo effettuata da un perito "
            "assicurativo incaricato dalla compagnia. Il perito analizza le fotografie e la "
            "descrizione del sinistro, stima il costo dei danni e produce un documento ufficiale "
            "chiamato 'pratica'. In SafeClaim l'analisi AI di Gemini supporta il perito "
            "fornendo una prima valutazione automatica delle immagini caricate."
        )
    },
    {
        "titolo": "Come funziona il rimborso",
        "contenuto": (
            "Dopo la perizia, il perito propone una stima del danno (rimborso). "
            "La pratica passa allo stato 'rimborso_proposto'. "
            "L'assicuratore verifica la pratica e approva l'erogazione del rimborso. "
            "I tempi di erogazione dipendono dalla compagnia assicurativa e dalla "
            "complessità del caso."
        )
    },
    {
        "titolo": "Il mio veicolo verrà riparato",
        "contenuto": (
            "Sì, in molti casi il veicolo viene inviato presso un'officina convenzionata. "
            "Il perito, dopo aver valutato il danno, può disporre la riparazione del veicolo "
            "presso un'officina partner. In SafeClaim puoi seguire lo stato della riparazione "
            "direttamente dalla pagina del sinistro: quando il veicolo è in officina "
            "lo stato diventa 'in_riparazione'."
        )
    },

    # ── ASSISTENZA E CONTATTI ─────────────────────────────────────────────────
    {
        "titolo": "Come contatto l'assistenza SafeClaim",
        "contenuto": (
            "Per assistenza puoi contattare SafeClaim tramite la sezione 'Contatti' del sito. "
            "Il team di supporto è disponibile per problemi tecnici, domande sulle polizze, "
            "aggiornamenti sui sinistri e qualsiasi altra necessità. "
            "SafeClaim dispone anche di un sistema di notifiche email per gli aggiornamenti "
            "più importanti sul tuo sinistro."
        )
    },
    {
        "titolo": "SafeClaim è sicuro",
        "contenuto": (
            "SafeClaim utilizza connessioni sicure HTTPS per tutte le comunicazioni. "
            "I dati degli utenti sono memorizzati su database protetti. "
            "Le immagini dei sinistri vengono archiviate in modo sicuro. "
            "Le password non vengono mai memorizzate in chiaro nel database."
        )
    },

    # ── INTELLIGENZA ARTIFICIALE ──────────────────────────────────────────────
    {
        "titolo": "Come funziona l'analisi AI delle immagini",
        "contenuto": (
            "Quando carichi una foto del danno, SafeClaim utilizza Gemini Vision (Google AI) "
            "per analizzare automaticamente l'immagine. L'analisi identifica: "
            "il punto d'impatto principale sul veicolo, "
            "i componenti specificamente danneggiati (es. paraurti anteriore, faro sinistro, cofano), "
            "e la gravità del danno (graffio superficiale, ammaccatura, deformazione strutturale). "
            "Questo referto tecnico automatico viene messo a disposizione del perito assegnato "
            "per velocizzare la valutazione del sinistro."
        )
    },
    {
        "titolo": "L'analisi AI sostituisce il perito",
        "contenuto": (
            "No, l'analisi AI di SafeClaim è uno strumento di supporto e non sostituisce "
            "la valutazione del perito umano. L'AI fornisce una prima analisi tecnica "
            "delle immagini per velocizzare il processo, ma la perizia ufficiale e la "
            "stima del danno vengono sempre effettuate da un perito assicurativo certificato."
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
#  FUNZIONE RETRIEVAL
# ─────────────────────────────────────────────

def recupera_chunk_rilevanti(domanda: str, top_k: int = 3) -> list[dict]:
    query_vec  = vectorizer.transform([domanda])
    similarita = cosine_similarity(query_vec, tfidf_matrix).flatten()
    indici_top = np.argsort(similarita)[::-1][:top_k]

    risultati = []
    for idx in indici_top:
        if similarita[idx] > 0.01:
            risultati.append({
                "titolo":    KNOWLEDGE_BASE[idx]["titolo"],
                "contenuto": KNOWLEDGE_BASE[idx]["contenuto"],
                "score":     round(float(similarita[idx]), 4)
            })
    return risultati


# ─────────────────────────────────────────────
#  FUNZIONE GENERAZIONE RISPOSTA CON GEMINI
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
        parti_contesto = []
        for i, chunk in enumerate(chunk_rilevanti, 1):
            parti_contesto.append(f"[Informazione {i} - {chunk['titolo']}]\n{chunk['contenuto']}")
        contesto = "\n\n".join(parti_contesto)

    prompt_completo = f"""{SYSTEM_PROMPT}

CONTESTO (informazioni recuperate dalla Knowledge Base):
{contesto}

DOMANDA DELL'UTENTE:
{domanda}

RISPOSTA:"""

    MAX_TENTATIVI = 3
    ATTESA_BASE   = 15  # secondi

    for tentativo in range(1, MAX_TENTATIVI + 1):
        try:
            client = get_gemini_client()
            risposta = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt_completo
            )
            return risposta.text.strip()

        except Exception as e:
            print(f"[ERRORE GEMINI] Tentativo {tentativo}/{MAX_TENTATIVI}: {e}")
            if tentativo < MAX_TENTATIVI:
                attesa = ATTESA_BASE * tentativo  # 15s, 30s
                print(f"[AI] Attendo {attesa}s prima di ritentare...")
                time.sleep(attesa)
            else:
                print(f"[AI] Tutti i tentativi esauriti.")
                return (
                    "Mi dispiace, si è verificato un errore nel generare la risposta. "
                    "Per assistenza contatta direttamente il supporto SafeClaim."
                )


# ─────────────────────────────────────────────
#  ENDPOINT PRINCIPALE
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
        "status":      "online",
        "modello":     GEMINI_MODEL,
        "kb_chunks":   len(KNOWLEDGE_BASE),
        "tfidf_termini": tfidf_matrix.shape[1]
    }), 200


@app.route('/assistente/argomenti', methods=['GET'])
def lista_argomenti():
    argomenti = [chunk["titolo"] for chunk in KNOWLEDGE_BASE]
    return jsonify({"argomenti": argomenti, "totale": len(argomenti)}), 200


if __name__ == '__main__':
    print("\nSafeBot RAG Assistente avviato su porta 12000")
    app.run(debug=True, host='0.0.0.0', port=12000)
