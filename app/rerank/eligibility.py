# app/rerank/eligibility.py
from __future__ import annotations

from typing import Any, Dict, Sequence, Tuple


def _looks_like_gibberish(q: str) -> bool:
    t = q.strip().lower()
    if not t:
        return True

    # only treat as gibberish for single-token alpha strings
    if (" " in t) or (not t.isalpha()):
        return False

    if len(t) >= 8:
        vowels = sum(ch in "aeiou" for ch in t)
        unique_ratio = len(set(t)) / len(t)
        if vowels <= 1 or unique_ratio < 0.35:
            return True

    return False


def should_apply_rerank(
    *,
    query: str,
    hits: Sequence[Dict[str, Any]],
    max_vector_distance: float,
) -> Tuple[bool, str]:
    q = (query or "").strip()
    if not q:
        return False, "empty_query"
    if len(q) < 3:
        return False, "query_too_short"
    if not hits:
        return False, "no_hits"

    if _looks_like_gibberish(q):
        return False, "gibberish_query"

    # lexical signal
    has_lexical = any(h.get("lexical_rank") is not None for h in hits)

    # vector signal
    best_distance = None
    for h in hits:
        if h.get("vector_rank") == 1 and h.get("distance") is not None:
            best_distance = float(h["distance"])
            break
    if best_distance is None:
        distances = [float(h["distance"]) for h in hits if h.get("distance") is not None]
        best_distance = min(distances) if distances else None

    # Skip only if BOTH signals are weak
    if (not has_lexical) and (best_distance is None or best_distance > max_vector_distance):
        return False, "no_lexical_and_weak_vector"

    return True, "ok"