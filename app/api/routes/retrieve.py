# app/api/routes/retrieve.py
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.embeddings.provider import embed_texts, get_embedding_model
from app.retrieval.vector import vector_search
from app.retrieval.lexical import lexical_search
from app.retrieval.hybrid import hybrid_search_rrf

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

    return {
        "model": model,
        "k_vector": req.k_vector,
        "k_lexical": req.k_lexical,
        "k_final": req.k_final,
        "rrf_k": req.rrf_k,
        "hits": hits,
    }