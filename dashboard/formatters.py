"""Human-readable formatting and normalize helpers for the dashboard.

This module is pure functions; easy to test. Independent of Streamlit.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

import pandas as pd


# ---------- Category and labels ----------

QUALITY_BADGE = {
    "good": "Good",
    "warning": "Warning",
    "poor": "Poor",
}

ROOT_CAUSE_LABELS = {
    "healthy": "Network looks healthy",
    "wifi_signal_issue": "Wi-Fi signal strength may be low",
    "wifi_congestion_issue": "Wi-Fi noise or channel congestion may be the cause",
    "local_ap_issue": "Issue may be on the access point side",
    "gateway_or_lan_issue": "Issue may be on the local network (modem/cable)",
    "wan_or_isp_issue": "Latency may be on the WAN/ISP side",
    "dns_issue": "Issue may be on the DNS side",
    "single_device_issue": "Issue may be isolated to this device",
    "probe_or_backend_issue": "Issue may be on the probe or backend side",
    "unknown_issue": "Could not classify the issue",
    "possible_2ghz_limit_or_congestion": "Channel/limit issue on the 2.4 GHz band",
    "wifi_signal_or_2ghz_congestion_issue": "Wi-Fi signal or 2.4 GHz congestion",
    "wifi_signal_or_congestion_issue": "Wi-Fi signal or noise",
    "packet_loss_issue": "Packet loss issue",
}


def quality_label(q: str | None) -> str:
    if not q:
        return "Unknown"
    return QUALITY_BADGE.get(q, q)


def root_cause_label(rc: str | None) -> str:
    if not rc:
        return "—"
    return ROOT_CAUSE_LABELS.get(rc, rc)


# ---------- Time ----------

def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def fmt_time_ago(value: str | None) -> str:
    dt = parse_iso(value)
    if dt is None:
        return "—"
    delta = datetime.now(dt.tzinfo) - dt if dt.tzinfo else datetime.now() - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds} seconds ago"
    if seconds < 3600:
        return f"{seconds // 60} minutes ago"
    if seconds < 86400:
        return f"{seconds // 3600} hours ago"
    return f"{seconds // 86400} days ago"


def fmt_timestamp(value: str | None) -> str:
    dt = parse_iso(value)
    if dt is None:
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ---------- Filters ----------

def filter_metrics_by_type(metrics: list[dict], metric_type: str) -> list[dict]:
    """Return only records whose `metric_type` matches."""
    return [m for m in metrics if m.get("metric_type") == metric_type]


def latest_per_device(metrics: list[dict]) -> dict[str, dict]:
    """Return the newest metric (by collected_at) for each device."""
    out: dict[str, dict] = {}
    for m in metrics:
        did = m.get("device_id", "")
        cur = out.get(did)
        if cur is None or (m.get("collected_at") or "") > (cur.get("collected_at") or ""):
            out[did] = m
    return out


# ---------- Flatten / DataFrame ----------

def wifi_metric_to_row(metric: dict) -> dict[str, Any]:
    """Convert a Wi-Fi metric dict to a chart-ready row."""
    payload = metric.get("payload", {}) or {}
    return {
        "time": parse_iso(metric.get("collected_at")),
        "device_id": metric.get("device_id"),
        "ssid": payload.get("ssid"),
        "rssi": payload.get("rssi"),
        "snr": payload.get("snr"),
        "tx_rate_mbps": payload.get("tx_rate_mbps"),
        "rx_rate_mbps": payload.get("rx_rate_mbps"),
        "band": payload.get("band"),
        "channel": payload.get("channel"),
        "phy_mode": payload.get("phy_mode"),
        "mcs_index": payload.get("mcs_index"),
        "security": payload.get("security"),
        "bssid_redacted": payload.get("bssid_redacted"),
        "bssid_hash": payload.get("bssid_hash"),
        "quality_score": metric.get("quality_score"),
        "quality": metric.get("quality"),
    }


def network_metric_to_row(metric: dict) -> dict[str, Any]:
    """Convert a Network metric dict to a chart-ready row."""
    payload = metric.get("payload", {}) or {}
    return {
        "time": parse_iso(metric.get("collected_at")),
        "device_id": metric.get("device_id"),
        "gateway_latency_ms": payload.get("gateway_latency_ms"),
        "ap_latency_ms": payload.get("ap_latency_ms"),
        "internet_latency_ms": payload.get("internet_latency_ms"),
        "dns_latency_ms": payload.get("dns_latency_ms"),
        "packet_loss_percent": payload.get("packet_loss_percent"),
        "jitter_ms": payload.get("jitter_ms"),
        "quality_score": metric.get("quality_score"),
        "quality": metric.get("quality"),
    }


def metrics_to_dataframe(rows: list[dict], time_col: str = "time") -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if not df.empty and time_col in df.columns:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce", utc=True)
    return df


# ---------- Issues & recommendations ----------

def collect_recent_recommendations(metrics: Iterable[dict], limit: int = 10) -> list[str]:
    """Collect recommendations from recent metrics (first-seen first), dedup."""
    seen: set[str] = set()
    out: list[str] = []
    for m in metrics:
        for rec in (m.get("recommendations") or []):
            if rec and rec not in seen:
                seen.add(rec)
                out.append(rec)
                if len(out) >= limit:
                    return out
    return out


def collect_recent_issues(metrics: Iterable[dict], limit: int = 10) -> list[dict[str, Any]]:
    """Collect recent issues (code + explanation) from metrics (newest first)."""
    out: list[dict[str, Any]] = []
    for m in metrics:
        issues = m.get("issues") or []
        explanations = m.get("explanations") or []
        for i, code in enumerate(issues):
            out.append({
                "collected_at": m.get("collected_at"),
                "device_id": m.get("device_id"),
                "issue": code,
                "explanation": explanations[i] if i < len(explanations) else "",
                "root_cause": m.get("root_cause"),
            })
        if len(out) >= limit:
            return out[:limit]
    return out


def count_active_issues(metrics: list[dict]) -> dict[str, int]:
    """Issue code -> count (as seen in the most recent metrics)."""
    counts: dict[str, int] = {}
    for m in metrics:
        for code in (m.get("issues") or []):
            counts[code] = counts.get(code, 0) + 1
    return counts
