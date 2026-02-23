# app/embeddings/worker.py
import os
import time
import uuid
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SessionLocal
from app.db.models.chunk import Chunk
from app.db.models.embedding import ChunkEmbedding
from app.ingestion.queue import dequeue_embed_job_blocking
from app.embeddings.provider import embed_texts, get_embedding_model


def chunk_batches(items: List[Tuple[uuid.UUID, str]], batch_size: int) -> List[List[Tuple[uuid.UUID, str]]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def fetch_missing_chunks(version_id: uuid.UUID, limit: int | None = None) -> List[Tuple[uuid.UUID, str]]:
    """
    Returns [(chunk_id, content), ...] for chunks in this version that have no embedding yet.
    """
    db = SessionLocal()
    try:
        stmt = (
            select(Chunk.id, Chunk.content)
            .outerjoin(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
            .where(Chunk.version_id == version_id)
            .where(ChunkEmbedding.chunk_id.is_(None))
            .order_by(Chunk.chunk_index.asc())
        )
        if limit:
            stmt = stmt.limit(limit)

        rows = db.execute(stmt).all()
        return [(row[0], row[1]) for row in rows]
    finally:
        db.close()


def upsert_embeddings(pairs: List[Tuple[uuid.UUID, List[float]]]) -> None:
    """
    Upsert embeddings by chunk_id (idempotent).
    """
    if not pairs:
        return

    db = SessionLocal()
    try:
        values = [{"chunk_id": cid, "embedding": emb} for cid, emb in pairs]

        stmt = pg_insert(ChunkEmbedding).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[ChunkEmbedding.chunk_id],
            set_={"embedding": stmt.excluded.embedding},
        )
        db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run_once(job: dict) -> None:
    ver_id = uuid.UUID(job["version_id"])
    model = get_embedding_model()

    batch_size = int(os.getenv("EMBED_BATCH_SIZE", "64"))

    # 1) Fetch chunks that still need embeddings
    missing = fetch_missing_chunks(ver_id)
    if not missing:
        print(f"[embed-worker] version={ver_id} nothing to embed", flush=True)
        return

    print(f"[embed-worker] version={ver_id} missing_chunks={len(missing)} model={model}", flush=True)

    # 2) Embed in batches
    for batch in chunk_batches(missing, batch_size=batch_size):
        ids = [cid for cid, _ in batch]
        texts = [txt for _, txt in batch]

        embs = embed_texts(texts, model=model)  # list[list[float]]
        upsert_embeddings(list(zip(ids, embs)))

        print(f"[embed-worker] embedded batch size={len(batch)}", flush=True)


def main():
    print("[embed-worker] started", flush=True)
    while True:
        try:
            job = dequeue_embed_job_blocking(timeout_sec=5)
            if not job:
                continue
            run_once(job)
        except Exception as e:
            # Don't die — retry loop
            print(f"[embed-worker] error: {e} (retrying in 2s)", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()