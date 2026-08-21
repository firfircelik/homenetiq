import json
import os
from dataclasses import dataclass
from pathlib import Path


def _settings_file() -> Path:
    """Runtime-editable overrides live here (JSON). Created on first save."""
    return Path(os.getenv("HOMENETIQ_SETTINGS_FILE", "data/settings.json"))


# Keys an operator may change at runtime (dashboard / API). Everything else
# stays environment-controlled on purpose.
RUNTIME_KEYS = ("notify_url",)


@dataclass
class Settings:
    """Backend runtime settings.

    Values come from environment variables first; optional JSON overrides
    (data/settings.json, written by POST /api/v1/settings) are applied on
    top. The dataclass is intentionally MUTABLE so the dashboard can change
    operational knobs (e.g. the notification webhook) without a restart.
    """

    db_path: str = os.getenv("HOMENETIQ_DB_PATH", "./homenetiq.sqlite3")
    api_token: str = os.getenv("HOMENETIQ_API_TOKEN", "change-me-local-token")
    require_auth: bool = os.getenv("HOMENETIQ_REQUIRE_AUTH", "true").lower() == "true"
    # When true, data-read GET endpoints also demand the Bearer token.
    get_auth: bool = os.getenv("HOMENETIQ_REQUIRE_GET_AUTH", "false").lower() == "true"
    stale_after_seconds: int = int(os.getenv("HOMENETIQ_STALE_AFTER_SECONDS", "120"))
    offline_after_seconds: int = int(os.getenv("HOMENETIQ_OFFLINE_AFTER_SECONDS", "600"))
    # meshlink enrollment: coordinator public key served to LAN clients so
    # `scripts/join.sh` can bootstrap without copying keys by hand.
    # A public key is an identity, not a secret; see docs/MESH_INTEGRATION.md.
    mesh_pubkey: str = os.getenv("HOMENETIQ_MESH_PUBKEY", "")
    # Optional webhook / ntfy URL for mesh state-change notifications
    # (e.g. https://ntfy.sh/my-topic). Empty disables notifications.
    notify_url: str = os.getenv("HOMENETIQ_NOTIFY_URL", "")

    def __post_init__(self) -> None:
        self.apply_file_overrides()

    # ------------------------------------------------------------- overrides
    def apply_file_overrides(self) -> None:
        """Apply JSON overrides for RUNTIME_KEYS (silently skip bad files)."""
        f = _settings_file()
        if not f.is_file():
            return
        try:
            data = json.loads(f.read_text())
        except Exception:
            return
        if not isinstance(data, dict):
            return
        for key in RUNTIME_KEYS:
            if key in data:
                setattr(self, key, data[key])

    def save_overrides(self, update: dict) -> dict:
        """Validate + persist runtime overrides; apply them immediately.

        Returns the applied subset. Raises ValueError on unknown keys or
        invalid values.
        """
        applied: dict = {}
        for key, value in update.items():
            if key not in RUNTIME_KEYS:
                raise ValueError(f"unknown setting: {key}")
            if key == "notify_url" and value not in ("", None):
                v = str(value).strip()
                if not (v.startswith("http://") or v.startswith("https://")):
                    raise ValueError("notify_url must start with http:// or https://")
                applied[key] = v
            elif key == "notify_url":
                applied[key] = ""  # explicit clear
        f = _settings_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        current: dict = {}
        if f.is_file():
            try:
                current = json.loads(f.read_text()) or {}
            except Exception:
                current = {}
        current.update(applied)
        f.write_text(json.dumps(current, indent=2))
        for k, v in applied.items():
            setattr(self, k, v)
        return applied


settings = Settings()
