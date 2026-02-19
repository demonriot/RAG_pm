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
    doc_type: str = Form(...),  # pdf/md/docx/html/txt
    tags: str | None = Form(None),  # comma-separated
    file: UploadFile = File(...),
):
    # read file bytes
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    ensure_bucket(BUCKET)

    # create doc + version
    doc_id = uuid.uuid4()
    version_id = uuid.uuid4()

    content_hash = sha256_bytes(data)
    storage_key = f"docs/{doc_id}/{version_id}/{file.filename}"

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    db = SessionLocal()
    try:
        # create document
        doc = Document(id=doc_id, title=title, doc_type=doc_type)
        db.add(doc)

        # version_number = 1 for MVP (later: auto increment per doc)
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

        # upload to MinIO after commit (so IDs exist)
        upload_bytes(BUCKET, storage_key, data, content_type=file.content_type)

        # enqueue job
        enqueue_job({
            "doc_id": str(doc_id),
            "version_id": str(version_id),
            "doc_type": doc_type,
            "bucket": BUCKET,
            "key": storage_key,
            "tags": tag_list,
            "title": title,
        })

        return {
            "doc_id": str(doc_id),
            "version_id": str(version_id),
            "status": "queued",
        }
    except Exception as e:
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
