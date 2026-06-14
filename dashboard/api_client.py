"""Dashboard -> backend API client.

All dashboard pages use this module. On error it raises clear exceptions;
the UI layer surfaces them to the user.
"""

from __future__ import annotations

import os
from typing import Any

import requests


DEFAULT_TIMEOUT = 8


class ApiUnavailable(RuntimeError):
    """Raised when the backend cannot be reached or returns an HTTP error."""


def get_backend_url() -> str:
    """Return the backend URL from HOMENETIQ_BACKEND_URL."""
    return os.getenv("HOMENETIQ_BACKEND_URL", "http://127.0.0.1:8080").rstrip("/")


def get_api_token() -> str:
    """Return the API token from HOMENETIQ_API_TOKEN.

    GET endpoints do not require auth, so it can be empty. This helper is
    kept so a future auth change needs no dashboard code update.
    """
    return os.getenv("HOMENETIQ_API_TOKEN", "")


def _headers() -> dict[str, str]:
    token = get_api_token()
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _request(path: str, params: dict | None = None) -> Any:
    url = get_backend_url() + path
    try:
        response = requests.get(url, headers=_headers(), params=params, timeout=DEFAULT_TIMEOUT)
    except requests.RequestException as exc:
        raise ApiUnavailable(
            f"Cannot reach backend ({url}). Is it running? Error: {exc}"
        ) from exc
    if response.status_code >= 400:
        raise ApiUnavailable(
            f"Backend returned HTTP {response.status_code}: {response.text[:200]}"
        )
    try:
        return response.json()
    except ValueError as exc:
        raise ApiUnavailable(f"Backend JSON parse error: {exc}") from exc


def get_summary() -> dict[str, Any]:
    return _request("/api/v1/summary")


def get_devices() -> list[dict[str, Any]]:
    return _request("/api/v1/devices")


def get_latest_metrics(limit: int = 200) -> list[dict[str, Any]]:
    return _request("/api/v1/metrics/latest", params={"limit": limit})


def health() -> dict[str, Any]:
    return _request("/health")
