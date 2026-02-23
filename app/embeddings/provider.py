# app/embeddings/provider.py
import os
import time
from typing import List

import requests


OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


def get_embedding_model() -> str:
    # 1536 dims, matches your Vector(1536)
    return os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def embed_texts(texts: List[str], *, model: str | None = None, max_retries: int = 5) -> List[List[float]]:
    """
    Returns a list of embeddings aligned with input texts.
    Uses OpenAI embeddings REST API.
    """
    if os.getenv("DISABLE_EMBEDDING", "false") == "true":
        print("[embed-worker] embedding disabled", flush=True)
        return []
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    
    

    model = model or get_embedding_model()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "input": texts,
    }

    backoff = 1.0
    for attempt in range(max_retries):
        try:
            resp = requests.post(OPENAI_EMBEDDINGS_URL, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429 or resp.status_code >= 500:
                # rate limit / transient server errors
                time.sleep(backoff)
                backoff = min(backoff * 2, 20)
                continue

            resp.raise_for_status()
            data = resp.json()

            # OpenAI returns data: [{embedding: [...], index: 0}, ...]
            items = data["data"]
            items.sort(key=lambda x: x["index"])
            return [it["embedding"] for it in items]

        except requests.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 20)

    raise RuntimeError("Embedding retries exhausted")