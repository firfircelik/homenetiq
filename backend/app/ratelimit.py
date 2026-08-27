"""Simple in-memory rate limit for metric ingest (IP + token)."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException

# Sliding window: max POSTs per window per (client, token) pair.
WINDOW_SECONDS = 60.0
MAX_HITS = 60

_hits: dict[str, list[float]] = defaultdict(list)


def check_ingest_rate(client_host: str, authorization: str | None) -> None:
    key = f"{client_host}|{authorization or ''}"
    now = time.monotonic()
    bucket = [t for t in _hits[key] if now - t < WINDOW_SECONDS]
    if len(bucket) >= MAX_HITS:
        _hits[key] = bucket
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    bucket.append(now)
    _hits[key] = bucket


def reset_for_tests() -> None:
    _hits.clear()
