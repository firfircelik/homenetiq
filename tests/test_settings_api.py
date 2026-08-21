"""Tests for the runtime settings API and the optional GET-auth toggle."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


AUTH = {"Authorization": "Bearer test-token"}


@pytest.fixture
def app():
    from backend.app import main as main_mod

    importlib.reload(main_mod)
    return main_mod.app


def test_settings_defaults(app):
    with TestClient(app) as c:
        data = c.get("/api/v1/settings").json()
        assert data["notify_url"] == ""
        assert data["mesh_pubkey_set"] is False
        assert data["get_auth"] is False


def test_settings_post_requires_token(app):
    with TestClient(app) as c:
        r = c.post("/api/v1/settings", json={"notify_url": "https://ntfy.sh/x"})
        assert r.status_code == 401


def test_settings_rejects_invalid_url(app):
    with TestClient(app) as c:
        r = c.post(
            "/api/v1/settings",
            json={"notify_url": "ftp://nope"},
            headers=AUTH,
        )
        assert r.status_code == 422


def test_settings_unknown_key_rejected(app):
    with TestClient(app) as c:
        r = c.post("/api/v1/settings", json={"db_path": "/etc/passwd"}, headers=AUTH)
        assert r.status_code == 422


def test_settings_roundtrip_and_persist(app):
    with TestClient(app) as c:
        r = c.post(
            "/api/v1/settings",
            json={"notify_url": "https://ntfy.sh/my-topic"},
            headers=AUTH,
        )
        assert r.status_code == 200
        assert r.json()["applied"]["notify_url"] == "https://ntfy.sh/my-topic"

        # GET reflects the change (runtime-applied)
        assert c.get("/api/v1/settings").json()["notify_url"] == "https://ntfy.sh/my-topic"

    # persisted override survives a fresh app instance (file-based)
    from backend.app.settings import Settings

    fresh = Settings()
    assert fresh.notify_url == "https://ntfy.sh/my-topic"


def test_clear_notify_url_with_empty_string(app):
    with TestClient(app) as c:
        c.post("/api/v1/settings", json={"notify_url": "https://ntfy.sh/t"}, headers=AUTH)
        r = c.post("/api/v1/settings", json={"notify_url": ""}, headers=AUTH)
        assert r.status_code == 200
        assert c.get("/api/v1/settings").json()["notify_url"] == ""


def test_optional_get_auth_toggle(app):
    from backend.app.settings import settings

    settings.get_auth = True
    try:
        with TestClient(app) as c:
            assert c.get("/api/v1/devices").status_code == 401
            ok = c.get("/api/v1/devices", headers=AUTH)
            assert ok.status_code == 200
    finally:
        settings.get_auth = False
