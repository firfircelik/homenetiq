"""MAC/BSSID privacy helpers.

No agent ever sends a raw MAC/BSSID. Two modes are supported:

- "redact" (default): the BSSID is reduced to its last two octets
  (e.g. "...:44:55"). Not identifiable, but consistent across re-connects
  to the same network.

- "hash": the BSSID is SHA-256 hashed (with optional user salt). When a
  `privacy.salt` is set in config, the same salt + same BSSID produces
  the same hash (allowing joinability across agents). There is NO fixed
  salt.
"""

from __future__ import annotations

import hashlib


def bssid_redact(bssid: str | None) -> str | None:
    """Reduce the BSSID to its last two octets; not identifiable.

    Example: "00:11:22:33:44:55" -> "...:44:55"
    Invalid or None input -> None
    """

    if not bssid:
        return None
    parts = bssid.strip().split(":")
    if len(parts) != 6:
        # Not a valid IEEE 802 MAC format -> fully hide
        return None
    return f"...:{parts[4]}:{parts[5]}"


def bssid_hash(bssid: str | None, salt: str = "") -> str | None:
    """SHA-256 hash the BSSID; return the first 12 hex characters.

    Salt is optional: the user can set their own salt in config. With no
    salt, the same BSSID always yields the same hash. There is NO fixed
    salt.
    """

    if not bssid:
        return None
    text = (salt + ":" + bssid.strip().lower()) if salt else bssid.strip().lower()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def apply_privacy(bssid: str | None, mode: str = "redact", salt: str = "") -> str | None:
    """Apply the configured privacy transform to a BSSID."""
    if mode == "hash":
        return bssid_hash(bssid, salt)
    return bssid_redact(bssid)
