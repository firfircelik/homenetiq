"""HTTP client for posting metrics to the backend.

`requests` is already in requirements.txt; no extra dependencies. Retry
is linear (not exponential) — sufficient for a small LAN.
"""

from __future__ import annotations

import time
from typing import Any

import requests


class HttpError(RuntimeError):
    """Raised when an HTTP POST fails."""


def post_metric(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 10) -> dict[str, Any]:
    """Make a single POST attempt. Return parsed JSON or raise."""
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def post_metric_with_retry(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    *,
    max_attempts: int = 3,
    retry_delay_seconds: int = 10,
    timeout: int = 10,
) -> dict[str, Any]:
    """Retry POST up to N times. Waits `retry_delay_seconds` between attempts.

    `max_attempts=1` -> no retry. Raises `HttpError` if the final attempt
    also fails.
    """

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return post_metric(url, payload, headers, timeout=timeout)
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            if attempt >= max_attempts:
                break
            time.sleep(retry_delay_seconds)
    raise HttpError(f"POST {url} failed after {max_attempts} attempts: {last_exc}")
