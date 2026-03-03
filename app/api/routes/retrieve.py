# app/api/routes/retrieve.py
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.embeddings.provider import embed_texts, get_embedding_model
from app.retrieval.vector import vector_search
from app.retrieval.lexical import lexical_search
from app.retrieval.hybrid import hybrid_search_rrf
from app.confidence.retrieval import compute_retrieval_confidence

from app.rerank.config import (
    get_rerank_fail_open,
    get_rerank_max_chars,
    get_rerank_model,
    get_rerank_per_doc_cap,
    get_rerank_top_n,
    get_rerank_max_vector_distance,
)
from app.rerank.eligibility import should_apply_rerank
from app.rerank.provider import VoyageRerankProvider
from app.rerank.rerank import rerank_hits_with_diversity

router = APIRouter(prefix="/retrieve", tags=["retrieve"])


class VectorRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)
    k: int = Field(10, ge=1, le=50)


class HybridRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)

    k_vector: int = Field(40, ge=1, le=50)
    k_lexical: int = Field(40, ge=1, le=50)
    k_final: int = Field(20, ge=1, le=50)
    rrf_k: int = Field(60, ge=1, le=200)


@router.post("/vector")
def retrieve_vector(req: VectorRetrieveRequest):
    model = get_embedding_model()
    q_emb = embed_texts([req.query], model=model)[0]
    hits = vector_search(q_emb, k=req.k)
    return {"model": model, "k": req.k, "hits": hits}


@router.post("/lexical")
def retrieve_lexical(req: VectorRetrieveRequest):
    hits = lexical_search(req.query, k=req.k)
    return {"k": req.k, "hits": hits}


def _best_vector_distance(hits):
    # Prefer vector_rank==1 if present; else min distance; else None.
    for h in hits:
        if h.get("vector_rank") == 1 and h.get("distance") is not None:
            return float(h["distance"])
    dists = [float(h["distance"]) for h in hits if h.get("distance") is not None]
    return min(dists) if dists else None


@router.post("/hybrid")
def retrieve_hybrid(req: HybridRetrieveRequest):
    model = get_embedding_model()
    q_emb = embed_texts([req.query], model=model)[0]

    hits = hybrid_search_rrf(
        query=req.query,
        query_embedding=q_emb,
        k_vector=req.k_vector,
        k_lexical=req.k_lexical,
        k_final=req.k_final,
        rrf_k=req.rrf_k,
    )

    # Step 4: Rerank hybrid candidates
    rerank_model = get_rerank_model()
    top_n = get_rerank_top_n()
    per_doc_cap = get_rerank_per_doc_cap()
    max_chars = get_rerank_max_chars()
    fail_open = get_rerank_fail_open()
    max_vec_dist = get_rerank_max_vector_distance()

    eligible, reason = should_apply_rerank(
        query=req.query,
        hits=hits,
        max_vector_distance=max_vec_dist,
    )

    best_distance = _best_vector_distance(hits)

    rerank_applied = False
    rerank_error = None

    if eligible:
        try:
            provider = VoyageRerankProvider(model=rerank_model)
            hits = rerank_hits_with_diversity(
                query=req.query,
                hits=hits,
                provider=provider,
                top_n=top_n,
                per_doc_cap=per_doc_cap,
                max_chars=max_chars,
            )
            rerank_applied = True
            reason = "ok"
        except Exception as e:
            if not fail_open:
                raise
            rerank_error = str(e)
    
    retrieval_confidence = compute_retrieval_confidence(
    hits=hits,
    rerank_applied=rerank_applied,
    )

    return {
        "model": model,
        "k_vector": req.k_vector,
        "k_lexical": req.k_lexical,
        "k_final": req.k_final,
        "rrf_k": req.rrf_k,
        "rerank": {
            "eligible": eligible,
            "applied": rerank_applied,
            "reason": reason,
            "model": rerank_model,
            "top_n": top_n,
            "per_doc_cap": per_doc_cap,
            "max_chars": max_chars,
            "max_vector_distance": max_vec_dist,
            "best_vector_distance": best_distance,
            "error": rerank_error,
        },
        "hits": hits,
        "retrieval_confidence": retrieval_confidence,
    }