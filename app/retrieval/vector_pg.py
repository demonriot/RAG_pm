from typing import Any, Dict, List

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.chunk import Chunk
from app.db.models.embedding import ChunkEmbedding


def vector_search_pg(query_embedding: list[float], k: int = 10) -> List[Dict[str, Any]]:
    """
    Returns top-k chunks by pgvector cosine distance.
    Smaller distance = more similar.
    """
    db = SessionLocal()
    try:
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
                Chunk.doc_type,
                Chunk.course_code,
                Chunk.program_name,
                Chunk.source_url,
                Chunk.accessed_date,
                Chunk.catalog_year,
                Chunk.citation_label,
                Chunk.section,
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
                "doc_type": r.doc_type,
                "course_code": r.course_code,
                "program_name": r.program_name,
                "source_url": r.source_url,
                "accessed_date": r.accessed_date,
                "catalog_year": r.catalog_year,
                "citation_label": r.citation_label,
                "section": r.section,
            }
            for r in rows
        ]
    finally:
        db.close()