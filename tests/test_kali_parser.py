"""Agent/parser canonical payload tests.

The old `test_kali_parser.py` covered the pre-refactor Kali agent. The
new tests verify canonical payload generation and privacy behavior.
"""

from __future__ import annotations

from collectors import kali_wifi_agent
from collectors import macos_wifi_agent
from agents import bssid_hash, bssid_redact, ping_stats, apply_privacy
from agents.ping import _unreachable  # type: ignore
from probes import pi_network_probe
import subprocess
import unittest.mock as mock


# ---------- Kali parser ----------

SAMPLE_IW_LINK = """\
Connected to 00:11:22:33:44:55 (on wlan0)
\tSSID: YOUR_SSID
\tfreq: 5180
\tsignal: -47 dBm
\ttx bitrate: 433.3 MBit/s
\trx bitrate: 433.3 MBit/s
\tbss flags:\tshort-slot-time
\tdtim period:\t2
\tbeacon int:\t100
"""


def test_parse_iw_link_extracts_all_fields():
    parsed = kali_wifi_agent.parse_iw_link(SAMPLE_IW_LINK)
    assert parsed["bssid"] == "00:11:22:33:44:55"
    assert parsed["ssid"] == "YOUR_SSID"
    assert parsed["freq"] == 5180
    assert parsed["signal"] == -47
    assert parsed["tx_bitrate"] == 433.3
    assert parsed["rx_bitrate"] == 433.3


def test_parse_iw_link_handles_missing_fields():
    parsed = kali_wifi_agent.parse_iw_link("Connected to 00:11:22:33:44:55\n")
    assert parsed["bssid"] == "00:11:22:33:44:55"
    assert "ssid" not in parsed
    assert "rssi" not in parsed


def test_freq_to_band_canonical_strings():
    """Canonical band stringleri: 2.4GHz, 5GHz, 6GHz."""
    assert kali_wifi_agent.freq_to_band(2412) == "2.4GHz"
    assert kali_wifi_agent.freq_to_band(5180) == "5GHz"
    assert kali_wifi_agent.freq_to_band(6135) == "6GHz"
    assert kali_wifi_agent.freq_to_band(900) == "unknown"


def test_freq_to_channel_common():
    assert kali_wifi_agent.freq_to_channel(2412) == 1
    assert kali_wifi_agent.freq_to_channel(2437) == 6
    assert kali_wifi_agent.freq_to_channel(2462) == 11
    assert kali_wifi_agent.freq_to_channel(5180) == 36
    assert kali_wifi_agent.freq_to_channel(5955) == 1
    assert kali_wifi_agent.freq_to_channel(6135) == 37
    assert kali_wifi_agent.freq_to_channel(2484) == 14
    assert kali_wifi_agent.freq_to_channel(1000) is None


def test_payload_iw_link_canonical_fields():
    payload = kali_wifi_agent.payload_iw_link(SAMPLE_IW_LINK)
    assert payload["ssid"] == "YOUR_SSID"
    assert payload["frequency_mhz"] == 5180
    assert payload["band"] == "5GHz"
    assert payload["channel"] == 36
    assert payload["rssi"] == -47
    assert payload["tx_rate_mbps"] == 433.3
    assert payload["rx_rate_mbps"] == 433.3
    # Privacy: default redact -> bssid_redacted, bssid_hash OLMAMALI
    assert "bssid_redacted" in payload
    assert "bssid_hash" not in payload
    assert payload["bssid_redacted"] == "...:44:55"


def test_payload_iw_link_hash_mode_uses_salt():
    payload = kali_wifi_agent.payload_iw_link(SAMPLE_IW_LINK, privacy_mode="hash", privacy_salt="my-salt")
    assert "bssid_hash" in payload
    assert "bssid_redacted" not in payload
    # Same salt + same BSSID should produce the same hash
    h = payload["bssid_hash"]
    assert bssid_hash("00:11:22:33:44:55", salt="my-salt") == h
    # Different salt -> different hash
    assert bssid_hash("00:11:22:33:44:55", salt="other-salt") != h


# ---------- macOS parser ----------

