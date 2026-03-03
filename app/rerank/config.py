# app/rerank/config.py
from __future__ import annotations

import os


def get_rerank_model() -> str:
    return os.getenv("VOYAGE_RERANK_MODEL", "rerank-2.5-lite")


def get_rerank_top_n() -> int:
    return int(os.getenv("RERANK_TOP_N", "12"))


def get_rerank_per_doc_cap() -> int:
    return int(os.getenv("RERANK_PER_DOC_CAP", "2"))


def get_rerank_max_chars() -> int:
    return int(os.getenv("RERANK_MAX_CHARS", "1500"))


def get_rerank_fail_open() -> bool:
    return os.getenv("RERANK_FAIL_OPEN", "true").lower() in ("1", "true", "yes", "y")

def get_rerank_max_vector_distance() -> float:
    return float(os.getenv("RERANK_MAX_VECTOR_DISTANCE", "0.75"))