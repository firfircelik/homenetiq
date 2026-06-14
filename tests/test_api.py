"""FastAPI end-to-end tests.

The `isolated_db` fixture (in conftest.py) sets up a temporary SQLite
file for each test, so the real database is never touched. The fixture
also reloads `backend.app.main` with the new env vars, so we get a
fresh `app` reference from inside the fixture.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    from backend.app import main as main_mod

    importlib.reload(main_mod)
    return main_mod.app


def _client(app) -> TestClient:
    return TestClient(app)


def test_health_endpoint(app):
    with _client(app) as c:
        r = c.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "service": "homenetiq-backend"}


def test_unauthorized_post_rejected(app):
    """POST /api/v1/metrics without a token should return 401."""
    with _client(app) as c:
        r = c.post("/api/v1/metrics", json={
            "device_id": "x",
            "device_type": "wifi_probe",
            "metric_type": "wifi",
            "payload": {},
        })
        assert r.status_code == 401


def test_authorized_post_stores_metric(app):
    """POST with a token returns 200, and the response fields are populated
    by the backend with computed quality/root_cause.
    kalite/root_cause ile dolar."""

    payload = {
        "device_id": "kali-test",
        "device_name": "Kali Test",
        "device_type": "wifi_probe",
        "os": "kali",
        "metric_type": "wifi",
        "payload": {
            "rssi": -80,
            "snr": 10,
            "tx_rate_mbps": 20,
            "band": "2GHz",
        },
    }
    with _client(app) as c:
        r = c.post(
            "/api/v1/metrics",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "stored"
        assert body["device_id"] == "kali-test"
        assert body["quality"] == "poor"
        assert "weak_signal" in body["issues"]
        assert body["root_cause"] in {
            "wifi_signal_issue",
            "wifi_congestion_issue",
            "wifi_signal_or_2ghz_congestion_issue",
        }


def test_post_then_get_devices_lists_device(app):
    payload = {
        "device_id": "pi-test",
        "device_type": "network_probe",
        "metric_type": "network",
        "payload": {"internet_latency_ms": 40},
    }
    with _client(app) as c:
        c.post("/api/v1/metrics", json=payload, headers={"Authorization": "Bearer test-token"})
        r = c.get("/api/v1/devices")
        assert r.status_code == 200
        devices = r.json()
        assert len(devices) == 1
        assert devices[0]["device_id"] == "pi-test"
        assert devices[0]["status"] == "active"


def test_post_then_get_latest_metrics_returns_inserted_row(app):
    payload = {
        "device_id": "kali-latest",
        "device_type": "wifi_probe",
        "metric_type": "wifi",
        "payload": {"rssi": -55, "snr": 30, "tx_rate_mbps": 144},
    }
    with _client(app) as c:
        c.post("/api/v1/metrics", json=payload, headers={"Authorization": "Bearer test-token"})
        r = c.get("/api/v1/metrics/latest")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 1
        assert rows[0]["device_id"] == "kali-latest"
        assert rows[0]["quality"] == "good"
        assert rows[0]["payload"]["rssi"] == -55
