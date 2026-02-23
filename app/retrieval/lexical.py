from typing import Any, Dict, List
from sqlalchemy import select, func

from app.db.session import SessionLocal
from app.db.models.chunk import Chunk


def lexical_search(query: str, k: int = 10) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        ts_query = func.websearch_to_tsquery("simple", query)

        rank_expr = func.ts_rank_cd(Chunk.content_tsv, ts_query)

        stmt = (
            select(
                Chunk.id,
                Chunk.document_id,
                Chunk.version_id,
                Chunk.chunk_index,
                Chunk.section_path,
                Chunk.page_range,
                Chunk.content,
                Chunk.content_hash,
                Chunk.tags,
                rank_expr.label("rank"),
            )
            .where(Chunk.content_tsv.op("@@")(ts_query))
            .order_by(rank_expr.desc())
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
                "rank": float(r.rank),
            }
            for r in rows
        ]
    finally:
        db.close()