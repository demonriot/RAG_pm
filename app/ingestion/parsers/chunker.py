from __future__ import annotations

import re
from typing import List, Optional

from app.ingestion.schemas.catalog_models import CatalogChunk, CatalogSection


COURSE_CODE_PATTERN = re.compile(r"^([A-Z]{2,4}\s+\d+[A-Z]{0,2})\s*,")


def extract_course_code_from_heading(heading: str) -> Optional[str]:
    match = COURSE_CODE_PATTERN.match(heading.strip())
    if not match:
        return None
    return match.group(1)


def _split_text_with_overlap(
    text: str,
    max_chars: int = 1200,
    overlap: int = 150,
) -> List[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + max_chars, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        start = max(0, end - overlap)

    return chunks


def build_citation_label(
    *,
    title: str,
    section: Optional[str] = None,
    course_code: Optional[str] = None,
    program_name: Optional[str] = None,
) -> str:
    if course_code and section:
        return f"{course_code} | {section}"
    if course_code:
        return course_code
    if program_name and section:
        return f"{program_name} | {section}"
    if program_name:
        return program_name
    if section:
        return f"{title} | {section}"
    return title


def section_to_chunks(
    *,
    section: CatalogSection,
    doc_type: str,
    title: str,
    source_url: str,
    accessed_date: str,
    start_chunk_index: int,
    course_code: Optional[str] = None,
    program_name: Optional[str] = None,
    catalog_year: Optional[str] = None,
    max_chars: int = 1200,
    overlap: int = 150,
) -> List[CatalogChunk]:
    effective_course_code = course_code
    if doc_type == "course":
        effective_course_code = extract_course_code_from_heading(section.heading) or course_code

    chunk_texts = _split_text_with_overlap(
        section.text,
        max_chars=max_chars,
        overlap=overlap,
    )

    chunks: List[CatalogChunk] = []
    for offset, chunk_text in enumerate(chunk_texts):
        citation_label = build_citation_label(
            title=title,
            section=section.heading,
            course_code=effective_course_code,
            program_name=program_name,
        )

        chunks.append(
            CatalogChunk(
                doc_type=doc_type,
                title=title,
                source_url=source_url,
                accessed_date=accessed_date,
                chunk_index=start_chunk_index + offset,
                text=chunk_text,
                citation_label=citation_label,
                section=section.heading,
                course_code=effective_course_code,
                program_name=program_name,
                catalog_year=catalog_year,
                metadata={
                    "section_order": section.order,
                    "section_parser": section.metadata.get("parser"),
                    "subchunk_index": offset,
                },
            )
        )

    return chunks


def build_chunks(
    *,
    sections: List[CatalogSection],
    doc_type: str,
    title: str,
    source_url: str,
    accessed_date: str,
    course_code: Optional[str] = None,
    program_name: Optional[str] = None,
    catalog_year: Optional[str] = None,
    max_chars: int = 1200,
    overlap: int = 150,
) -> List[CatalogChunk]:
    all_chunks: List[CatalogChunk] = []
    next_chunk_index = 0

    for section in sections:
        section_chunks = section_to_chunks(
            section=section,
            doc_type=doc_type,
            title=title,
            source_url=source_url,
            accessed_date=accessed_date,
            start_chunk_index=next_chunk_index,
            course_code=course_code,
            program_name=program_name,
            catalog_year=catalog_year,
            max_chars=max_chars,
            overlap=overlap,
        )
        all_chunks.extend(section_chunks)
        next_chunk_index += len(section_chunks)

    return all_chunks