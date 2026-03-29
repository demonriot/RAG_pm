import json
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.chunk import Chunk


FAISS_DIR = Path("data/faiss")
INDEX_PATH = FAISS_DIR / "chunks.index"
IDMAP_PATH = FAISS_DIR / "id_map.json"


def _load_faiss_assets():
    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"FAISS index not found at {INDEX_PATH}. "
            f"Run: python -m app.indexing.build_faiss"
        )

    if not IDMAP_PATH.exists():
        raise FileNotFoundError(
            f"FAISS id map not found at {IDMAP_PATH}. "
            f"Run: python -m app.indexing.build_faiss"
        )

    index = faiss.read_index(str(INDEX_PATH))

    with open(IDMAP_PATH, "r", encoding="utf-8") as f:
        id_map = json.load(f)

    return index, id_map


def vector_search_faiss(query_embedding: list[float], k: int = 10) -> List[Dict[str, Any]]:
    """
    Returns top-k chunks by FAISS inner product on normalized vectors.
    Higher score = more similar.
    Exposes distance = 1 - score for compatibility with existing code.
    """
    index, id_map = _load_faiss_assets()

    q = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
    faiss.normalize_L2(q)

    scores, indices = index.search(q, k)

    ordered_chunk_ids: list[str] = []
    score_by_chunk_id: dict[str, float] = {}

    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        chunk_id = id_map.get(str(idx))
        if not chunk_id:
            continue

        ordered_chunk_ids.append(chunk_id)
        score_by_chunk_id[chunk_id] = float(score)

    if not ordered_chunk_ids:
        return []

    db = SessionLocal()
    try:
        stmt = select(
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
        ).where(Chunk.id.in_(ordered_chunk_ids))

        rows = db.execute(stmt).all()
        row_by_chunk_id = {str(r.id): r for r in rows}

        out: list[dict[str, Any]] = []
        for chunk_id in ordered_chunk_ids:
            r = row_by_chunk_id.get(chunk_id)
            if r is None:
                continue

            score = score_by_chunk_id[chunk_id]

            out.append(
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
                    "distance": float(1.0 - score),
                    "score": float(score),
                    "doc_type": r.doc_type,
                    "course_code": r.course_code,
                    "program_name": r.program_name,
                    "source_url": r.source_url,
                    "accessed_date": r.accessed_date,
                    "catalog_year": r.catalog_year,
                    "citation_label": r.citation_label,
                    "section": r.section,
                }
            )

        return out
    finally:
        db.close()