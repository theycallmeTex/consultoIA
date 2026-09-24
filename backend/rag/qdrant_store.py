import os
from urllib.parse import urlparse

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

COLLECTION = os.getenv("QDRANT_COLLECTION", "dsm5_symptoms")
VECTOR_NAME = "semantic"
VECTOR_SIZE = 1024  # embed-multilingual-v3.0

_client = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        url = os.environ["QDRANT_URL"].strip()
        # Senza porta esplicita il client userebbe la 6333, spesso bloccata da reti/firewall: Qdrant Cloud risponde anche sulla 443.
        port = None if urlparse(url).port else 443
        _client = QdrantClient(url=url, port=port, api_key=os.environ["QDRANT_API_KEY"])
    return _client


def ensure_collection(recreate: bool = False) -> None:
    client = get_client()
    exists = client.collection_exists(COLLECTION)
    if exists and recreate:
        client.delete_collection(COLLECTION)
        exists = False
    if not exists:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config={VECTOR_NAME: VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)},
        )
