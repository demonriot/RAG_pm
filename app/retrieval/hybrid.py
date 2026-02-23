# app/retrieval/hybrid.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.retrieval.vector import vector_search
from app.retrieval.lexical import lexical_search


def _rrf_term(rank_1_based: int, rrf_k: int) -> float:
    return 1.0 / float(rrf_k + rank_1_based)


def hybrid_search_rrf(
    *,
    query: str,
    query_embedding: List[float],
    k_vector: int = 40,
    k_lexical: int = 40,
    k_final: int = 20,
    rrf_k: int = 60,
) -> List[Dict[str, Any]]:
    vec_hits = vector_search(query_embedding, k=k_vector)  # best -> worst
    lex_hits = lexical_search(query, k=k_lexical)          # best -> worst

    vec_rank: Dict[str, int] = {}
    vec_map: Dict[str, Dict[str, Any]] = {}
    for i, h in enumerate(vec_hits, start=1):
        cid = h["chunk_id"]
        vec_rank[cid] = i
        vec_map[cid] = h

    lex_rank: Dict[str, int] = {}
    lex_map: Dict[str, Dict[str, Any]] = {}
    for i, h in enumerate(lex_hits, start=1):
        cid = h["chunk_id"]
        lex_rank[cid] = i
        lex_map[cid] = h

    candidate_ids = set(vec_rank.keys()) | set(lex_rank.keys())

    fused: List[Tuple[str, float]] = []
    for cid in candidate_ids:
        score = 0.0
        vr = vec_rank.get(cid)
        lr = lex_rank.get(cid)

        if vr is not None:
            score += _rrf_term(vr, rrf_k)
        if lr is not None:
            score += _rrf_term(lr, rrf_k)

        fused.append((cid, score))

    def sort_key(item: Tuple[str, float]):
        cid, score = item
        vr = vec_rank.get(cid)
        lr = lex_rank.get(cid)
        best_rank = min([r for r in (vr, lr) if r is not None], default=10**9)
        return (-score, best_rank, cid)

    fused.sort(key=sort_key)

    # Deduplicate by content_hash and collect k_final
    seen_hashes = set()
    out: List[Dict[str, Any]] = []

    for cid, score in fused:
        base = vec_map.get(cid) or lex_map.get(cid)
        if base is None:
            continue

        content_hash = base.get("content_hash") or cid  # fallback if missing

        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)

        hit = dict(base)
        hit["vector_rank"] = vec_rank.get(cid)
        hit["lexical_rank"] = lex_rank.get(cid)
        hit["rrf_score"] = float(score)

        out.append(hit)

        if len(out) >= k_final:
            break

    return out