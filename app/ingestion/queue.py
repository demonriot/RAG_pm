import os
import json
import redis

QUEUE_KEY = "ingest:jobs"

def redis_client():
    host = os.getenv("REDIS_HOST")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return redis.Redis(host=host, port=port, decode_responses=True)

def enqueue_job(payload: dict):
    r = redis_client()
    r.lpush(QUEUE_KEY, json.dumps(payload))

def dequeue_job_blocking(timeout_sec: int = 5) -> dict | None:
    r = redis_client()
    item = r.brpop(QUEUE_KEY, timeout=timeout_sec)
    if not item:
        return None
    _, raw = item
    return json.loads(raw)
