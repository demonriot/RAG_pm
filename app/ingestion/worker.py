import uuid
from datetime import datetime
from sqlalchemy import update

from app.db.session import SessionLocal
from app.db.models.document_version import DocumentVersion
from app.db.models.chunk import Chunk
from app.ingestion.queue import dequeue_job_blocking, enqueue_embed_job
from app.ingestion.storage import download_bytes

import hashlib
def parse_bytes(doc_type: str, data: bytes) -> str:
    # MVP: handle text-like types only. Real parsing comes next.
    if doc_type in ("txt", "md", "html"):
        return data.decode("utf-8", errors="ignore")
    raise ValueError(f"unsupported_doc_type:{doc_type}")
# ... unchanged helpers ...
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
        text = parse_bytes(job["doc_type"], data)

        parts = simple_chunk(text)

        # insert chunks
        for idx, chunk_text in enumerate(parts):
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
            )
            db.add(ch)

        # mark done
        db.execute(
            update(DocumentVersion)
            .where(DocumentVersion.id == ver_id)
            .values(status="done", ingested_at=datetime.utcnow(), error_code=None)
        )
        db.commit()

        # enqueue embedding job (Step 3)
        enqueue_embed_job({
            "doc_id": job["doc_id"],
            "version_id": job["version_id"],
        })

    except Exception as e:
        # mark failed with redacted error_code
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
