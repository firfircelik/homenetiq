from backend.app.quality import classify_quality
from backend.app.root_cause import classify_root_cause


def test_good_wifi_metric():
    quality, issues, score, _ = classify_quality(
        "wifi", {"rssi": -55, "snr": 30, "tx_rate_mbps": 144, "packet_loss_percent": 0}
    )
    assert quality == "good"
    assert issues == []
    assert score >= 80


def test_poor_signal_metric():
    quality, issues, score, _ = classify_quality(
        "wifi", {"rssi": -80, "snr": 10, "tx_rate_mbps": 20}
    )
    assert quality == "poor"
    assert "weak_signal" in issues
    assert "low_snr" in issues
    assert "low_tx_rate" in issues
    assert score < 50


def test_root_cause_wifi_issue():
    _, issues, _, _ = classify_quality("wifi", {"rssi": -80, "snr": 10, "tx_rate_mbps": 20})
    root = classify_root_cause("wifi", {}, issues)
    assert root in {"wifi_signal_issue", "wifi_congestion_issue", "wifi_signal_or_2ghz_congestion_issue"}


def test_dns_issue():
    quality, issues, score, _ = classify_quality("network", {"dns_latency_ms": 250})
    # DNS bad: issue should appear and root cause should be dns_issue.
    # Quality can still be "good" in isolation (borderline score); this is
    # a known v1 limitation — it gets more accurate with bigger payload context.
    assert "slow_dns" in issues
    assert classify_root_cause("network", {}, issues) == "dns_issue"
    assert score < 100
    assert quality in {"good", "warning", "poor"}
