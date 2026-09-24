import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI, APIStatusError
from pydantic import BaseModel

from feedback_store import carica_feedback_esperti, costruisci_prompt_cds_con_esempi, salva_feedback_esperto
from prompts import SYSTEM_PROMPT_CDS_BASE, SYSTEM_PROMPT_JOURNALING
from rag.diagnosi_score import aggrega_per_diagnosi, calcola_ambiguita, conta_candidate
from rag.retrieval import cerca_sintomi_simili, formatta_contesto_rag, formatta_differenziale

load_dotenv()

MAX_TOKENS_JOURNAL = 4000  # risposte colloquiali brevi: un limite alto fa fallire la richiesta (402) se i crediti sono pochi

MODEL = os.getenv("OPENROUTER_MODEL", "nex-agi/nex-n2.5-pro:free")

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError("OPENROUTER_API_KEY non trovata. Impostala nel file .env.")

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

app = FastAPI(title="AI psychological diagnosis & Consulting API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class JournalRequest(BaseModel):
    messages: list[ChatMessage]


class CdsAnalyzeRequest(BaseModel):
    testo_paziente: str


class CdsFeedbackRequest(BaseModel):
    testo_originale: str
    analisi_ia: str
    correzione_esperto: str


def _handle_openai_error(e: Exception, contesto: str):
    if isinstance(e, APIStatusError) and e.status_code == 402:
        raise HTTPException(
            status_code=402,
            detail="Crediti OpenRouter insufficienti per questa richiesta. Ricarica il saldo e riprova.",
        )
    if isinstance(e, APIStatusError):
        raise HTTPException(status_code=502, detail=f"{contesto}: {e.message}")
    raise HTTPException(status_code=502, detail=f"{contesto}: {e}")


RICHIAMO_FORMATO_TESTO = (
    "Ricorda: rispondi con un messaggio di testo naturale e colloquiale, MAI in JSON "
    "o con campi strutturati come 'ipotesi_diagnostica' o 'punti_chiave'."
)

RISPOSTA_SICUREZZA_FALLBACK = (
    "Mi dispiace, in questo momento non riesco a risponderti come vorrei. "
    "Se quello che mi hai raccontato è urgente o pericoloso, non aspettare: parlane subito "
    "con un adulto di cui ti fidi o chiama il 112."
)


def _sembra_json(testo: str) -> bool:
    testo = (testo or "").strip()
    if not testo.startswith("{"):
        return False
    try:
        json.loads(testo)
        return True
    except ValueError:
        # Anche un JSON troncato (per via del limite di token) va trattato
        # come JSON: se comincia con "{" il modello ha comunque sbagliato formato.
        return True


@app.post("/api/journal/chat")
def journal_chat(payload: JournalRequest):
    messages = [{"role": "system", "content": SYSTEM_PROMPT_JOURNALING}]
    messages += [m.model_dump() for m in payload.messages]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=MAX_TOKENS_JOURNAL,
        )
        reply = response.choices[0].message.content

        if _sembra_json(reply):
            # Il modello ha risposto in formato clinico/JSON invece che in linguaggio
            # naturale: capita su contenuti percepiti come "clinicamente carichi".
            # Un secondo tentativo con un promemoria esplicito di solito basta.
            retry = client.chat.completions.create(
                model=MODEL,
                messages=messages + [
                    {"role": "assistant", "content": reply},
                    {"role": "system", "content": RICHIAMO_FORMATO_TESTO},
                ],
                temperature=0.3,
                max_tokens=MAX_TOKENS_JOURNAL,
            )
            reply = retry.choices[0].message.content
            if _sembra_json(reply):
                reply = RISPOSTA_SICUREZZA_FALLBACK

        return {"reply": reply}
    except Exception as e:
        _handle_openai_error(e, "Errore durante la generazione")


@app.post("/api/cds/analyze")
def cds_analyze(payload: CdsAnalyzeRequest):
    if not payload.testo_paziente.strip():
        raise HTTPException(status_code=400, detail="Per favore inserisci un testo da analizzare.")

    matches = cerca_sintomi_simili(payload.testo_paziente)
    diagnosi = aggrega_per_diagnosi(matches)
    ambiguita = calcola_ambiguita(diagnosi)
    candidate = conta_candidate(diagnosi)

    system_prompt = costruisci_prompt_cds_con_esempi(SYSTEM_PROMPT_CDS_BASE)
    system_prompt += formatta_contesto_rag(matches)
    system_prompt += formatta_differenziale(candidate["lista"], ambiguita)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.testo_paziente},
            ],
            temperature=0.2,
            max_tokens=8000,
            response_format={"type": "json_object"},
        )
        choice = response.choices[0]
        contenuto = choice.message.content or ""
        troncata = choice.finish_reason == "length"
        try:
            json.loads(contenuto)
            json_valido = True
        except ValueError:
            json_valido = False
        if troncata or not json_valido:
            raise HTTPException(
                status_code=502,
                detail=(
                    "La risposta dell'IA è stata interrotta (probabilmente per token insufficienti) "
                    "e l'analisi è incompleta. Riprova o accorcia il testo."
                    if troncata
                    else "L'IA ha restituito una risposta non valida. Riprova."
                ),
            )
        return {
            "analisi": contenuto,
            "rag": {"ambiguita": ambiguita, "candidate": candidate},
        }
    except HTTPException:
        raise
    except Exception as e:
        _handle_openai_error(e, "Errore nell'analisi")


@app.get("/api/cds/feedback/count")
def cds_feedback_count():
    return {"count": len(carica_feedback_esperti())}


@app.post("/api/cds/feedback")
def cds_feedback(payload: CdsFeedbackRequest):
    if not payload.correzione_esperto.strip():
        raise HTTPException(status_code=400, detail="Inserisci una nota prima di salvare.")

    salva_feedback_esperto(payload.testo_originale, payload.analisi_ia, payload.correzione_esperto)
    return {"status": "ok"}
