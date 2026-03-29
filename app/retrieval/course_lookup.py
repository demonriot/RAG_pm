# app/retrieval/course_lookup.py

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.chunk import Chunk


def normalize_course_code(course_code: str) -> str:
    if not course_code:
        return ""

    raw = course_code.upper().strip()
    raw = " ".join(raw.split())

    m = re.fullmatch(r"([A-Z]{2,4})\s?(\d{3}[A-Z]?)", raw)
    if m:
        return f"{m.group(1)} {m.group(2)}"

    return raw


def _row_to_chunk_dict(row: Any) -> Dict[str, Any]:
    r = row._mapping if hasattr(row, "_mapping") else row

    return {
        "chunk_id": str(r["id"]),
        "document_id": str(r["document_id"]),
        "version_id": str(r["version_id"]),
        "chunk_index": r["chunk_index"],
        "section_path": r["section_path"],
        "page_range": r["page_range"],
        "content_hash": str(r["content_hash"]) if r["content_hash"] is not None else None,
        "content": r["content"],
        "text": r["content"],
        "tags": r["tags"],

        "doc_type": r["doc_type"],
        "course_code": r["course_code"],
        "program_name": r["program_name"],
        "source_url": r["source_url"],
        "accessed_date": r["accessed_date"],
        "catalog_year": r["catalog_year"],
        "citation_label": r["citation_label"],
        "section": r["section"],
        "title": r["section"],
        "section_parser": r["section_parser"],
        "subchunk_index": r["subchunk_index"],
    }


def get_course_chunk_by_code(course_code: str) -> Optional[Dict[str, Any]]:
    normalized_code = normalize_course_code(course_code)
    if not normalized_code:
        return None

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
                Chunk.section_parser,
                Chunk.subchunk_index,
            )
            .where(Chunk.doc_type == "course")
            .where(Chunk.course_code == normalized_code)
            .order_by(Chunk.chunk_index.asc())
            .limit(1)
        )

        row = db.execute(stmt).first()
        if row is None:
            return None

        return _row_to_chunk_dict(row)

    finally:
        db.close()