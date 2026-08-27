"""macOS Wi-Fi agent.

System commands: `system_profiler SPAirPortDataType`, `wdutil`, `ipconfig`.
Only collects telemetry when the user's own device is connected to the
user's own network. It does NOT scan or attack other networks.

`system_profiler` does not require root, but the adapter must be on and
connected to a network.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Any

from agents import (
    AgentConfig,
    apply_privacy,
    load_agent_config,
    empty_required_targets,
    now_iso,
    ping_stats,
    post_metric,
)
from agents.http_client import HttpError


# --- Parser'lar (saf, mocklanabilir) ---

_CHANNEL_RE = re.compile(r"Channel:\s*(\d+)")
_BAND_RE = re.compile(r"Network Type:\s*([^\n]+)")
_SIGNAL_RE = re.compile(r"Signal / Noise:\s*(-?\d+)\s*dBm\s*/\s*(-?\d+)\s*dBm")
_TX_RATE_RE = re.compile(r"Transmit Rate:\s*([\d.]+)\s*Mbps")
_SECURITY_RE = re.compile(r"Security:\s*([^\n]+)")
_MCS_RE = re.compile(r"MCS Index:\s*(\d+)")
_PHY_RE = re.compile(r"PHY Mode:\s*([^\n]+)")
_CHANNEL_WIDTH_RE = re.compile(r"Channel Width:\s*(\d+)\s*MHz")
_SSID_RE = re.compile(r"^\s*([^\s:][^:]*?):\s*$", re.MULTILINE)


def _channel_to_band_freq(channel: int) -> tuple[str, int]:
    """Estimate band and approximate center frequency from a channel number."""
    if 1 <= channel <= 14:
        return "2.4GHz", 2407 + channel * 5
    if 36 <= channel <= 165:
        return "5GHz", 5000 + channel * 5
    if 1 <= channel <= 233:
        return "6GHz", 5950 + channel * 5
    return "unknown", 0


def parse_system_profiler(output: str) -> dict[str, Any]:
    """Parse `system_profiler SPAirPortDataType` output.

    Typical format (summary):

        Current Network Information:
            SSID:
                MyWiFi:
                    PHY Mode: 802.11ax
                    Channel: 36
                    Network Type: 5 GHz
                    Signal / Noise: -47 dBm / -95 dBm
                    Transmit Rate: 1200 Mbps
                    MCS Index: 11
                    Security: WPA2 Personal
    """

    data: dict[str, Any] = {}
    ssid_match = re.search(
        r"Current Network Information:\s*\n\s*([^\n:]+):\s*\n", output
    )
    if ssid_match:
        data["ssid"] = ssid_match.group(1).strip()

    ch = _CHANNEL_RE.search(output)
    if ch:
        channel = int(ch.group(1))
        data["channel"] = channel
        band, freq = _channel_to_band_freq(channel)
        data["band"] = band
        if freq:
            data["frequency_mhz"] = freq

    sig = _SIGNAL_RE.search(output)
    if sig:
        rssi = int(sig.group(1))
        noise = int(sig.group(2))
        data["rssi"] = rssi
        data["noise"] = noise
        data["snr"] = rssi - noise  # dB

    rate = _TX_RATE_RE.search(output)
    if rate:
        data["tx_rate_mbps"] = float(rate.group(1))

    sec = _SECURITY_RE.search(output)
    if sec:
        data["security"] = sec.group(1).strip()

    mcs = _MCS_RE.search(output)
    if mcs:
        data["mcs_index"] = int(mcs.group(1))

    phy = _PHY_RE.search(output)
    if phy:
        data["phy_mode"] = phy.group(1).strip()

    width = _CHANNEL_WIDTH_RE.search(output)
    if width:
        data["channel_width_mhz"] = int(width.group(1))

    # BSSID is not directly exposed by macOS system_profiler; could be added via wdutil/info.
    return data


def payload_from_macos(data: dict[str, Any], privacy_mode: str = "redact", privacy_salt: str = "") -> dict[str, Any]:
    """Build a canonical payload from the parsed dict."""
    out: dict[str, Any] = {}
    for k in ("ssid", "frequency_mhz", "band", "channel", "channel_width_mhz",
              "rssi", "snr", "noise", "tx_rate_mbps", "rx_rate_mbps",
              "mcs_index", "phy_mode", "security"):
        if k in data:
            out[k] = data[k]
    if "bssid" in data:
        if privacy_mode == "hash":
            out["bssid_hash"] = apply_privacy(data["bssid"], "hash", privacy_salt)
        else:
            out["bssid_redacted"] = apply_privacy(data["bssid"], "redact")
    return out


# --- macOS-specific system calls ---

def read_system_profiler() -> str:
    result = subprocess.run(
        ["system_profiler", "SPAirPortDataType"],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"system_profiler hata verdi: {result.stderr}")
    return result.stdout


# --- Top-level collect & send ---

def build_metric(cfg: AgentConfig, extra_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "device_id": cfg.device_id,
        "device_name": cfg.device_name,
        "device_type": cfg.device_type,
        "os": cfg.os,
        "agent_version": cfg.agent_version,
        "metric_type": "wifi",
        "collected_at": now_iso(),
        "payload": extra_payload,
    }


def collect_and_send(cfg: AgentConfig, targets: dict[str, str], *, once: bool) -> dict[str, Any]:
    sp_output = read_system_profiler()
    parsed = parse_system_profiler(sp_output)
    payload = payload_from_macos(parsed, cfg.privacy_mode, cfg.privacy_salt)
    if not payload.get("ssid"):
        raise RuntimeError("Could not read Wi-Fi connection (no SSID). Is the device connected to a network?")

    gateway = ping_stats(targets["gateway_ip"], timeout=cfg.timeout_seconds)
    ap = ping_stats(targets["ap_ip"], timeout=cfg.timeout_seconds)
    internet = ping_stats(targets["internet_ip"], timeout=cfg.timeout_seconds)
    payload["ap_latency_ms"] = ap["avg_ms"]
    payload["gateway_latency_ms"] = gateway["avg_ms"]
    payload["internet_latency_ms"] = internet["avg_ms"]
    payload["jitter_ms"] = internet["jitter_ms"]
    payload["packet_loss_percent"] = internet["packet_loss_percent"]
    payload["target_gateway_ip"] = targets["gateway_ip"]
    payload["target_ap_ip"] = targets["ap_ip"]
    payload["target_internet_ip"] = targets["internet_ip"]

    metric = build_metric(cfg, payload)
    return post_metric(cfg.backend_url, metric, cfg.backend_headers(), timeout=cfg.timeout_seconds)


# --- Main loop ---

def main() -> int:
    parser = argparse.ArgumentParser(description="HomeNetIQ macOS Wi-Fi agent")
    parser.add_argument("--config", required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    try:
        cfg = load_agent_config(args.config)
    except Exception as exc:
        print(f"macOS agent config error: {exc}", file=sys.stderr, flush=True)
        return 1

    targets = cfg.extra.get("targets", {})
    missing = empty_required_targets(targets)
    if missing:
        print(
            f"targets.{missing[0]} empty — fill YOUR network (init does not invent a gateway)",
            file=sys.stderr,
            flush=True,
        )
        return 1

    while True:
        try:
            result = collect_and_send(cfg, targets, once=args.once)
            print(json.dumps({"ok": True, "backend_response": result}, ensure_ascii=False), flush=True)
        except KeyboardInterrupt:
            print("macOS agent: stopped by user.", file=sys.stderr, flush=True)
            return 0
        except Exception as exc:
            print(
                json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False),
                file=sys.stderr, flush=True,
            )
            if args.once:
                return 1
            import time as _time
            _time.sleep(cfg.retry_delay_seconds)
            continue

        if args.once:
            return 0
        import time as _time
        _time.sleep(cfg.interval_seconds)


if __name__ == "__main__":
    sys.exit(main())
