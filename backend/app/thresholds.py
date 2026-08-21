"""All quality and root-cause thresholds collected in one place.

Stored as a frozen dataclass so they can later be overridden via YAML/env.
For now defaults are hard-coded.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    """Threshold values. Hard-coded in v1; can be overridden later."""

    # --- Wi-Fi sinyal kalitesi ---
    rssi_weak: float = -75.0
    rssi_medium: float = -67.0
    snr_low: float = 15.0
    snr_warning: float = 20.0

    # --- Throughput ---
    tx_rate_low: float = 50.0
    tx_rate_medium: float = 100.0
    rx_rate_low: float = 50.0
    local_throughput_low: float = 20.0

    # --- Latency (ms) ---
    gateway_latency_high: float = 30.0
    ap_latency_high: float = 30.0
    internet_latency_high: float = 100.0
    internet_latency_very_high: float = 150.0
    dns_latency_slow: float = 200.0
    jitter_warning: float = 10.0
    jitter_high: float = 30.0

    # --- Packet loss (percent) ---
    packet_loss_warning: float = 2.0
    packet_loss_high: float = 5.0
    # "unreachable" threshold: ping failure means packet_loss is 100
    packet_loss_unreachable: float = 100.0

    # --- meshlink overlay (VPN tüneli) ---
    # RTT is end-to-end through the encrypted tunnel; LAN-direct paths are
    # typically <5 ms, relay paths and cross-WAN paths are higher.
    mesh_rtt_high: float = 150.0
    mesh_rtt_very_high: float = 400.0

    # --- Skor kategorileri ---
    score_good_min: int = 80
    score_warning_min: int = 50


THRESHOLDS = Thresholds()