SAMPLE_MACOS = """
Wi-Fi:

    Software Versions:
        CoreWLAN: ...
        CoreWLANKit: ...
    Current Network Information:
        YOUR_SSID:
            PHY Mode: 802.11ax
            Channel: 36
            Network Type: 5 GHz
            Signal / Noise: -47 dBm / -95 dBm
            Transmit Rate: 1200 Mbps
            MCS Index: 11
            Security: WPA2 Personal
            Channel Width: 80 MHz
"""


def test_parse_macos_extracts_signal_snr_band_channel():
    parsed = macos_wifi_agent.parse_system_profiler(SAMPLE_MACOS)
    assert parsed["ssid"] == "YOUR_SSID"
    assert parsed["channel"] == 36
    assert parsed["band"] == "5GHz"
    assert parsed["rssi"] == -47
    assert parsed["noise"] == -95
    # SNR = RSSI - noise
    assert parsed["snr"] == 48
    assert parsed["tx_rate_mbps"] == 1200.0
    assert parsed["mcs_index"] == 11
    assert parsed["phy_mode"] == "802.11ax"
    assert parsed["security"] == "WPA2 Personal"
    assert parsed["channel_width_mhz"] == 80


def test_payload_from_macos_canonical_fields():
    parsed = macos_wifi_agent.parse_system_profiler(SAMPLE_MACOS)
    payload = macos_wifi_agent.payload_from_macos(parsed)
    for k in ("ssid", "frequency_mhz", "band", "channel", "channel_width_mhz",
              "rssi", "snr", "noise", "tx_rate_mbps", "mcs_index", "phy_mode", "security"):
        assert k in payload, f"eksik canonical alan: {k}"


# ---------- Pi network probe ----------

def test_dns_latency_returns_number_or_none():
    # Valid domain
    v = pi_network_probe.dns_latency_ms("example.com")
    assert v is None or v > 0


def test_build_network_payload_canonical_keys():
    targets = {
        "gateway_ip": "127.0.0.1", "ap_ip": "127.0.0.1", "internet_ip": "127.0.0.1",
        "dns_domains": ["example.com"],
    }
    payload = pi_network_probe.build_network_payload(targets, timeout=2)
    for k in ("gateway_ip", "ap_ip", "internet_ip",
              "gateway_latency_ms", "ap_latency_ms", "internet_latency_ms",
              "packet_loss_percent", "jitter_ms", "dns_latency_ms"):
        assert k in payload, f"eksik canonical alan: {k}"


# ---------- Privacy ----------

def test_bssid_redact_keeps_last_octets():
    assert bssid_redact("00:11:22:33:44:55") == "...:44:55"
    assert bssid_redact("AA:BB:CC:DD:EE:FF") == "...:EE:FF"


def test_bssid_redact_handles_invalid():
    assert bssid_redact(None) is None
    assert bssid_redact("") is None
    assert bssid_redact("not-a-mac") is None
    assert bssid_redact("11:22:33") is None  # eksik oktet


def test_bssid_hash_is_deterministic_with_salt():
    h1 = bssid_hash("00:11:22:33:44:55", salt="salt-A")
    h2 = bssid_hash("00:11:22:33:44:55", salt="salt-A")
    assert h1 == h2
    assert h1 != bssid_hash("00:11:22:33:44:55", salt="salt-B")
    assert h1 != bssid_hash("aa:bb:cc:dd:ee:ff", salt="salt-A")


def test_apply_privacy_dispatch():
    assert apply_privacy("00:11:22:33:44:55", "redact") == "...:44:55"
    h = apply_privacy("00:11:22:33:44:55", "hash", salt="s")
    assert h == bssid_hash("00:11:22:33:44:55", salt="s")


# ---------- Ping (shared) ----------

def test_ping_stats_handles_timeout(monkeypatch):
    """ping komutu timeout olursa packet_loss=100, latency=None."""
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(["ping"], 1)
    monkeypatch.setattr("agents.ping.subprocess.run", fake_run)
    result = ping_stats("127.0.0.1", count=1, timeout=1)
    assert result["avg_ms"] is None
    assert result["packet_loss_percent"] == 100.0


def test_ping_stats_blank_target_does_not_run_ping(monkeypatch):
    def fake_run(*args, **kwargs):
        raise AssertionError("ping must not run for a blank target")

    monkeypatch.setattr("agents.ping.subprocess.run", fake_run)
    result = ping_stats("", count=1, timeout=1)
    assert result["avg_ms"] is None
    assert result["packet_loss_percent"] == 100.0
