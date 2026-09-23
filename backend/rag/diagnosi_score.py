"""Aggregazione dei match sintomo->diagnosi in una differenziale pesata,
con indice di ambiguità e conteggio delle diagnosi candidate.

I match grezzi di `retrieval.cerca_sintomi_simili` sono a livello di singolo
sintomo: questo modulo li raggruppa per diagnosi, pesandoli con un IDF che
sterilizza i sintomi "ubiqui" del DSM-5-TR (es. "Clinically Significant
Distress", presente in 136 diagnosi su 167) che altrimenti farebbero comparire
ogni diagnosi come candidata plausibile.
"""

import json
import math
from functools import lru_cache
from pathlib import Path

DATASET_PATH = Path(__file__).resolve().parents[1] / "dsm5_tr_data" / "diagnoses.json"

N_FISSO = 5  # candidati considerati per l'ambiguity score, per rendere i punteggi confrontabili tra casi
TEMPERATURA_SOFTMAX = 0.15
SOGLIA_CANDIDATA = 0.40  # frazione del punteggio massimo sotto cui una diagnosi non è "candidata"
MIN_SINTOMI_CANDIDATA = 2
MAX_CANDIDATE = 6


@lru_cache(maxsize=1)
def _catalogo() -> tuple[dict[str, float], dict[str, dict]]:
    """Calcola l'IDF di ogni sintomo e i metadati di ogni diagnosi da diagnoses.json.

    idf(s) = log(N / df(s)) / log(N), in [0, 1]: un sintomo presente in quasi
    tutte le diagnosi (df alto) pesa vicino a 0, uno raro (df=1) pesa 1.
    """
    with open(DATASET_PATH, encoding="utf-8") as f:
        diagnosi = json.load(f)

    n_diagnosi = len(diagnosi)
    df: dict[str, int] = {}
    meta: dict[str, dict] = {}

    for dx in diagnosi:
        sintomi = dx.get("symptoms", [])
        meta[dx["diagnosis_id"]] = {
            "diagnosis_name": dx["diagnosis_name"],
            "diagnostic_code": dx.get("diagnostic_code"),
            "chapter_category": dx.get("chapter_category"),
            "threshold_count": dx.get("threshold_count"),
            "duration_rule": dx.get("duration_rule"),
            "n_symptoms": len(sintomi),
        }
        for sintomo in sintomi:
            df[sintomo["symptom_id"]] = df.get(sintomo["symptom_id"], 0) + 1

    idf = {
        symptom_id: (math.log(n_diagnosi / conteggio) / math.log(n_diagnosi)) if conteggio < n_diagnosi else 0.0
        for symptom_id, conteggio in df.items()
    }
    return idf, meta


def aggrega_per_diagnosi(matches: list[dict]) -> list[dict]:
    """Raggruppa i match sintomo->diagnosi in una diagnosi->punteggio pesato per IDF.

    peso(m) = score_coseno(m) * idf(symptom_id(m))
    punteggio_d = Σ peso(m) / sqrt(Σ idf(m))   per m nei sintomi matchati di d

    La radice quadrata al denominatore è un damping sublineare: una somma pura
    premierebbe le diagnosi con molti sintomi nel dataset (fino a 20), una
    media pura premierebbe diagnosi che matchano un solo sintomo raro; la
    radice è il compromesso che valorizza la copertura senza farla esplodere.
    """
    idf, meta = _catalogo()

    per_diagnosi: dict[str, list[dict]] = {}
    for m in matches:
        per_diagnosi.setdefault(m["diagnosis_id"], []).append(m)

    risultati = []
    for diagnosis_id, membri in per_diagnosi.items():
        pesi = [idf.get(m["symptom_id"], 0.0) for m in membri]
        raw = sum(m["score"] * peso for m, peso in zip(membri, pesi))
        somma_idf = sum(pesi)
        if raw <= 0 or somma_idf <= 0:
            continue

        punteggio = raw / math.sqrt(somma_idf)
        info = meta.get(diagnosis_id, {})
        risultati.append({
            "diagnosis_id": diagnosis_id,
            "diagnosis_name": info.get("diagnosis_name", diagnosis_id),
            "diagnostic_code": info.get("diagnostic_code"),
            "chapter_category": info.get("chapter_category"),
            "threshold_count": info.get("threshold_count"),
            "duration_rule": info.get("duration_rule"),
            "punteggio": punteggio,
            "n_sintomi_match": len(membri),
            "n_sintomi_totali": info.get("n_symptoms", len(membri)),
            "sintomi": [m["symptom_name"] for m in membri],
        })

    risultati.sort(key=lambda r: r["punteggio"], reverse=True)
    return risultati


def calcola_ambiguita(diagnosi: list[dict]) -> dict:
    """Indice di ambiguità 0-100 basato su entropia di Shannon normalizzata + gap top1-top2.

    entropia_norm usa un denominatore FISSO (log2(N_FISSO)) invece che
    log2(k) con k = numero di candidati: così un caso con 2 candidati e uno
    con 5 restano confrontabili sulla stessa scala.
    """
    if not diagnosi:
        return {"ambiguita": None, "livello": "nessun_dato", "descrizione": "nessun dato disponibile"}

    top = diagnosi[:N_FISSO]
    if len(top) == 1:
        return {"ambiguita": 0, "livello": "verde", "descrizione": "quadro coerente"}

    punteggi = [d["punteggio"] for d in top]
    esponenziali = [math.exp(p / TEMPERATURA_SOFTMAX) for p in punteggi]
    totale = sum(esponenziali)
    probabilita = [e / totale for e in esponenziali]

    entropia = -sum(p * math.log2(p) for p in probabilita if p > 0)
    entropia_norm = entropia / math.log2(N_FISSO)

    gap = (probabilita[0] - probabilita[1]) / probabilita[0] if probabilita[0] > 0 else 0

    ambiguita = 100 * (0.7 * entropia_norm + 0.3 * (1 - gap))
    ambiguita = round(max(0, min(100, ambiguita)))

    if ambiguita < 30:
        livello, descrizione = "verde", "quadro coerente"
    elif ambiguita < 70:
        livello, descrizione = "giallo", "diagnosi differenziale attiva"
    else:
        livello, descrizione = "rosso", "sovrapposizione marcata / possibile comorbidità"

    return {"ambiguita": ambiguita, "livello": livello, "descrizione": descrizione}


def conta_candidate(diagnosi: list[dict]) -> dict:
    """Seleziona le diagnosi 'candidate': sopra una frazione del punteggio massimo
    e con almeno MIN_SINTOMI_CANDIDATA sintomi corrispondenti."""
    if not diagnosi:
        return {"conteggio": 0, "lista": []}

    punteggio_max = diagnosi[0]["punteggio"]
    candidate = [
        d for d in diagnosi
        if d["punteggio"] >= SOGLIA_CANDIDATA * punteggio_max and d["n_sintomi_match"] >= MIN_SINTOMI_CANDIDATA
    ]
    if not candidate:
        candidate = diagnosi[:1]

    candidate = candidate[:MAX_CANDIDATE]
    for d in candidate:
        d["punteggio_norm"] = round(100 * d["punteggio"] / punteggio_max)

    # I dict restano completi (includono sintomi, soglia DSM, durata): servono
    # sia al prompt LLM (formatta_differenziale) sia al frontend, che userà
    # solo il sottoinsieme di campi che gli serve.
    return {"conteggio": len(candidate), "lista": candidate}
