# app/rerank/provider.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import voyageai


@dataclass(frozen=True)
class RerankItem:
    index: int          # index into the input documents list
    score: float        # higher = more relevant


class VoyageRerankProvider:
    """
    Thin wrapper around Voyage rerank API.
    """

    def __init__(self, *, model: str, api_key: Optional[str] = None) -> None:
        # voyageai.Client() will use VOYAGE_API_KEY env var automatically if api_key is None.
        self._client = voyageai.Client(api_key=api_key)  # type: ignore[arg-type]
        self._model = model

    def rerank(
        self,
        *,
        query: str,
        documents: Sequence[str],
        top_k: Optional[int] = None,
    ) -> List[RerankItem]:
        if not query.strip():
            raise ValueError("query must be non-empty")
        if not documents:
            return []

        # Voyage rerank endpoint expects query + list of documents + model name. :contentReference[oaicite:3]{index=3}
        resp = self._client.rerank(
            query=query,
            documents=list(documents),
            model=self._model,
            top_k=top_k,
        )

        # The python client returns an object with "results" including index + relevance_score.
        # We keep only what we need, and make it stable for the rest of the codebase.
        items: List[RerankItem] = []
        for r in resp.results:
            items.append(RerankItem(index=int(r.index), score=float(r.relevance_score)))
        return items