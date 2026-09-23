import os

import cohere

_client = None


def _get_client() -> cohere.ClientV2:
    global _client
    if _client is None:
        _client = cohere.ClientV2(api_key=os.environ["COHERE_API_KEY"])
    return _client


def _embed(texts: list[str], input_type: str) -> list[list[float]]:
    model = os.getenv("COHERE_EMBED_MODEL", "embed-multilingual-v3.0")
    response = _get_client().embed(
        texts=texts,
        model=model,
        input_type=input_type,
        embedding_types=["float"],
    )
    return response.embeddings.float_


def embed_documents(texts: list[str]) -> list[list[float]]:
    return _embed(texts, "search_document")


def embed_query(text: str) -> list[float]:
    return _embed([text], "search_query")[0]


def embed_queries(texts: list[str]) -> list[list[float]]:
    return _embed(texts, "search_query")
