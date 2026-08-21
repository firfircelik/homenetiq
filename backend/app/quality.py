"""Payload -> explainable quality, issues, score, explanations.

v1 design choice: rule-based and explainable. Each issue is tied to a
threshold rule. Score is 0-100; category thresholds come from Thresholds.
"""

from __future__ import annotations

from typing import Any

from .thresholds import THRESHOLDS

T = THRESHOLDS


def _num(value: Any) -> float | None:
    """Safely convert string/int/float to float. Empty/None/NaN -> None."""
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f


def _normalize_band(value: Any) -> str:
    """Normalize a band label to a short lowercase form.

    Examples: "2GHz" / "2.4GHz" / "2.4 ghz" -> "2.4", "5GHz" -> "5", "6GHz" -> "6"
    """
    if value is None:
        return ""
    s = str(value).strip().lower().replace(" ", "")
    s = s.replace("ghz", "")
    return s


def _is_24ghz(band: str) -> bool:
    return band in {"2", "2.4", "2g"}


def _rssi(payload: dict) -> float | None:
    """Try `signal` if `rssi` is absent; otherwise None."""
    if payload.get("rssi") is not None:
        return _num(payload.get("rssi"))
    return _num(payload.get("signal"))


def _packet_loss(payload: dict) -> float | None:
    """Try `packet_loss_percent` if `packet_loss` is absent."""
    val = payload.get("packet_loss_percent")
    if val is None:
        val = payload.get("packet_loss")
    return _num(val)


