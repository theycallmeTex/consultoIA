"""Indicizza dsm5_tr_data/diagnoses.json su Qdrant, un punto per ogni sintomo.

Uso: python -m rag.ingest   (dalla cartella backend/, con il venv attivo)
"""

import json
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client.models import PointStruct

load_dotenv()

from .embeddings import embed_documents
from .qdrant_store import VECTOR_NAME, COLLECTION, ensure_collection, get_client

DATASET_PATH = Path(__file__).resolve().parents[1] / "dsm5_tr_data" / "diagnoses.json"
BATCH_SIZE = 90  # limite pratico per richiesta Cohere


def carica_record():
    with open(DATASET_PATH, encoding="utf-8") as f:
        diagnosi = json.load(f)

    record = []
    for dx in diagnosi:
        for sintomo in dx.get("symptoms", []):
            testo = f"{dx['diagnosis_name']} — {sintomo['symptom_name']}: {sintomo['description']}"
            record.append({
                "text": testo,
                "payload": {
                    "diagnosis_id": dx["diagnosis_id"],
                    "diagnosis_name": dx["diagnosis_name"],
                    "diagnostic_code": dx.get("diagnostic_code"),
                    "chapter_category": dx.get("chapter_category"),
                    "threshold_count": dx.get("threshold_count"),
                    "duration_rule": dx.get("duration_rule"),
                    "symptom_id": sintomo["symptom_id"],
                    "symptom_name": sintomo["symptom_name"],
                    "description": sintomo["description"],
                },
            })
    return record


def main():
    record = carica_record()
    print(f"Trovati {len(record)} sintomi da indicizzare da {DATASET_PATH.name}.")

    ensure_collection(recreate=True)
    client = get_client()

    punto_id = 0
    for i in range(0, len(record), BATCH_SIZE):
        batch = record[i:i + BATCH_SIZE]
        vettori = embed_documents([r["text"] for r in batch])

        punti = [
            PointStruct(id=punto_id + j, vector={VECTOR_NAME: vec}, payload=rec["payload"])
            for j, (rec, vec) in enumerate(zip(batch, vettori))
        ]
        client.upsert(collection_name=COLLECTION, points=punti)
        punto_id += len(batch)
        print(f"Indicizzati {punto_id}/{len(record)}")

    print("Completato.")


if __name__ == "__main__":
    main()
