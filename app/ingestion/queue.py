import os
import json
import redis

INGEST_QUEUE_KEY = "ingest:jobs"
EMBED_QUEUE_KEY = "embed:jobs"

def redis_client():
    host = os.getenv("REDIS_HOST")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return redis.Redis(host=host, port=port, decode_responses=True)

# --- Ingest queue ---
def enqueue_job(payload: dict):
    r = redis_client()
    r.lpush(INGEST_QUEUE_KEY, json.dumps(payload))

def dequeue_job_blocking(timeout_sec: int = 5) -> dict | None:
    r = redis_client()
    item = r.brpop(INGEST_QUEUE_KEY, timeout=timeout_sec)
    if not item:
        return None
    _, raw = item
    return json.loads(raw)

# --- Embed queue ---
def enqueue_embed_job(payload: dict):
    """
    Payload should include:
      - doc_id
      - version_id
    Optional:
      - priority, force, etc. (later)
    """
    r = redis_client()
    r.lpush(EMBED_QUEUE_KEY, json.dumps(payload))

def dequeue_embed_job_blocking(timeout_sec: int = 5) -> dict | None:
    r = redis_client()
    item = r.brpop(EMBED_QUEUE_KEY, timeout=timeout_sec)
    if not item:
        return None
    _, raw = item
    return json.loads(raw)