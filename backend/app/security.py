"""Startup token policy and GET/enrollment guards."""

from __future__ import annotations

import os

INSECURE_TOKENS = frozenset({"", "change-me-local-token"})


def allow_insecure() -> bool:
    return os.getenv("HOMENETIQ_ALLOW_INSECURE", "").lower() in ("1", "true", "yes")


def assert_secure_token(token: str) -> None:
    """Refuse empty / example tokens unless the operator opted into a local demo."""
    if (token or "").strip() in INSECURE_TOKENS and not allow_insecure():
        raise RuntimeError(
            "refusing to start: HOMENETIQ_API_TOKEN is empty or the example "
            "value change-me-local-token. Run `make init` / `scripts/homenetiq-init.sh` "
            "or `openssl rand -hex 32`, then set the token. For a throwaway local "
            "demo only, set HOMENETIQ_ALLOW_INSECURE=1."
        )


def enroll_token() -> str:
    return os.getenv("HOMENETIQ_ENROLL_TOKEN", "").strip()
