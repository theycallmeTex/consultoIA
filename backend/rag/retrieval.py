import re

from .embeddings import embed_queries
from .qdrant_store import COLLECTION, VECTOR_NAME, get_client

# Sotto questa soglia di similarità coseno il risultato è rumore, non un match
# clinicamente pertinente. Abbassata rispetto alla versione a query singola:
# i segmenti brevi del multi-query producono score coseno più bassi del testo
# intero, e l'aggregazione per diagnosi filtra il rumore residuo a valle.
SOGLIA_RILEVANZA = 0.35

_SEPARATORI = re.compile(r"[.;\n!?]|,\s*(?:e|ma|inoltre|mentre|anche)\s+")


def segmenta_testo(testo: str, min_char: int = 25, max_seg: int = 12) -> list[str]:
    """Spezza il racconto del paziente in segmenti brevi, uno per (idealmente) sintomo.

    Una singola query sull'intero testo dilusce sintomi distinti in un unico
    vettore "medio"; qui invece ogni frase/proposizione diventa una query a sé,
    così un caso multi-sintomo (insonnia + ansia + calo dell'umore) trova
    match specifici per ciascuno invece di uno generico per tutti.
    """
    segmenti = [s.strip() for s in _SEPARATORI.split(testo)]
    segmenti = [s for s in segmenti if len(s) >= min_char]

    visti = set()
    dedup = []
    for s in segmenti:
        if s not in visti:
            visti.add(s)
            dedup.append(s)

    if not dedup:
        return [testo]

    # Il testo intero resta sempre il primo segmento: cattura il quadro
    # d'insieme che la scomposizione in frasi può perdere.
    return [testo] + dedup[:max_seg]


def cerca_sintomi_simili(query: str, top_k_per_segmento: int = 6, top_k: int = 12) -> list[dict]:
    """Trova i sintomi DSM-5-TR più simili semanticamente al testo del paziente.

    Interroga Qdrant una volta per ogni segmento del testo (una sola chiamata
    Cohere in batch per tutti i vettori), poi fonde i risultati tenendo per
    ogni coppia (diagnosi, sintomo) lo score migliore fra i segmenti che l'hanno
    trovata: usare il massimo, non la somma, evita di premiare i sintomi
    generici solo perché ricorrono in più frasi del racconto.
    """
    segmenti = segmenta_testo(query)
    vettori = embed_queries(segmenti)
    client = get_client()

    migliori: dict[tuple, dict] = {}
    for vettore in vettori:
        hits = client.query_points(
            collection_name=COLLECTION,
            query=vettore,
            using=VECTOR_NAME,
            limit=top_k_per_segmento,
            score_threshold=SOGLIA_RILEVANZA,
        ).points
        for hit in hits:
            chiave = (hit.payload["diagnosis_id"], hit.payload["symptom_id"])
            esistente = migliori.get(chiave)
            if esistente is None:
                migliori[chiave] = {"score": hit.score, "n_segmenti_match": 1, **hit.payload}
            else:
                esistente["n_segmenti_match"] += 1
                if hit.score > esistente["score"]:
                    esistente["score"] = hit.score

    risultati = sorted(migliori.values(), key=lambda m: m["score"], reverse=True)
    return risultati[:top_k]


def formatta_contesto_rag(matches: list[dict]) -> str:
    if not matches:
        return ""

    righe = ["\n\n### CONTESTO DSM-5-TR (sintomi correlati trovati nel database, i più simili al caso):"]
    for m in matches:
        righe.append(
            f"- [{m['diagnosis_name']} ({m.get('diagnostic_code', 'N/A')})] "
            f"{m['symptom_name']}: {m['description']}"
        )
    return "\n".join(righe)


def formatta_differenziale(candidate: list[dict], ambiguita: dict) -> str:
    """Formatta la differenziale diagnostica pesata (IDF + aggregazione) per il prompt LLM."""
    if not candidate:
        return ""

    righe = ["\n\n### DIAGNOSI DIFFERENZIALE CANDIDATA (retrieval pesato IDF, non conclusiva):"]
    for i, c in enumerate(candidate, start=1):
        sintomi = ", ".join(c["sintomi"])
        righe.append(
            f"{i}. {c['diagnosis_name']} ({c.get('diagnostic_code', 'N/A')}) — "
            f"rilevanza {c['punteggio_norm']}/100, {c['n_sintomi_match']} sintomi corrispondenti: {sintomi}\n"
            f"   soglia DSM: \"{c.get('threshold_count', 'N/A')}\"; durata: \"{c.get('duration_rule', 'N/A')}\""
        )

    if ambiguita.get("ambiguita") is not None:
        righe.append(f"\nIndice di ambiguità: {ambiguita['ambiguita']}/100 ({ambiguita['descrizione']}).")

    return "\n".join(righe)