def classify_quality(metric_type: str, payload: dict) -> tuple[str, list[str], int, list[str]]:
    """Analyze the payload and return (quality, issues, quality_score, explanations).

    - quality: "good" | "warning" | "poor"
    - issues: machine-readable code list (e.g. "weak_signal")
    - quality_score: 0-100 integer
    - explanations: short human-readable reason for each issue

    Both `payload.get("rssi")` and `payload.get("signal")` are accepted;
    same for `packet_loss_percent` and `packet_loss`.
    """

    issues: list[str] = []
    explanations: list[str] = []

    rssi = _rssi(payload)
    snr = _num(payload.get("snr"))
    tx_rate = _num(payload.get("tx_rate_mbps"))
    rx_rate = _num(payload.get("rx_rate_mbps"))
    local_throughput = _num(payload.get("local_throughput_mbps"))
    packet_loss = _packet_loss(payload)
    internet_latency = _num(payload.get("internet_latency_ms"))
    gateway_latency = _num(payload.get("gateway_latency_ms"))
    ap_latency = _num(payload.get("ap_latency_ms"))
    jitter = _num(payload.get("jitter_ms"))
    dns_latency = _num(payload.get("dns_latency_ms"))
    band = _normalize_band(payload.get("band"))

    score = 100  # start perfect; each issue subtracts

    # ---------- Wi-Fi signal quality ----------
    if rssi is not None:
        if rssi < T.rssi_weak:
            issues.append("weak_signal")
            explanations.append(f"RSSI {rssi} dBm below threshold ({T.rssi_weak} dBm)")
            score -= 25
        elif rssi < T.rssi_medium:
            issues.append("weak_signal")
            explanations.append(f"RSSI {rssi} dBm is moderate (threshold {T.rssi_medium} dBm)")
            score -= 10

    if snr is not None:
        if snr < T.snr_low:
            issues.append("low_snr")
            explanations.append(f"SNR {snr} dB below threshold ({T.snr_low} dB)")
            score -= 15
        elif snr < T.snr_warning:
            explanations.append(f"SNR {snr} dB in warning range (threshold {T.snr_warning} dB)")
            score -= 5

    if tx_rate is not None:
        if tx_rate < T.tx_rate_low:
            issues.append("low_tx_rate")
            explanations.append(f"TX rate {tx_rate} Mbps very low (threshold {T.tx_rate_low} Mbps)")
            score -= 10
        elif tx_rate < T.tx_rate_medium:
            explanations.append(f"TX rate {tx_rate} Mbps is moderate")
            score -= 4

    if rx_rate is not None:
        if rx_rate < T.rx_rate_low:
            issues.append("low_rx_rate")
            explanations.append(f"RX rate {rx_rate} Mbps low (threshold {T.rx_rate_low} Mbps)")
            score -= 8

    if local_throughput is not None and local_throughput < T.local_throughput_low:
        issues.append("low_local_throughput")
        explanations.append(f"Local throughput {local_throughput} Mbps low (threshold {T.local_throughput_low} Mbps)")
        score -= 8

    if _is_24ghz(band):
        issues.append("using_2ghz_band")
        explanations.append("Device is on 2.4 GHz; noise/channel conflict possible")
        score -= 5

    # ---------- Network experience ----------
    if packet_loss is not None:
        if packet_loss >= T.packet_loss_unreachable:
            issues.append("internet_unreachable")
            explanations.append(f"Packet loss {packet_loss}% (target unreachable)")
            score -= 40
        elif packet_loss > T.packet_loss_high:
            issues.append("packet_loss")
            explanations.append(f"Packet loss {packet_loss}% high (threshold {T.packet_loss_high}%)")
            score -= 25
        elif packet_loss > T.packet_loss_warning:
            issues.append("packet_loss")
            explanations.append(f"Packet loss {packet_loss}% in warning range (threshold {T.packet_loss_warning}%)")
            score -= 10

    if internet_latency is not None:
        if internet_latency > T.internet_latency_very_high:
            issues.append("high_internet_latency")
            explanations.append(f"Internet latency {internet_latency} ms very high (threshold {T.internet_latency_very_high} ms)")
            score -= 25
        elif internet_latency > T.internet_latency_high:
            issues.append("high_internet_latency")
            explanations.append(f"Internet latency {internet_latency} ms high (threshold {T.internet_latency_high} ms)")
            score -= 12

    if gateway_latency is not None and gateway_latency > T.gateway_latency_high:
        issues.append("high_gateway_latency")
        explanations.append(f"Gateway latency {gateway_latency} ms high (threshold {T.gateway_latency_high} ms)")
        score -= 12

    if ap_latency is not None:
        if ap_latency > T.ap_latency_high * 2:
            issues.append("ap_unreachable")
            explanations.append(f"AP latency {ap_latency} ms very high; AP may be unreachable")
            score -= 30
        elif ap_latency > T.ap_latency_high:
            issues.append("high_ap_latency")
            explanations.append(f"AP latency {ap_latency} ms high (threshold {T.ap_latency_high} ms)")
            score -= 10

    if jitter is not None:
        if jitter > T.jitter_high:
            issues.append("high_jitter")
            explanations.append(f"Jitter {jitter} ms high (threshold {T.jitter_high} ms)")
            score -= 10
        elif jitter > T.jitter_warning:
            issues.append("high_jitter")
            explanations.append(f"Jitter {jitter} ms in warning range (threshold {T.jitter_warning} ms)")
            score -= 4

    if dns_latency is not None and dns_latency > T.dns_latency_slow:
        issues.append("slow_dns")
        explanations.append(f"DNS latency {dns_latency} ms high (threshold {T.dns_latency_slow} ms)")
        score -= 10

    # ---------- meshlink overlay (VPN tunnel health) ----------
    established = payload.get("established")
    path = str(payload.get("path") or "").strip().lower()
    mesh_rtt = _num(payload.get("rtt_ms"))

    if established is False:
        issues.append("mesh_peer_down")
        explanations.append("Mesh peer is registered but the encrypted session is not established")
        score -= 55
    elif established is True:
        if path == "none":
            issues.append("mesh_no_path")
            explanations.append("Session exists but no working path (direct or relay) was found")
            score -= 35
        elif path == "relay":
            issues.append("mesh_relay_fallback")
            explanations.append("Traffic is going through the relay; direct path was not possible")
            score -= 25

    if mesh_rtt is not None:
        if mesh_rtt > T.mesh_rtt_very_high:
            issues.append("high_mesh_latency")
            explanations.append(f"Tunnel RTT {mesh_rtt} ms very high (threshold {T.mesh_rtt_very_high} ms)")
            score -= 25
        elif mesh_rtt > T.mesh_rtt_high:
            issues.append("high_mesh_latency")
            explanations.append(f"Tunnel RTT {mesh_rtt} ms high (threshold {T.mesh_rtt_high} ms)")
            score -= 12

    registry_count = _num(payload.get("registry_count"))
    if registry_count == 0:
        issues.append("mesh_registry_empty")
        explanations.append("Coordinator registry reports no peers; registration may have failed")
        score -= 10

    # ---------- Clamp score and map to category ----------
    # Cumulative penalty when multiple "severe" issues accumulate; prevents
    # borderline cases from being classified as "warning".
    severe_codes = {
        "weak_signal", "low_snr", "low_tx_rate", "low_rx_rate",
        "packet_loss", "high_internet_latency", "high_gateway_latency",
        "high_ap_latency", "ap_unreachable", "internet_unreachable",
        "mesh_peer_down",
    }
    severe_count = sum(1 for i in issues if i in severe_codes)
    if severe_count >= 3:
        score -= 10
    elif severe_count >= 2:
        score -= 5

    score = max(0, min(100, score))
    if score >= T.score_good_min:
        quality = "good"
    elif score >= T.score_warning_min:
        quality = "warning"
    else:
        quality = "poor"

    return quality, issues, score, explanations
