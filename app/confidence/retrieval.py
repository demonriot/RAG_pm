# app/confidence/retrieval.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _has_lexical(hits: Sequence[Dict[str, Any]]) -> bool:
    return any(h.get("lexical_rank") is not None for h in hits)


def _best_vector_distance(hits: Sequence[Dict[str, Any]]) -> Optional[float]:
    # Prefer vector_rank==1 if present; else min distance; else None.
    for h in hits:
        if h.get("vector_rank") == 1 and h.get("distance") is not None:
            return float(h["distance"])
    dists = [float(h["distance"]) for h in hits if h.get("distance") is not None]
    return min(dists) if dists else None


def _top_rerank_scores(hits: Sequence[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
    scores = [float(h["rerank_score"]) for h in hits if h.get("rerank_score") is not None]
    if not scores:
        return None, None
    scores.sort(reverse=True)
    top1 = scores[0]
    top2 = scores[1] if len(scores) > 1 else None
    return top1, top2


def compute_retrieval_confidence(
    *,
    hits: Sequence[Dict[str, Any]],
    rerank_applied: bool,
) -> Dict[str, Any]:
    """
    Heuristic retrieval confidence for Step 4.5.
    - score in [0,1]
    - label in {HIGH, MEDIUM, LOW}
    - reasons: human-readable diagnostics
    """
    reasons: List[str] = []

    if not hits:
        return {
            "label": "LOW",
            "score": 0.0,
            "signals": {
                "has_lexical": False,
                "best_vector_distance": None,
                "rerank_applied": rerank_applied,
                "top_rerank_score": None,
                "rerank_gap": None,
            },
            "reasons": ["no_hits"],
        }

    has_lex = _has_lexical(hits)
    best_dist = _best_vector_distance(hits)

    top1, top2 = _top_rerank_scores(hits) if rerank_applied else (None, None)
    gap = (top1 - top2) if (top1 is not None and top2 is not None) else None

    # --- Scoring components (simple + tunable) ---
    # Vector distance mapping: lower distance => higher confidence.
    # Based on your observed distances: ~0.4 strong, ~0.7 weak, ~0.9 very weak.
    if best_dist is None:
        vec_score = 0.2
        reasons.append("missing_vector_distance")
    else:
        # Map [0.35 .. 0.85] roughly to [1.0 .. 0.0]
        vec_score = 1.0 - ((best_dist - 0.35) / 0.50)
        vec_score = _clamp01(vec_score)
        if best_dist <= 0.55:
            reasons.append("good_vector_match")
        elif best_dist <= 0.70:
            reasons.append("ok_vector_match")
        else:
            reasons.append("weak_vector_match")

    lex_score = 1.0 if has_lex else 0.0
    if has_lex:
        reasons.append("lexical_support")
    else:
        reasons.append("no_lexical_support")

    # Rerank quality: if rerank applied and top score separates from runner-up, good signal.
    rerank_score = 0.0
    if rerank_applied and top1 is not None:
        # If only one result, treat as moderate.
        if gap is None:
            rerank_score = 0.5
            reasons.append("rerank_single_or_no_gap")
        else:
            # Gap mapping: [0.0 .. 0.3] -> [0.0 .. 1.0]
            rerank_score = _clamp01(gap / 0.30)
            if gap >= 0.15:
                reasons.append("rerank_separates_top")
            else:
                reasons.append("rerank_weak_separation")
    else:
        reasons.append("rerank_not_applied")

    # Weighted blend (kept simple, can tune later)
    # Vector is the backbone signal; rerank helps; lexical boosts.
    score = (
        0.55 * vec_score +
        0.25 * rerank_score +
        0.20 * lex_score
    )
    score = _clamp01(score)

    if score >= 0.75:
        label = "HIGH"
    elif score >= 0.45:
        label = "MEDIUM"
    else:
        label = "LOW"

    return {
        "label": label,
        "score": float(score),
        "signals": {
            "has_lexical": has_lex,
            "best_vector_distance": best_dist,
            "rerank_applied": rerank_applied,
            "top_rerank_score": top1,
            "rerank_gap": gap,
        },
        "reasons": reasons,
    }