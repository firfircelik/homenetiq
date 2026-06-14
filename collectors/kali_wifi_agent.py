"""Kali Linux (and other Linux) Wi-Fi agent.

This agent only collects telemetry when the user's own device is connected
to the user's own network. It does NOT scan neighboring networks, perform
deauth, sniffing, or any kind of attack.

System commands: `iw` (may require root or CAP_NET_ADMIN).

Structure:
- Configuration and HTTP client: shared `agents/` modules
- Payload generation: `payload_iw_link()` (pure, testable)
- Main loop: wrapped in a single error-handling layer
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Any

from agents import (
    AGENT_PROTOCOL_VERSION,
    AgentConfig,
    apply_privacy,
    bssid_redact,
    load_agent_config,
    now_iso,
    ping_stats,
    post_metric,
    post_metric_with_retry,
)
from agents.http_client import HttpError


# --- iw link output parser (pure) ---

_IW_LINK_PATTERNS = {
    "bssid": re.compile(r"Connected to\s+([0-9a-fA-F:]+)"),
    "ssid": re.compile(r"SSID:\s+(.+)"),
    "freq": re.compile(r"freq:\s+(\d+)"),
    "signal": re.compile(r"signal:\s+(-?\d+)\s+dBm"),
    "tx_bitrate": re.compile(r"tx bitrate:\s+([\d.]+)\s+MBit/s"),
    "rx_bitrate": re.compile(r"rx bitrate:\s+([\d.]+)\s+MBit/s"),
    "tx_packets": re.compile(r"tx packets\s+(\d+)"),
    "rx_packets": re.compile(r"rx packets\s+(\d+)"),
}


def parse_iw_link(output: str) -> dict[str, Any]:
    """Build a dict from `iw dev <iface> link` output.

    Every field is optional: if no connection is established, many fields
    will be missing.
    """

    data: dict[str, Any] = {}
    for key, pat in _IW_LINK_PATTERNS.items():
        m = pat.search(output)
        if not m:
            continue
        if key in ("freq", "signal", "tx_packets", "rx_packets"):
            data[key] = int(m.group(1))
        elif key in ("tx_bitrate", "rx_bitrate"):
            data[key] = float(m.group(1))
        else:
            data[key] = m.group(1).strip()
    return data


# --- Band / channel conversion (pure) ---

def freq_to_band(freq_mhz: int) -> str:
    if 2400 <= freq_mhz < 2500:
        return "2.4GHz"
    if 5000 <= freq_mhz < 5900:
        return "5GHz"
    if 5900 <= freq_mhz < 7200:
        return "6GHz"
    return "unknown"


def freq_to_channel(freq_mhz: int) -> int | None:
    if 2412 <= freq_mhz <= 2472:
        return int((freq_mhz - 2407) / 5)
    if freq_mhz == 2484:
        return 14
    if 5000 <= freq_mhz <= 5900:
        return int((freq_mhz - 5000) / 5)
    if 5955 <= freq_mhz <= 7115:
        return int((freq_mhz - 5950) / 5)
    return None


# --- Wi-Fi payload generation (pure) ---

def payload_iw_link(iw_output: str, privacy_mode: str = "redact", privacy_salt: str = "") -> dict[str, Any]:
    """Build a canonical Wi-Fi payload from iw link output.

    Canonical fields: ssid, bssid_hash/bssid_redacted, frequency_mhz,
    band, channel, tx_rate_mbps, rx_rate_mbps, rssi.
    """

    parsed = parse_iw_link(iw_output)
    payload: dict[str, Any] = {}

    if "ssid" in parsed:
        payload["ssid"] = parsed["ssid"]
    if "bssid" in parsed:
        redacted = apply_privacy(parsed["bssid"], privacy_mode, privacy_salt)
        if privacy_mode == "hash":
            payload["bssid_hash"] = redacted
        else:
            payload["bssid_redacted"] = redacted
    if "freq" in parsed:
        freq = parsed["freq"]
        payload["frequency_mhz"] = freq
        payload["band"] = freq_to_band(freq)
        ch = freq_to_channel(freq)
        if ch is not None:
            payload["channel"] = ch
    if "signal" in parsed:
        payload["rssi"] = parsed["signal"]
    if "tx_bitrate" in parsed:
        payload["tx_rate_mbps"] = parsed["tx_bitrate"]
    if "rx_bitrate" in parsed:
        payload["rx_rate_mbps"] = parsed["rx_bitrate"]
    if "tx_packets" in parsed:
        payload["tx_packets"] = parsed["tx_packets"]
    if "rx_packets" in parsed:
        payload["rx_packets"] = parsed["rx_packets"]
    return payload


# --- Linux-specific command calls ---

def _run(cmd: list[str], timeout: int = 10) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout


def detect_wifi_interface() -> str:
    output = _run(["iw", "dev"])
    match = re.search(r"Interface\s+(\S+)", output)
    if not match:
        raise RuntimeError(
            "No Wi-Fi interface found. Check `iw dev` output. "
            "Either the system has no wireless adapter, or root/CAP_NET_ADMIN is required."
        )
    return match.group(1)


def read_iw_link(interface: str) -> str:
    return _run(["iw", "dev", interface, "link"])


# --- Top-level collect & send ---

def build_metric(cfg: AgentConfig, extra_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Agent config + extra payload (Wi-Fi info) -> metric to send to backend."""
    payload: dict[str, Any] = dict(extra_payload or {})
    return {
        "device_id": cfg.device_id,
        "device_name": cfg.device_name,
        "device_type": cfg.device_type,
        "os": cfg.os,
        "agent_version": cfg.agent_version,
        "metric_type": "wifi",
        "collected_at": now_iso(),
        "payload": payload,
    }


