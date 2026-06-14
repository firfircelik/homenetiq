"""Basic CRUD tests for backend.app.database."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app import database as db


def test_init_db_creates_tables(isolated_db):
    db.init_db()
    with db.get_conn() as conn:
        names = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert {"devices", "metrics"}.issubset(names)


def test_upsert_device_inserts_then_updates(isolated_db):
    db.init_db()
    db.upsert_device("dev-1", "My Device", "wifi_probe", "linux")

    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM devices WHERE device_id = ?", ("dev-1",)).fetchone()
        assert row["device_name"] == "My Device"
        first_seen = row["first_seen"]

    db.upsert_device("dev-1", "My Device 2", "wifi_probe", "linux")
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM devices WHERE device_id = ?", ("dev-1",)).fetchone()
        assert row["device_name"] == "My Device 2"
        # first_seen should not change
        assert row["first_seen"] == first_seen


def test_insert_and_latest_metrics_roundtrip(isolated_db):
    db.init_db()
    db.upsert_device("dev-1", None, "wifi_probe", "linux")
    db.upsert_device("dev-2", None, "network_probe", "linux")

    db.insert_metric(
        device_id="dev-1", device_type="wifi_probe", metric_type="wifi",
        collected_at=datetime.now(timezone.utc),
        payload={"rssi": -55}, quality="good", issues=[], root_cause="healthy",
    )
    db.insert_metric(
        device_id="dev-2", device_type="network_probe", metric_type="network",
        collected_at=datetime.now(timezone.utc),
        payload={"internet_latency_ms": 200}, quality="poor",
        issues=["very_high_internet_latency"], root_cause="wan_or_isp_issue",
    )

    rows = db.latest_metrics(limit=10)
    assert len(rows) == 2
    # each row should come back with payload as a dict
    sample = next(r for r in rows if r["device_id"] == "dev-1")
    assert sample["payload"] == {"rssi": -55}
    assert sample["issues"] == []


def test_latest_metrics_for_device_filters(isolated_db):
    db.init_db()
    for did in ("a", "b"):
        db.upsert_device(did, None, "wifi_probe", "linux")
        db.insert_metric(
            device_id=did, device_type="wifi_probe", metric_type="wifi",
            collected_at=datetime.now(timezone.utc),
            payload={}, quality="good", issues=[], root_cause="healthy",
        )

    rows = db.latest_metrics_for_device("a", limit=10)
    assert all(r["device_id"] == "a" for r in rows)
    assert len(rows) == 1


def test_list_devices_marks_stale_and_offline(isolated_db, monkeypatch):
    db.init_db()
    db.upsert_device("fresh", None, "wifi_probe", "linux")
    # Set last_seen to an old date
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE devices SET last_seen = ? WHERE device_id = ?",
            ("2000-01-01T00:00:00+00:00", "fresh"),
        )

    # With default 120s / 600s thresholds: >600s = offline
    devices = db.list_devices(stale_after=120, offline_after=600)
    assert devices[0]["status"] == "offline"
