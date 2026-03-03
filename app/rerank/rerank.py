# app/rerank/rerank.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.rerank.provider import VoyageRerankProvider


def _truncate(s: str, max_chars: int) -> str:
    s = s or ""
    if max_chars <= 0:
        return s
    return s if len(s) <= max_chars else s[:max_chars]


def rerank_hits_with_diversity(
    *,
    query: str,
    hits: Sequence[Dict[str, Any]],
    provider: VoyageRerankProvider,
    top_n: int,
    per_doc_cap: int,
    max_chars: int,
) -> List[Dict[str, Any]]:
    """
    - Calls Voyage rerank on hit["content"]
    - Adds rerank_score + rerank_rank
    - Sorts by rerank_score desc
    - Enforces <= per_doc_cap per document_id
    - Returns top_n
    """
    if not hits:
        return []

    # Build documents list aligned to hits list
    docs: List[str] = []
    for h in hits:
        docs.append(_truncate(str(h.get("content", "")), max_chars=max_chars))

    reranked = provider.rerank(query=query, documents=docs, top_k=None)

    # Map index->score (Voyage returns indices into docs list)
    score_by_idx: Dict[int, float] = {item.index: item.score for item in reranked}

    # Attach score; if missing, set very low score (should be rare)
    enriched: List[Dict[str, Any]] = []
    for i, h in enumerate(hits):
        hh = dict(h)
        hh["rerank_score"] = float(score_by_idx.get(i, float("-inf")))
        enriched.append(hh)

    def sort_key(h: Dict[str, Any]) -> Tuple[float, float, int, str]:
        # Deterministic tie-break:
        # 1) rerank_score desc
        # 2) rrf_score desc (preserve your fusion info)
        # 3) best_rank asc (vector/lexical)
        # 4) chunk_id asc
        rerank_score = float(h.get("rerank_score", float("-inf")))
        rrf_score = float(h.get("rrf_score", 0.0))

        vr = h.get("vector_rank")
        lr = h.get("lexical_rank")
        best_rank = min([r for r in (vr, lr) if isinstance(r, int)], default=10**9)

        cid = str(h.get("chunk_id", ""))
        return (-rerank_score, -rrf_score, best_rank, cid)

    enriched.sort(key=sort_key)

    # Diversity cap per document
    out: List[Dict[str, Any]] = []
    doc_counts: Dict[str, int] = {}

    for h in enriched:
        doc_id = str(h.get("document_id", ""))
        if per_doc_cap > 0:
            if doc_counts.get(doc_id, 0) >= per_doc_cap:
                continue
        doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
        out.append(h)
        if len(out) >= top_n:
            break

    # Add rerank_rank (1-based) after diversity filtering
    for i, h in enumerate(out, start=1):
        h["rerank_rank"] = i

    return out