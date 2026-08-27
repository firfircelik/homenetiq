"""Shared pytest fixtures.

Each test function gets a temporary SQLite file; tests don't touch the
real database and can run in parallel.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """For each test, set up an isolated SQLite file and reload backend
    modules with these new settings.

    `settings` is a frozen dataclass, so monkeypatch.setattr cannot update
    it; instead we reload all `backend.app` modules. Each test then
    works with a clean `HOMENETIQ_DB_PATH` and `HOMENETIQ_API_TOKEN`.
    """

    db_path = tmp_path / "homenetiq.sqlite3"
    monkeypatch.setenv("HOMENETIQ_DB_PATH", str(db_path))
    monkeypatch.setenv("HOMENETIQ_API_TOKEN", "test-token")
    monkeypatch.setenv("HOMENETIQ_REQUIRE_AUTH", "true")
    monkeypatch.setenv("HOMENETIQ_REQUIRE_GET_AUTH", "true")
    monkeypatch.setenv("HOMENETIQ_ALLOW_INSECURE", "1")
    monkeypatch.setenv("HOMENETIQ_SETTINGS_FILE", str(tmp_path / "settings.json"))

    # Test-caller modules may have imported these before `isolated_db`
    # ran; reload them so the new env values take effect.
    from backend.app import database as database_mod
    from backend.app import main as main_mod
    from backend.app import settings as settings_mod

    importlib.reload(settings_mod)
    importlib.reload(database_mod)
    importlib.reload(main_mod)

    yield db_path
