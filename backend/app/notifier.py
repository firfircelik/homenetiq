"""Mesh state-change detection + optional webhook/ntfy notifications.

`detect_transitions` is a pure function (easy to test): it compares two
consecutive mesh payloads for the same (device, peer) and reports what
changed. `send_notification` delivers the human-readable summary to the
configured webhook/ntfy URL; failures are swallowed so ingestion never
breaks because of a notification problem.
"""

from __future__ import annotations

from typing import Any

import requests

from .settings import settings


def detect_transitions(
    prev_payload: dict[str, Any] | None, new_payload: dict[str, Any]
) -> list[tuple[str, str]]:
    """Return (kind, detail) tuples describing state changes between payloads.

    Kinds: `peer_down`, `peer_up`, `path_change`.
    Only meaningful transitions fire — e.g. a first-ever report (no previous
    payload) or peer-less snapshots produce nothing.
    """
    events: list[tuple[str, str]] = []
    if not new_payload:
        return events
    peer = new_payload.get("peer_id")
    if not peer:
        return events

    prev_est = (prev_payload or {}).get("established")
    new_est = new_payload.get("established")
    prev_path = (prev_payload or {}).get("path")
    new_path = new_payload.get("path")

    if prev_est is True and new_est is False:
        events.append(("peer_down", f"peer '{peer}' tüneli kapandı"))
    elif prev_est is False and new_est is True:
        events.append(("peer_up", f"peer '{peer}' tüneli kuruldu"))

    if (
        prev_est is True
        and new_est is True
        and prev_path
        and new_path
        and prev_path != new_path
    ):
        events.append(("path_change", f"peer '{peer}': {prev_path} → {new_path}"))

    return events


def send_notification(title: str, body: str) -> bool:
    """POST a notification to `HOMENETIQ_NOTIFY_URL` (ntfy-compatible).

    Returns True when delivered; never raises.
    """
    url = settings.notify_url
    if not url:
        return False
    try:
        resp = requests.post(
            url,
            data=body.encode("utf-8"),
            headers={"Title": title, "Tags": "mesh"},
            timeout=5,
        )
        return resp.ok
    except Exception:
        return False
