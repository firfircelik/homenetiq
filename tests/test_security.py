"""Auth, token, and rate-limit behaviour."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from fastapi import HTTPException

from backend.app.ratelimit import check_ingest_rate, reset_for_tests
from backend.app.security import assert_secure_token


def test_assert_secure_token_refuses_example(monkeypatch):
    monkeypatch.delenv("HOMENETIQ_ALLOW_INSECURE", raising=False)
    with pytest.raises(RuntimeError, match="refusing to start"):
        assert_secure_token("change-me-local-token")
    with pytest.raises(RuntimeError, match="refusing to start"):
        assert_secure_token("")


def test_assert_secure_token_allows_insecure_flag(monkeypatch):
    monkeypatch.setenv("HOMENETIQ_ALLOW_INSECURE", "1")
    assert_secure_token("change-me-local-token")


def test_get_endpoints_require_token_when_get_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMENETIQ_DB_PATH", str(tmp_path / "homenetiq.sqlite3"))
    monkeypatch.setenv("HOMENETIQ_API_TOKEN", "test-token")
    monkeypatch.setenv("HOMENETIQ_REQUIRE_AUTH", "true")
    monkeypatch.setenv("HOMENETIQ_REQUIRE_GET_AUTH", "true")
    monkeypatch.setenv("HOMENETIQ_ALLOW_INSECURE", "1")
    monkeypatch.setenv("HOMENETIQ_MESH_PUBKEY", "aa" * 32)
    monkeypatch.setenv("HOMENETIQ_SETTINGS_FILE", str(tmp_path / "settings.json"))

    from backend.app import database as database_mod
    from backend.app import main as main_mod
    from backend.app import settings as settings_mod

    importlib.reload(settings_mod)
    importlib.reload(database_mod)
    importlib.reload(main_mod)

    with TestClient(main_mod.app) as c:
        assert c.get("/api/v1/devices").status_code == 401
        assert c.get("/api/v1/metrics/latest").status_code == 401
        assert c.get("/api/v1/mesh/pubkey").status_code == 401
        ok = c.get("/api/v1/devices", headers={"Authorization": "Bearer test-token"})
        assert ok.status_code == 200
        pub = c.get("/api/v1/mesh/pubkey", headers={"Authorization": "Bearer test-token"})
        assert pub.status_code == 200
        assert pub.json()["coord_pubkey"] == "aa" * 32


def test_mesh_pubkey_accepts_enroll_token(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMENETIQ_DB_PATH", str(tmp_path / "homenetiq.sqlite3"))
    monkeypatch.setenv("HOMENETIQ_API_TOKEN", "test-token")
    monkeypatch.setenv("HOMENETIQ_REQUIRE_GET_AUTH", "true")
    monkeypatch.setenv("HOMENETIQ_ENROLL_TOKEN", "enroll-me")
    monkeypatch.setenv("HOMENETIQ_ALLOW_INSECURE", "1")
    monkeypatch.setenv("HOMENETIQ_MESH_PUBKEY", "bb" * 32)
    monkeypatch.setenv("HOMENETIQ_SETTINGS_FILE", str(tmp_path / "settings.json"))

    from backend.app import database as database_mod
    from backend.app import main as main_mod
    from backend.app import settings as settings_mod

    importlib.reload(settings_mod)
    importlib.reload(database_mod)
    importlib.reload(main_mod)

    with TestClient(main_mod.app) as c:
        r = c.get("/api/v1/mesh/pubkey", headers={"Authorization": "Bearer enroll-me"})
        assert r.status_code == 200
        assert r.json()["coord_pubkey"] == "bb" * 32


def test_mesh_pubkey_requires_token_even_when_get_auth_off(tmp_path, monkeypatch):
    monkeypatch.setenv("HOMENETIQ_DB_PATH", str(tmp_path / "homenetiq.sqlite3"))
    monkeypatch.setenv("HOMENETIQ_API_TOKEN", "test-token")
    monkeypatch.setenv("HOMENETIQ_REQUIRE_AUTH", "true")
    monkeypatch.setenv("HOMENETIQ_REQUIRE_GET_AUTH", "false")
    monkeypatch.setenv("HOMENETIQ_ALLOW_INSECURE", "1")
    monkeypatch.setenv("HOMENETIQ_MESH_PUBKEY", "cc" * 32)
    monkeypatch.setenv("HOMENETIQ_SETTINGS_FILE", str(tmp_path / "settings.json"))

    from backend.app import database as database_mod
    from backend.app import main as main_mod
    from backend.app import settings as settings_mod

    importlib.reload(settings_mod)
    importlib.reload(database_mod)
    importlib.reload(main_mod)

    with TestClient(main_mod.app) as c:
        assert c.get("/api/v1/mesh/pubkey").status_code == 401
        ok = c.get("/api/v1/mesh/pubkey", headers={"Authorization": "Bearer test-token"})
        assert ok.status_code == 200


def test_ingest_rate_limit_trips(monkeypatch):
    import backend.app.ratelimit as rl

    monkeypatch.setattr(rl, "MAX_HITS", 2)
    reset_for_tests()
    check_ingest_rate("192.0.2.1", "Bearer t")
    check_ingest_rate("192.0.2.1", "Bearer t")
    with pytest.raises(HTTPException) as ei:
        check_ingest_rate("192.0.2.1", "Bearer t")
    assert ei.value.status_code == 429
