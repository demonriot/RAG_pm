import os
from typing import Any, Dict, List

from app.retrieval.vector_pg import vector_search_pg
from app.retrieval.vector_faiss import vector_search_faiss


def vector_search(query_embedding: list[float], k: int = 10) -> List[Dict[str, Any]]:
    """
    Dispatch vector retrieval based on VECTOR_BACKEND.
    Supported:
      - pgvector
      - faiss
    """
    backend = os.getenv("VECTOR_BACKEND", "pgvector").strip().lower()

    if backend == "faiss":
        return vector_search_faiss(query_embedding=query_embedding, k=k)

    return vector_search_pg(query_embedding=query_embedding, k=k)