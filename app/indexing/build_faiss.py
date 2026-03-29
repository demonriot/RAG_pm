import json
from pathlib import Path

import faiss
import numpy as np
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.embedding import ChunkEmbedding


FAISS_DIR = Path("data/faiss")
INDEX_PATH = FAISS_DIR / "chunks.index"
IDMAP_PATH = FAISS_DIR / "id_map.json"


def build_faiss_index() -> None:
    db = SessionLocal()
    try:
        stmt = select(
            ChunkEmbedding.chunk_id,
            ChunkEmbedding.embedding,
        ).where(ChunkEmbedding.embedding.is_not(None))

        rows = db.execute(stmt).all()

        chunk_ids: list[str] = []
        vectors: list[np.ndarray] = []

        for row in rows:
            chunk_id = str(row.chunk_id)
            embedding = row.embedding

            if embedding is None:
                continue

            vec = np.asarray(embedding, dtype=np.float32)
            if vec.ndim != 1:
                continue

            chunk_ids.append(chunk_id)
            vectors.append(vec)

        if not vectors:
            raise ValueError("No embeddings found. Cannot build FAISS index.")

        matrix = np.vstack(vectors).astype(np.float32)
        faiss.normalize_L2(matrix)

        dim = matrix.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(matrix)

        FAISS_DIR.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(INDEX_PATH))

        id_map = {str(i): chunk_ids[i] for i in range(len(chunk_ids))}
        with open(IDMAP_PATH, "w", encoding="utf-8") as f:
            json.dump(id_map, f, indent=2)

        print(f"FAISS index built successfully with {len(chunk_ids)} vectors.")
        print(f"Saved index to: {INDEX_PATH}")
        print(f"Saved id map to: {IDMAP_PATH}")

    finally:
        db.close()


if __name__ == "__main__":
    build_faiss_index()