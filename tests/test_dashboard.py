"""Tests for dashboard modules.

Streamlit import may fail in test environments due to starlette version
mismatch, so we only test the pure modules (api_client + formatters).
Page UI is verified manually.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from dashboard import api_client
from dashboard import formatters
from dashboard.formatters import (
    ROOT_CAUSE_LABELS,
    collect_recent_issues,
    collect_recent_recommendations,
    count_active_issues,
    filter_metrics_by_type,
    fmt_time_ago,
    fmt_timestamp,
    latest_per_device,
    metrics_to_dataframe,
    network_metric_to_row,
    parse_iso,
    quality_label,
    root_cause_label,
    wifi_metric_to_row,
)


# ---------- api_client: env ----------

def test_get_backend_url_default(monkeypatch):
    monkeypatch.delenv("HOMENETIQ_BACKEND_URL", raising=False)
    assert api_client.get_backend_url() == "http://127.0.0.1:8080"


def test_get_backend_url_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("HOMENETIQ_BACKEND_URL", "http://pi.local:8080/")
    assert api_client.get_backend_url() == "http://pi.local:8080"


def test_get_api_token_default_empty(monkeypatch):
    monkeypatch.delenv("HOMENETIQ_API_TOKEN", raising=False)
    assert api_client.get_api_token() == ""


def test_get_api_token_from_env(monkeypatch):
    monkeypatch.setenv("HOMENETIQ_API_TOKEN", "tok")
    assert api_client.get_api_token() == "tok"


# ---------- api_client: error handling ----------

def test_request_raises_api_unavailable_on_connection_error(monkeypatch):
    def fake_get(*args, **kwargs):
        raise api_client.requests.ConnectionError("refused")

    monkeypatch.setattr(api_client.requests, "get", fake_get)
    with pytest.raises(api_client.ApiUnavailable) as exc:
        api_client.get_summary()
    assert "Cannot reach backend" in str(exc.value)
    assert "127.0.0.1:8080" in str(exc.value)


def test_request_raises_api_unavailable_on_http_error(monkeypatch):
    class _R:
        status_code = 401
        text = "unauthorized"

        def json(self):
            raise ValueError("not json")

    monkeypatch.setattr(api_client.requests, "get", lambda *a, **k: _R())
    with pytest.raises(api_client.ApiUnavailable) as exc:
        api_client.get_devices()
    assert "401" in str(exc.value)


def test_request_raises_api_unavailable_on_bad_json(monkeypatch):
    class _R:
        status_code = 200
        text = "ok"

        def json(self):
            raise ValueError("nope")

    monkeypatch.setattr(api_client.requests, "get", lambda *a, **k: _R())
    with pytest.raises(api_client.ApiUnavailable) as exc:
        api_client.get_summary()
    assert "JSON" in str(exc.value)


def test_request_adds_authorization_header_when_token_set(monkeypatch):
    monkeypatch.setenv("HOMENETIQ_API_TOKEN", "ABC")
    captured = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured["headers"] = headers
        captured["url"] = url
        class _R:
            status_code = 200
            def json(self_inner):
                return {"ok": True}
        return _R()

    monkeypatch.setattr(api_client.requests, "get", fake_get)
    api_client.get_summary()
    assert captured["headers"]["Authorization"] == "Bearer ABC"


def test_request_omits_authorization_header_when_no_token(monkeypatch):
    monkeypatch.delenv("HOMENETIQ_API_TOKEN", raising=False)
    captured = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured["headers"] = headers
        class _R:
            status_code = 200
            def json(self_inner):
                return []
        return _R()

    monkeypatch.setattr(api_client.requests, "get", fake_get)
    api_client.get_devices()
    assert "Authorization" not in captured["headers"]


# ---------- formatters: etiketler ----------

def test_quality_label_known():
    assert quality_label("good") == "Good"
    assert quality_label("warning") == "Warning"
    assert quality_label("poor") == "Poor"


def test_quality_label_unknown():
    assert quality_label(None) == "Unknown"
    assert quality_label("xyz") == "xyz"


def test_root_cause_label_all_known():
    """All documented root causes have a human-readable label."""
    documented = {
        "healthy", "wifi_signal_issue", "wifi_congestion_issue",
        "local_ap_issue", "gateway_or_lan_issue", "wan_or_isp_issue",
        "dns_issue", "single_device_issue", "probe_or_backend_issue",
        "unknown_issue",
    }
    for rc in documented:
        assert rc in ROOT_CAUSE_LABELS, f"missing label: {rc}"
        assert root_cause_label(rc) != rc, f"no human label for: {rc}"


def test_root_cause_label_unknown_returns_input():
    assert root_cause_label(None) == "—"
    assert root_cause_label("not_mapped") == "not_mapped"


# ---------- formatters: zaman ----------

def test_parse_iso_valid_and_invalid():
    assert parse_iso("2026-06-14T10:00:00+00:00") is not None
    assert parse_iso("") is None
    assert parse_iso(None) is None
    assert parse_iso("not-iso") is None


def test_fmt_timestamp_handles_invalid():
    assert fmt_timestamp(None) == "—"
    assert fmt_timestamp("xxx") == "—"


def test_fmt_time_ago_format(monkeypatch):
    """fmt_time_ago returns a human-readable relative time."""
    from datetime import datetime, timezone, timedelta
    near_now = (datetime.now(timezone.utc) - timedelta(seconds=3)).isoformat()
    assert "seconds ago" in fmt_time_ago(near_now)


def test_fmt_time_ago_invalid():
    assert fmt_time_ago(None) == "—"


# ---------- formatters: filtreler ----------

def test_filter_metrics_by_type():
    metrics = [
        {"metric_type": "wifi"},
        {"metric_type": "network"},
        {"metric_type": "wifi"},
        {"metric_type": "dns"},
    ]
    assert len(filter_metrics_by_type(metrics, "wifi")) == 2
    assert len(filter_metrics_by_type(metrics, "network")) == 1
    assert len(filter_metrics_by_type(metrics, "dns")) == 1
    assert len(filter_metrics_by_type(metrics, "x")) == 0


def test_latest_per_device():
    metrics = [
        {"device_id": "a", "collected_at": "2026-01-01T00:00:00Z"},
        {"device_id": "a", "collected_at": "2026-01-02T00:00:00Z"},
        {"device_id": "b", "collected_at": "2026-01-01T00:00:00Z"},
    ]
    latest = latest_per_device(metrics)
    assert latest["a"]["collected_at"] == "2026-01-02T00:00:00Z"
    assert latest["b"]["collected_at"] == "2026-01-01T00:00:00Z"


# ---------- formatters: flatten ----------

def test_wifi_metric_to_row_extracts_canonical_fields():
    m = {
        "device_id": "kali-1",
        "collected_at": "2026-06-14T10:00:00+00:00",
        "quality": "good",
        "quality_score": 95,
        "payload": {
            "ssid": "Lab",
            "bssid_redacted": "...:44:55",
            "rssi": -50, "snr": 40,
            "tx_rate_mbps": 200, "rx_rate_mbps": 200,
            "band": "5GHz", "channel": 36,
            "phy_mode": "802.11ac", "mcs_index": 9,
            "security": "WPA2 Personal",
        },
    }
    row = wifi_metric_to_row(m)
    assert row["ssid"] == "Lab"
    assert row["bssid_redacted"] == "...:44:55"
    assert row["rssi"] == -50
    assert row["band"] == "5GHz"
    assert row["channel"] == 36
    assert row["quality_score"] == 95


def test_network_metric_to_row_extracts_canonical_fields():
    m = {
        "device_id": "pi-1",
        "collected_at": "2026-06-14T10:00:00+00:00",
        "quality": "poor",
        "quality_score": 30,
        "payload": {
            "gateway_ip": "192.168.1.1", "ap_ip": "192.168.1.103", "internet_ip": "1.1.1.1",
            "gateway_latency_ms": 1.0, "ap_latency_ms": 2.0, "internet_latency_ms": 200,
            "dns_latency_ms": 30, "packet_loss_percent": 0, "jitter_ms": 1.5,
        },
    }
    row = network_metric_to_row(m)
    assert row["gateway_latency_ms"] == 1.0
    assert row["internet_latency_ms"] == 200
    assert row["dns_latency_ms"] == 30
    assert row["quality_score"] == 30


def test_metrics_to_dataframe_empty():
    df = metrics_to_dataframe([])
    assert df.empty


def test_metrics_to_dataframe_sorts_time():
    rows = [
        {"time": "2026-01-02T00:00:00Z", "v": 2},
        {"time": "2026-01-01T00:00:00Z", "v": 1},
    ]
    df = metrics_to_dataframe(rows)
    assert "time" in df.columns
    assert df["v"].tolist() == [2, 1]


# ---------- formatters: issues & recs ----------

def test_collect_recent_recommendations_dedup():
    metrics = [
        {"recommendations": ["A", "B"]},
        {"recommendations": ["A", "C"]},
        {"recommendations": ["B"]},
    ]
    out = collect_recent_recommendations(metrics, limit=10)
    assert out == ["A", "B", "C"]


def test_collect_recent_recommendations_respects_limit():
    metrics = [{"recommendations": [f"r{i}"]} for i in range(20)]
    out = collect_recent_recommendations(metrics, limit=5)
    assert out == ["r0", "r1", "r2", "r3", "r4"]


def test_collect_recent_issues_pairs_with_explanations():
    metrics = [
        {
            "device_id": "d1",
            "collected_at": "2026-06-14T10:00:00+00:00",
            "issues": ["weak_signal", "low_snr"],
            "explanations": ["RSSI -80 dBm", "SNR 8 dB"],
            "root_cause": "wifi_signal_issue",
        }
    ]
    out = collect_recent_issues(metrics, limit=10)
    assert len(out) == 2
    assert out[0]["issue"] == "weak_signal"
    assert out[0]["explanation"] == "RSSI -80 dBm"
    assert out[0]["root_cause"] == "wifi_signal_issue"


def test_count_active_issues():
    metrics = [
        {"issues": ["weak_signal", "low_snr"]},
        {"issues": ["weak_signal", "slow_dns"]},
    ]
    counts = count_active_issues(metrics)
    assert counts == {"weak_signal": 2, "low_snr": 1, "slow_dns": 1}


# ---------- import ----------

def test_dashboard_modules_import():
    """Modules that don't import streamlit must be importable."""
    from dashboard import api_client, formatters
    assert hasattr(api_client, "get_summary")
    assert hasattr(formatters, "quality_label")
