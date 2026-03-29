import uuid
import hashlib
from datetime import datetime

from sqlalchemy import update

from app.db.session import SessionLocal
from app.db.models.document_version import DocumentVersion
from app.db.models.chunk import Chunk
from app.ingestion.queue import dequeue_job_blocking, enqueue_embed_job
from app.ingestion.storage import download_bytes

from app.ingestion.parsers.html_cleaner import clean_html
from app.ingestion.parsers.section_parser import parse_sections
from app.ingestion.parsers.chunker import build_chunks


def parse_bytes(file_type: str, data: bytes) -> str:
    """
    Decode raw file bytes into text.
    For now, catalog ingestion uses HTML.
    """
    if file_type in ("txt", "md", "html"):
        return data.decode("utf-8", errors="ignore")
    raise ValueError(f"unsupported_file_type:{file_type}")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def simple_chunk(text: str, max_chars: int = 2000, overlap: int = 200):
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(n, i + max_chars)
        chunks.append(text[i:j])
        if j == n:
            break
        i = max(0, j - overlap)
    return chunks


def _merge_tags(*tag_groups):
    out = []
    seen = set()

    for group in tag_groups:
        if not group:
            continue
        for tag in group:
            if not tag:
                continue
            if tag not in seen:
                seen.add(tag)
                out.append(tag)

    return out or None


def build_catalog_chunks(job: dict, raw_text: str):
    """
    Build structured chunks for OSU catalog ingestion.
    """
    catalog_doc_type = job["catalog_doc_type"]  # course / program / policy

    parsed_title, clean_text = clean_html(raw_text)
    sections = parse_sections(clean_text, catalog_doc_type)

    structured_chunks = build_chunks(
        sections=sections,
        doc_type=catalog_doc_type,
        title=parsed_title,
        source_url=job["source_url"],
        accessed_date=job["accessed_date"],
        course_code=job.get("course_code"),
        program_name=job.get("program_name"),
        catalog_year=job.get("catalog_year"),
        max_chars=1200,
        overlap=150,
    )

    return parsed_title, clean_text, structured_chunks


def run_once(job: dict):
    print(f"[ingest-worker] processing {job['version_id']}", flush=True)
    db = SessionLocal()
    ver_id = uuid.UUID(job["version_id"])

    try:
        # mark processing
        db.execute(
            update(DocumentVersion)
            .where(DocumentVersion.id == ver_id)
            .values(status="processing", error_code=None)
        )
        db.commit()

        data = download_bytes(job["bucket"], job["key"])
        raw_text = parse_bytes(job["file_type"], data)

        if job.get("source_type") == "osu_catalog":
            parsed_title, clean_text, structured_chunks = build_catalog_chunks(job, raw_text)

            for idx, chunk in enumerate(structured_chunks):
                metadata = chunk.metadata or {}
                print(
                        {
                            "idx": idx,
                            "doc_type": getattr(chunk, "doc_type", None),
                            "course_code": getattr(chunk, "course_code", None),
                            "program_name": getattr(chunk, "program_name", None),
                            "source_url": getattr(chunk, "source_url", None),
                            "accessed_date": getattr(chunk, "accessed_date", None),
                            "catalog_year": getattr(chunk, "catalog_year", None),
                            "citation_label": getattr(chunk, "citation_label", None),
                            "section": getattr(chunk, "section", None),
                            "metadata": getattr(chunk, "metadata", None),
                            "text_preview": (getattr(chunk, "text", "") or "")[:120],
                        },
                        flush=True,
                    )

                # Keep tags only as optional loose labels
                tags = _merge_tags(
                    job.get("tags"),
                    [
                        f"catalog_doc_type:{chunk.doc_type}" if chunk.doc_type else None,
                        f"section_parser:{metadata.get('section_parser')}" if metadata.get("section_parser") else None,
                    ],
                )

                ch = Chunk(
                    id=uuid.uuid4(),
                    document_id=uuid.UUID(job["doc_id"]),
                    version_id=ver_id,
                    chunk_index=idx,
                    section_path=chunk.section,
                    page_range=None,
                    content_hash=sha256_text(chunk.text),
                    content=chunk.text,
                    token_count=None,
                    tags=tags,

                    # structured metadata
                    doc_type=chunk.doc_type,
                    course_code=chunk.course_code,
                    program_name=chunk.program_name,
                    source_url=chunk.source_url,
                    accessed_date=chunk.accessed_date,
                    catalog_year=chunk.catalog_year,
                    citation_label=chunk.citation_label,
                    section=chunk.section,
                    section_parser=metadata.get("section_parser"),
                    subchunk_index=metadata.get("subchunk_index"),
                )
                db.add(ch)

        else:
            # generic fallback path
            parts = simple_chunk(raw_text)

            for idx, chunk_text in enumerate(parts):
                print(
                        {
                            "idx": idx,
                            "doc_type": getattr(chunk, "doc_type", None),
                            "course_code": getattr(chunk, "course_code", None),
                            "program_name": getattr(chunk, "program_name", None),
                            "source_url": getattr(chunk, "source_url", None),
                            "accessed_date": getattr(chunk, "accessed_date", None),
                            "catalog_year": getattr(chunk, "catalog_year", None),
                            "citation_label": getattr(chunk, "citation_label", None),
                            "section": getattr(chunk, "section", None),
                            "metadata": getattr(chunk, "metadata", None),
                            "text_preview": (getattr(chunk, "text", "") or "")[:120],
                        },
                        flush=True,
                    )
                ch = Chunk(
                    id=uuid.uuid4(),
                    document_id=uuid.UUID(job["doc_id"]),
                    version_id=ver_id,
                    chunk_index=idx,
                    section_path=None,
                    page_range=None,
                    content_hash=sha256_text(chunk_text),
                    content=chunk_text,
                    token_count=None,
                    tags=job.get("tags"),

                    # generic chunks won't have structured catalog metadata
                    doc_type=None,
                    course_code=None,
                    program_name=None,
                    source_url=None,
                    accessed_date=None,
                    catalog_year=None,
                    citation_label=None,
                    section=None,
                    section_parser=None,
                    subchunk_index=None,
                )
                db.add(ch)

        # mark done
        db.execute(
            update(DocumentVersion)
            .where(DocumentVersion.id == ver_id)
            .values(status="done", ingested_at=datetime.utcnow(), error_code=None)
        )
        db.commit()

        enqueue_embed_job({
            "doc_id": job["doc_id"],
            "version_id": job["version_id"],
        })

    except Exception as e:
        code = str(e)
        if len(code) > 120:
            code = code[:120]

        db.execute(
            update(DocumentVersion)
            .where(DocumentVersion.id == ver_id)
            .values(status="failed", error_code=code)
        )
        db.commit()

    finally:
        db.close()


def main():
    while True:
        job = dequeue_job_blocking(timeout_sec=5)
        if not job:
            continue
        run_once(job)


if __name__ == "__main__":
    main()