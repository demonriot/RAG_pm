from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.chunk import Chunk

db = SessionLocal()
try:
    row = db.execute(
        select(
            Chunk.course_code,
            Chunk.doc_type,
            Chunk.citation_label,
            Chunk.source_url,
            Chunk.catalog_year,
            Chunk.section,
            Chunk.section_parser,
            Chunk.subchunk_index,
        )
        .where(Chunk.course_code == "CS 161")
        .where(Chunk.doc_type == "course")
        .limit(1)
    ).first()

    print(row)
finally:
    db.close()