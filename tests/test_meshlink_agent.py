"""Tests for the meshlink VPN health agent and mesh quality rules."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.quality import classify_quality
from backend.app.root_cause import classify_root_cause
from collectors.meshlink_agent import (
    build_argvs,
    check_schema_version,
    payloads_from_snapshot,
    parse_status_json,
    STATUS_SCHEMA_MAJOR,
)
from dashboard.formatters import latest_per_peer
from backend.app.notifier import detect_transitions


SAMPLE_SNAPSHOT = {
    "schema_version": 1,
    "name": "b",
    "pubkey": "abc123",
    "public_endpoint": "203.0.113.20:19502",
    "relay": "203.0.113.10:19205",
    "coordinator": "203.0.113.10:19200",
    "registry": {"count": 2, "total": 3, "up_s": 12},
    "peers": [
        {
            "id": "a",
            "established": True,
            "path": "direct",
            "rtt_ms": 0.369,
            "rtt_history_ms": [0.369, 0.979],
            "rekeys": 2,
            "age_s": 647.7,
            "endpoint": "203.0.113.20:19501",
        }
    ],
}


# --- Collector mapping ---

def test_parse_status_json_tolerates_leading_noise():
    text = 'time=... level=INFO msg="public key"\n{"name": "b", "peers": []}'
    snap = parse_status_json(text)
    assert snap["name"] == "b"


def test_build_argvs_includes_preauth():
    argv = build_argvs({
        "meshlink": {
            "bin": "/usr/bin/agent",
            "name": "b",
            "keyfile": "/tmp/key",
            "coordinator": "203.0.113.10:19200",
            "coord_pubkey": "aa",
            "preauth": "secret",
        }
    })
    assert "--preauth" in argv
    assert "secret" in argv


def test_payloads_one_per_peer():
    payloads = payloads_from_snapshot(SAMPLE_SNAPSHOT)
    assert len(payloads) == 1
    p = payloads[0]
    assert p["peer_id"] == "a"
    assert p["established"] is True
    assert p["path"] == "direct"
    assert p["rtt_ms"] == 0.369
    assert p["rekeys"] == 2
    assert p["registry_count"] == 2


def test_payloads_empty_peers_is_not_peer_down():
    """No peers yet must NOT be scored as a downed peer."""
    snap = {"name": "b", "registry": {"count": 0, "total": 0, "up_s": 5}, "peers": []}
    payloads = payloads_from_snapshot(snap)
    assert len(payloads) == 1
    assert payloads[0]["established"] is None
    assert payloads[0]["registry_count"] == 0


def test_missing_schema_version_treated_as_v1():
    snap = {"name": "b", "registry": {"count": 0, "total": 0, "up_s": 1}, "peers": []}
    check_schema_version(snap)
    assert payloads_from_snapshot(snap)[0]["registry_count"] == 0


def test_unknown_schema_major_is_hard_error():
    snap = dict(SAMPLE_SNAPSHOT)
    snap["schema_version"] = STATUS_SCHEMA_MAJOR + 1
    try:
        payloads_from_snapshot(snap)
    except RuntimeError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("expected RuntimeError for unknown major")


def test_extra_fields_on_known_major_are_ignored():
    snap = dict(SAMPLE_SNAPSHOT)
    snap["future_flag"] = True
    payloads = payloads_from_snapshot(snap)
    assert payloads[0]["peer_id"] == "a"
    assert payloads[0]["rtt_ms"] == 0.369


# --- Quality rules ---

def test_mesh_direct_healthy_scores_good():
    quality, issues, score, _ = classify_quality(
        "mesh", {"established": True, "path": "direct", "rtt_ms": 5.0, "registry_count": 2}
    )
    assert quality == "good"
    assert issues == []
    assert score >= 80


def test_mesh_relay_fallback_is_warning():
    quality, issues, score, _ = classify_quality(
        "mesh", {"established": True, "path": "relay", "rtt_ms": 30.0, "registry_count": 2}
    )
    assert quality == "warning"
    assert "mesh_relay_fallback" in issues
    assert 50 <= score < 80


def test_mesh_peer_down_is_poor():
    quality, issues, score, _ = classify_quality(
        "mesh", {"established": False, "path": "none", "rtt_ms": None, "registry_count": 2}
    )
    assert quality == "poor"
    assert "mesh_peer_down" in issues
    assert score < 50


def test_mesh_high_rtt_flagged():
    _, issues, _, _ = classify_quality(
        "mesh", {"established": True, "path": "direct", "rtt_ms": 500.0, "registry_count": 2}
    )
    assert "high_mesh_latency" in issues


def test_mesh_registry_empty_flagged():
    _, issues, _, _ = classify_quality(
        "mesh", {"established": None, "path": "none", "rtt_ms": None, "registry_count": 0}
    )
    assert "mesh_registry_empty" in issues


# --- Root cause ---

def test_root_cause_mesh_mapping():
    assert classify_root_cause("mesh", {}, ["mesh_peer_down"]) == "mesh_peer_offline"
    assert classify_root_cause("mesh", {}, ["mesh_relay_fallback"]) == "nat_traversal_limited"
    assert classify_root_cause("mesh", {}, ["mesh_no_path"]) == "nat_traversal_failed"
    assert classify_root_cause("mesh", {}, ["high_mesh_latency"]) == "mesh_path_degraded"
    assert classify_root_cause("mesh", {}, ["mesh_registry_empty"]) == "coordinator_registration_issue"
    assert classify_root_cause("mesh", {}, []) == "healthy"


# --- Multi-peer dashboard grouping ---

def _metric(device, peer, est, ts):
    return {
        "device_id": device,
        "collected_at": ts,
        "payload": {"peer_id": peer, "established": est, "path": "direct"},
    }


def test_latest_per_peer_keeps_every_peer_of_a_device():
    metrics = [
        _metric("dev1", "a", True, "2026-08-21T10:00:00+00:00"),
        _metric("dev1", "b", False, "2026-08-21T10:01:00+00:00"),
        _metric("dev1", "a", True, "2026-08-21T10:02:00+00:00"),  # newer for a
    ]
    pairs = latest_per_peer(metrics)
    assert set(pairs.keys()) == {("dev1", "a"), ("dev1", "b")}
    # newest sample per peer wins
    assert pairs[("dev1", "a")]["collected_at"] == "2026-08-21T10:02:00+00:00"


# --- State-change transitions (notifications / events) ---

def test_detect_transitions_up_down_and_path():
    prev = {"peer_id": "a", "established": True, "path": "direct"}
    new = {"peer_id": "a", "established": False, "path": "none"}
    kinds = [k for k, _ in detect_transitions(prev, new)]
    assert kinds == ["peer_down"]

    up = detect_transitions(new, prev)
    assert [k for k, _ in up] == ["peer_up"]

    switch = detect_transitions(
        {"peer_id": "a", "established": True, "path": "direct"},
        {"peer_id": "a", "established": True, "path": "relay"},
    )
    assert switch == [("path_change", "peer 'a': direct → relay")]


def test_detect_transitions_first_report_is_silent():
    first = detect_transitions(None, {"peer_id": "a", "established": True, "path": "direct"})
    assert first == []
