"""Likely root-cause label from an issue list.

Order matters: start with the most specific condition and fall back.
Keep each branch short and uncommented so it stays explainable.
"""

from __future__ import annotations


def classify_root_cause(metric_type: str, payload: dict, issues: list[str]) -> str:
    """Simple root-cause classification.

    Goal: instead of just saying "bad", tell the user where the issue
    likely is. v1 keeps this deterministic and explainable.
    """

    issue_set = set(issues)

    # A single-device metric cannot be benchmarked, so it relies only on
    # that device's own observations. If both AP and internet are
    # unreachable, the issue may be on the probe or backend side.
    if "ap_unreachable" in issue_set and "internet_unreachable" in issue_set:
        return "probe_or_backend_issue"

    if "ap_unreachable" in issue_set:
        return "local_ap_issue"

    if "high_ap_latency" in issue_set:
        return "local_ap_issue"

    if "high_gateway_latency" in issue_set and "high_internet_latency" in issue_set:
        # If both gateway and internet are slow, the issue is most likely
        # on the LAN side (modem, cable, AP).
        return "gateway_or_lan_issue"

    if "slow_dns" in issue_set and "high_internet_latency" not in issue_set:
        return "dns_issue"

    if "packet_loss" in issue_set or "internet_unreachable" in issue_set:
        if {"weak_signal", "low_snr"} & issue_set:
            return "wifi_signal_issue"
        if "using_2ghz_band" in issue_set:
            return "wifi_congestion_issue"
        # Signal is good but there is still packet loss: isolate to this device
        return "single_device_issue"

    if {"weak_signal", "low_snr", "low_tx_rate"} & issue_set:
        if "using_2ghz_band" in issue_set:
            return "wifi_congestion_issue"
        return "wifi_signal_issue"

    if "low_snr" in issue_set and "weak_signal" not in issue_set:
        # Signal is fine but SNR is low: environmental noise
        return "wifi_congestion_issue"

    if {"high_internet_latency"} & issue_set and "high_gateway_latency" not in issue_set:
        return "wan_or_isp_issue"

    if "high_gateway_latency" in issue_set:
        return "gateway_or_lan_issue"

    if "using_2ghz_band" in issue_set:
        return "possible_2ghz_limit_or_congestion"

    if not issues:
        return "healthy"

    return "unknown_issue"
