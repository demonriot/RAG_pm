import uuid
import hashlib
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.storage import ensure_bucket, upload_bytes
from app.ingestion.queue import enqueue_job

router = APIRouter(prefix="/ingest", tags=["ingest"])

BUCKET = "documents"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@router.post("/upload")
async def upload(
    title: str = Form(...),
    doc_type: str = Form(...),  # stored in Document.doc_type
    tags: str | None = Form(None),  # comma-separated
    file: UploadFile = File(...),

    # Optional structured-ingestion fields
    source_type: str | None = Form(None),          # e.g. "osu_catalog"
    catalog_doc_type: str | None = Form(None),     # e.g. "course" / "program" / "policy"
    source_url: str | None = Form(None),
    accessed_date: str | None = Form(None),
    catalog_year: str | None = Form(None),
    course_code: str | None = Form(None),
    program_name: str | None = Form(None),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    ensure_bucket(BUCKET)

    doc_id = uuid.uuid4()
    version_id = uuid.uuid4()

    content_hash = sha256_bytes(data)
    storage_key = f"docs/{doc_id}/{version_id}/{file.filename}"

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    db = SessionLocal()
    try:
        doc = Document(id=doc_id, title=title, doc_type=doc_type)
        db.add(doc)

        ver = DocumentVersion(
            id=version_id,
            document_id=doc_id,
            version_number=1,
            content_hash=content_hash,
            storage_path=f"{BUCKET}:{storage_key}",
            status="queued",
        )
        db.add(ver)
        db.commit()

        upload_bytes(BUCKET, storage_key, data, content_type=file.content_type)

        enqueue_job({
            "doc_id": str(doc_id),
            "version_id": str(version_id),

            # file/storage info
            "file_type": doc_type,   # important for worker decode path
            "bucket": BUCKET,
            "key": storage_key,

            # generic metadata
            "tags": tag_list,
            "title": title,

            # structured catalog metadata
            "source_type": source_type,
            "catalog_doc_type": catalog_doc_type,
            "source_url": source_url,
            "accessed_date": accessed_date,
            "catalog_year": catalog_year,
            "course_code": course_code,
            "program_name": program_name,
        })

        return {
            "doc_id": str(doc_id),
            "version_id": str(version_id),
            "status": "queued",
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("/status/{version_id}")
def status(version_id: str):
    db = SessionLocal()
    try:
        q = select(DocumentVersion).where(DocumentVersion.id == uuid.UUID(version_id))
        ver = db.execute(q).scalar_one_or_none()
        if not ver:
            raise HTTPException(status_code=404, detail="version not found")
        return {
            "version_id": version_id,
            "status": ver.status,
            "error_code": ver.error_code,
            "ingested_at": ver.ingested_at,
        }
    finally:
        db.close()