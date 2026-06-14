"""New tests for quality scoring + issue + root cause + recommendations.

The old tests are kept in `tests/test_quality.py`. These cover new
features (score, normalize, new root causes, recommendations,
backwards-compatible payload fields).
"""

from __future__ import annotations

from backend.app.quality import _normalize_band, _packet_loss, _rssi, classify_quality
from backend.app.recommendations import recommend
from backend.app.root_cause import classify_root_cause


# ---------- Helper: quick call ----------
def _q(payload, metric_type="wifi"):
    return classify_quality(metric_type, payload)


# ---------- Skor ve kategori ----------
def test_perfect_wifi_scores_high_and_healthy():
    q, issues, score, _ = _q({
        "rssi": -50, "snr": 35, "tx_rate_mbps": 200,
        "rx_rate_mbps": 200, "packet_loss_percent": 0,
    })
    assert q == "good"
    assert score >= 80
    assert classify_root_cause("wifi", {}, issues) == "healthy"


def test_weak_signal_yields_weak_signal_issue_and_wifi_signal_root():
    q, issues, score, _ = _q({"rssi": -80, "snr": 30, "tx_rate_mbps": 150})
    assert "weak_signal" in issues
    root = classify_root_cause("wifi", {}, issues)
    assert root in {"wifi_signal_issue", "wifi_congestion_issue"}
    assert q in {"warning", "poor"}
    assert score < 80


def test_low_snr_with_okay_rssi_maps_to_congestion_or_signal():
    q, issues, score, _ = _q({"rssi": -60, "snr": 12, "tx_rate_mbps": 200})
    assert "low_snr" in issues
    root = classify_root_cause("wifi", {}, issues)
    assert root in {"wifi_congestion_issue", "wifi_signal_issue"}


def test_high_gateway_and_internet_latency_becomes_gateway_or_lan():
    q, issues, score, _ = _q({
        "gateway_latency_ms": 80, "internet_latency_ms": 200,
    }, metric_type="network")
    assert "high_gateway_latency" in issues
    assert "high_internet_latency" in issues
    root = classify_root_cause("network", {}, issues)
    assert root == "gateway_or_lan_issue"


def test_high_internet_only_means_wan_or_isp():
    q, issues, score, _ = _q({
        "gateway_latency_ms": 5, "internet_latency_ms": 250,
    }, metric_type="network")
    assert "high_internet_latency" in issues
    root = classify_root_cause("network", {}, issues)
    assert root == "wan_or_isp_issue"


def test_slow_dns_becomes_dns_issue():
    q, issues, score, _ = _q({"dns_latency_ms": 500}, metric_type="network")
    assert "slow_dns" in issues
    root = classify_root_cause("network", {}, issues)
    assert root == "dns_issue"


def test_packet_loss_issue():
    q, issues, _, _ = _q({"packet_loss_percent": 10})
    assert "packet_loss" in issues
    # Just packet_loss without signal issues: single_device_issue or WAN
    root = classify_root_cause("network", {}, issues)
    assert root in {"single_device_issue", "wan_or_isp_issue", "gateway_or_lan_issue"}


def test_24ghz_band_with_low_tx_rate_marks_congestion_and_band():
    q, issues, _, _ = _q({
        "band": "2.4GHz", "tx_rate_mbps": 30, "rssi": -65, "snr": 18,
    })
    assert "using_2ghz_band" in issues
    assert "low_tx_rate" in issues
    root = classify_root_cause("wifi", {}, issues)
    assert root in {"wifi_congestion_issue", "wifi_signal_issue"}


def test_ap_unreachable_yields_local_ap_issue():
    q, issues, _, _ = _q({"ap_latency_ms": 200}, metric_type="network")
    assert "ap_unreachable" in issues
    root = classify_root_cause("network", {}, issues)
    assert root == "local_ap_issue"


def test_packet_loss_field_compat_works_as_well_as_percent():
    _, issues_a, _, _ = _q({"packet_loss_percent": 8})
    _, issues_b, _, _ = _q({"packet_loss": 8})
    assert "packet_loss" in issues_a
    assert "packet_loss" in issues_b


def test_rssi_alias_signal_works():
    _, issues_a, _, _ = _q({"rssi": -80})
    _, issues_b, _, _ = _q({"signal": -80})
    assert "weak_signal" in issues_a
    assert "weak_signal" in issues_b


def test_band_normalization_variants():
    # Different string formats should produce the same issue
    issues = [_q({"band": b, "rssi": -65, "snr": 25, "tx_rate_mbps": 100})[1] for b in
              ("2GHz", "2.4GHz", "2.4 ghz", "2g", "2G", "5GHz", "6GHz")]
    # First 5 should include using_2ghz_band
    for issues_list in issues[:5]:
        assert "using_2ghz_band" in issues_list
    # 5GHz ve 6GHz'te using_2ghz_band OLMAMAli
    assert "using_2ghz_band" not in issues[5]
    assert "using_2ghz_band" not in issues[6]


# ---------- Recommendations ----------
def test_recommendation_for_weak_signal_includes_actionable_text():
    recs = recommend(["weak_signal"], "wifi_signal_issue")
    assert any("access point" in r.lower() for r in recs)


def test_recommendation_for_healthy_is_brief():
    recs = recommend([], "healthy")
    assert len(recs) >= 1
    assert all(isinstance(r, str) and r for r in recs)


def test_recommendation_dedup_and_includes_root_cause_tip_first():
    recs = recommend(["weak_signal", "low_snr"], "wifi_signal_issue")
    # First recommendation should be the root-cause tip
    assert "Sinyal" in recs[0] or "konum" in recs[0].lower() or "AP" in recs[0]
    # Deduped
    assert len(recs) == len(set(recs))


# ---------- Score hesaplama ----------
def test_score_is_bounded_0_100():
    q, _, score, _ = _q({"rssi": -80, "snr": 5, "tx_rate_mbps": 10, "rx_rate_mbps": 10})
    assert 0 <= score <= 100
    assert q == "poor"


def test_score_thresholds_categories():
    # A single low tx_rate may keep it good (severity=1, no cumulative penalty)
    q, _, score, _ = _q({"tx_rate_mbps": 40})
    assert 80 <= score <= 100
    assert q == "good"
    # Three issues accumulate and the cumulative penalty drops it to poor
    q2, _, score2, _ = _q({"rssi": -80, "snr": 5, "tx_rate_mbps": 10})
    assert q2 == "poor"
    assert score2 < 50


# ---------- API response geriye uyumluluk ----------
def test_classify_quality_returns_four_values():
    result = classify_quality("wifi", {"rssi": -55})
    assert len(result) == 4
    quality, issues, score, explanations = result
    assert isinstance(quality, str)
    assert isinstance(issues, list)
    assert isinstance(score, int)
    assert isinstance(explanations, list)


# ---------- Helper unit ----------
def test_normalize_band_handles_none():
    assert _normalize_band(None) == ""


def test_packet_loss_helper_prefers_percent_field():
    assert _packet_loss({"packet_loss_percent": 5, "packet_loss": 50}) == 5
    assert _packet_loss({"packet_loss": 7}) == 7
    assert _packet_loss({}) is None


def test_rssi_helper_falls_back_to_signal():
    assert _rssi({"rssi": -50}) == -50
    assert _rssi({"signal": -50}) == -50
    assert _rssi({}) is None
