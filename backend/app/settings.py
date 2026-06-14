import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Backend runtime settings.

    Values are read from environment variables so the token, DB path and
    similar secrets are not hard-coded.
    """

    db_path: str = os.getenv("HOMENETIQ_DB_PATH", "./homenetiq.sqlite3")
    api_token: str = os.getenv("HOMENETIQ_API_TOKEN", "change-me-local-token")
    require_auth: bool = os.getenv("HOMENETIQ_REQUIRE_AUTH", "true").lower() == "true"
    stale_after_seconds: int = int(os.getenv("HOMENETIQ_STALE_AFTER_SECONDS", "120"))
    offline_after_seconds: int = int(os.getenv("HOMENETIQ_OFFLINE_AFTER_SECONDS", "600"))


settings = Settings()