def collect_and_send(cfg: AgentConfig, targets: dict[str, str], *, once: bool) -> dict[str, Any]:
    """One tick: collect Wi-Fi info + ping measurements and POST to backend.

    Returns: backend response dict
    """

    interface = cfg.extra.get("interface", "auto")
    if interface == "auto":
        interface = detect_wifi_interface()

    wifi = payload_iw_link(read_iw_link(interface), cfg.privacy_mode, cfg.privacy_salt)
    if not wifi:
        raise RuntimeError("Could not read Wi-Fi connection. Is the device connected to its network?")

    gateway = ping_stats(targets["gateway_ip"], timeout=cfg.timeout_seconds)
    ap = ping_stats(targets["ap_ip"], timeout=cfg.timeout_seconds)
    internet = ping_stats(targets["internet_ip"], timeout=cfg.timeout_seconds)

    wifi["ap_latency_ms"] = ap["avg_ms"]
    wifi["gateway_latency_ms"] = gateway["avg_ms"]
    wifi["internet_latency_ms"] = internet["avg_ms"]
    wifi["jitter_ms"] = internet["jitter_ms"]
    wifi["packet_loss_percent"] = internet["packet_loss_percent"]
    wifi["target_gateway_ip"] = targets["gateway_ip"]
    wifi["target_ap_ip"] = targets["ap_ip"]
    wifi["target_internet_ip"] = targets["internet_ip"]
    wifi["interface"] = interface

    metric = build_metric(cfg, wifi)
    return post_metric(
        cfg.backend_url, metric, cfg.backend_headers(), timeout=cfg.timeout_seconds,
    )


# --- Main loop ---

def main() -> int:
    parser = argparse.ArgumentParser(description="HomeNetIQ Kali/Linux Wi-Fi agent")
    parser.add_argument("--config", required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    try:
        cfg = load_agent_config(args.config)
    except Exception as exc:
        print(f"Kali agent config error: {exc}", file=sys.stderr, flush=True)
        return 1

    targets = cfg.extra.get("targets", {})
    missing = [k for k in ("gateway_ip", "ap_ip", "internet_ip") if k not in targets]
    if missing:
        print(f"Config missing target(s): {', '.join(missing)}", file=sys.stderr, flush=True)
        return 1

    while True:
        try:
            result = collect_and_send(cfg, targets, once=args.once)
            print(json.dumps({"ok": True, "backend_response": result}, ensure_ascii=False), flush=True)
        except KeyboardInterrupt:
            print("Kali agent: stopped by user.", file=sys.stderr, flush=True)
            return 0
        except Exception as exc:
            print(
                json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False),
                file=sys.stderr, flush=True,
            )
            if args.once:
                return 1
            # In continuous mode: wait retry_delay and continue
            import time as _time
            _time.sleep(cfg.retry_delay_seconds)
            continue

        if args.once:
            return 0
        import time as _time
        _time.sleep(cfg.interval_seconds)


if __name__ == "__main__":
    sys.exit(main())
