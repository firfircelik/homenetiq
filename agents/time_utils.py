"""Timestamp helper (ISO-8601 UTC)."""

from __future__ import annotations

from datetime import datetime, timezone


def now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string. All agents use the same format."""
    return datetime.now(timezone.utc).isoformat()
