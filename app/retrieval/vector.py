# app/retrieval/vector.py
import uuid
from typing import Any, Dict, List

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.chunk import Chunk
from app.db.models.embedding import ChunkEmbedding


def vector_search(query_embedding: list[float], k: int = 10) -> List[Dict[str, Any]]:
    """
    Returns top-k chunks by vector similarity (cosine distance).
    """
    db = SessionLocal()
    try:
        # pgvector operator:
        #   cosine distance: <=> (smaller is more similar)
        stmt = (
            select(
                Chunk.id,
                Chunk.document_id,
                Chunk.version_id,
                Chunk.chunk_index,
                Chunk.section_path,
                Chunk.page_range,
                Chunk.content_hash,
                Chunk.content,
                Chunk.tags,
                ChunkEmbedding.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
            .order_by(ChunkEmbedding.embedding.cosine_distance(query_embedding).asc())
            .limit(k)
        )

        rows = db.execute(stmt).all()
        return [
            {
                "chunk_id": str(r.id),
                "document_id": str(r.document_id),
                "version_id": str(r.version_id),
                "chunk_index": r.chunk_index,
                "section_path": r.section_path,
                "page_range": r.page_range,
                "tags": r.tags,
                "content": r.content,
                "content_hash": str(r.content_hash),
                "distance": float(r.distance),
            }
            for r in rows
        ]
    finally:
        db.close()