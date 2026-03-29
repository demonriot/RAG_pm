from __future__ import annotations

from typing import List

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.chunk import Chunk
from app.planning.eligibility_planner import normalize_course_code


def get_recommendation_candidates(
    *,
    completed_courses: List[str],
    subject_prefix: str | None = "CS",
) -> List[str]:
    completed_set = {normalize_course_code(c) for c in completed_courses}

    db = SessionLocal()
    try:
        stmt = (
            select(Chunk.course_code)
            .where(Chunk.doc_type == "course")
            .where(Chunk.course_code != None)  # noqa: E711
            .distinct()
        )

        if subject_prefix:
            stmt = stmt.where(Chunk.course_code.like(f"{subject_prefix} %"))

        rows = db.execute(stmt).all()

        codes = []
        seen = set()

        for (course_code,) in rows:
            normalized = normalize_course_code(course_code or "")
            if not normalized:
                continue
            if normalized in completed_set:
                continue
            if normalized in seen:
                continue

            seen.add(normalized)
            codes.append(normalized)

        return sorted(codes)
    finally:
        db.close()