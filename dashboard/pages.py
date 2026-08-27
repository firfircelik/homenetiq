"""Dashboard page render functions.

Each `render_*` function draws Streamlit UI and pulls data from the
backend as needed. This keeps `streamlit_app.py` as a thin router.
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st

from .api_client import (
    ApiUnavailable,
    get_backend_url,
    get_devices,
    get_latest_metrics,
    get_mesh_events,
    get_settings,
    get_summary,
    update_settings,
)
from .formatters import (
    collect_recent_issues,
    collect_recent_recommendations,
    count_active_issues,
    filter_metrics_by_type,
    fmt_bytes,
    fmt_time_ago,
    fmt_timestamp,
    latest_per_device,
    latest_per_peer,
    mesh_metric_to_row,
    metrics_to_dataframe,
    network_metric_to_row,
    quality_label,
    root_cause_label,
    wifi_metric_to_row,
)


METRIC_LIMIT = 200


# ---------- Data loading helpers ----------

@st.cache_data(ttl=10)
def _cached_summary() -> dict[str, Any]:
    return get_summary()


@st.cache_data(ttl=10)
def _cached_devices() -> list[dict[str, Any]]:
    return get_devices()


@st.cache_data(ttl=10)
def _cached_latest_metrics(limit: int) -> list[dict[str, Any]]:
    return get_latest_metrics(limit=limit)


def _safe_load_summary() -> dict[str, Any] | None:
    try:
        return _cached_summary()
    except ApiUnavailable as exc:
        st.error(str(exc))
        return None


def _safe_load_devices() -> list[dict[str, Any]] | None:
    try:
        return _cached_devices()
    except ApiUnavailable as exc:
        st.error(str(exc))
        return None


def _safe_load_metrics() -> list[dict[str, Any]] | None:
    try:
        return _cached_latest_metrics(METRIC_LIMIT)
    except ApiUnavailable as exc:
        st.error(str(exc))
        return None


# ---------- Pages ----------

def render_overview() -> None:
    st.header("Overview")
    summary = _safe_load_summary()
    devices = _safe_load_devices()
    metrics = _safe_load_metrics()

    if not summary or summary.get("sample_count", 0) == 0:
        st.info("No metrics received yet. Waiting for agents to report.")
        return

    latest = summary.get("latest") or {}
    quality = latest.get("quality")
    score = latest.get("quality_score")
    root_cause = latest.get("root_cause")
    issues = latest.get("issues") or []
    last_time = latest.get("collected_at")

    cols = st.columns(4)
    cols[0].metric("Overall Health", quality_label(quality))
    cols[1].metric("Quality Score", f"{score}/100" if score is not None else "—")
    cols[2].metric("Root Cause", root_cause_label(root_cause))
    cols[3].metric("Last Sample", fmt_time_ago(last_time))

    if devices is not None:
        counts = {"active": 0, "stale": 0, "offline": 0}
        for d in devices:
            s = d.get("status")
            if s in counts:
                counts[s] += 1
        dcols = st.columns(3)
        dcols[0].metric("Active Devices", counts["active"])
        dcols[1].metric("Stale Devices", counts["stale"])
        dcols[2].metric("Offline Devices", counts["offline"])

    st.subheader("Latest Measurement")
    st.write(
        f"**Device:** `{latest.get('device_id')}` • "
        f"**Type:** `{latest.get('metric_type')}` • "
        f"**Time:** {fmt_timestamp(last_time)}"
    )

    st.subheader("Top Issues (recent metrics)")
    if metrics:
        issue_counts = count_active_issues(metrics)
        if issue_counts:
            df = pd.DataFrame(
                [{"issue": k, "count": v} for k, v in sorted(issue_counts.items(), key=lambda x: -x[1])]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.success("No active issues right now.")
    else:
        st.info("No metrics to show issues for.")

    st.subheader("Top Recommendations")
    if metrics:
        recs = collect_recent_recommendations(metrics, limit=5)
        if recs:
            for r in recs:
                st.markdown(f"- {r}")
        else:
            st.info("No recommendations yet.")
    else:
        st.info("No metrics to show recommendations for.")


def render_devices() -> None:
    st.header("Devices")
    devices = _safe_load_devices()
    metrics = _safe_load_metrics()
    if devices is None:
        return
    if not devices:
        st.info("No devices registered yet.")
        return

    latest = latest_per_device(metrics or [])

    rows = []
    for d in devices:
        did = d.get("device_id")
        m = latest.get(did) or {}
        rows.append({
            "device_id": did,
            "device_name": d.get("device_name"),
            "device_type": d.get("device_type"),
            "os": d.get("os"),
            "status": d.get("status"),
            "first_seen": fmt_timestamp(d.get("first_seen")),
            "last_seen": fmt_time_ago(d.get("last_seen")),
            "latest_quality": m.get("quality"),
            "latest_quality_score": m.get("quality_score"),
            "latest_root_cause": m.get("root_cause"),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(
        "**active** = recent sample. "
        "**stale** = no data for a while. "
        "**offline** = no data for a long time."
    )


def _render_chart_or_empty(df: pd.DataFrame, value_col: str, title: str) -> None:
    sub = df.dropna(subset=[value_col])
    if sub.empty:
        st.info(f"No data yet for `{value_col}`.")
        return
    st.line_chart(sub.set_index("time")[[value_col]])


def render_wifi_metrics() -> None:
    st.header("Wi-Fi Metrics")
    metrics = _safe_load_metrics()
    if metrics is None:
        return
    wifi = filter_metrics_by_type(metrics, "wifi")
    if not wifi:
        st.info("No Wi-Fi metrics yet. Run a Kali or macOS agent.")
        return

    rows = [wifi_metric_to_row(m) for m in wifi]
    df = metrics_to_dataframe(rows)
    df = df.sort_values("time")

    latest_payload = (wifi[0].get("payload") or {})
    st.subheader("Latest Connection")
    lcols = st.columns(3)
    lcols[0].write(f"**SSID:** `{latest_payload.get('ssid') or '—'}`")
    lcols[1].write(
        f"**BSSID:** `{latest_payload.get('bssid_redacted') or latest_payload.get('bssid_hash') or '—'}`"
    )
    lcols[2].write(f"**Band/Channel:** `{latest_payload.get('band') or '—'} / {latest_payload.get('channel') or '—'}`")
    lcols3 = st.columns(3)
    lcols3[0].write(f"**PHY Mode:** `{latest_payload.get('phy_mode') or '—'}`")
    lcols3[1].write(f"**MCS Index:** `{latest_payload.get('mcs_index') or '—'}`")
    lcols3[2].write(f"**Security:** `{latest_payload.get('security') or '—'}`")

    st.subheader("Signal Time Series")
    _render_chart_or_empty(df, "rssi", "RSSI")
    _render_chart_or_empty(df, "snr", "SNR")
    _render_chart_or_empty(df, "tx_rate_mbps", "Tx Rate")

    st.subheader("Band Distribution")
    band_counts = df["band"].dropna().value_counts()
    if not band_counts.empty:
        st.bar_chart(band_counts)
    else:
        st.info("No band information yet.")


def render_network_metrics() -> None:
    st.header("Network Metrics")
    metrics = _safe_load_metrics()
    if metrics is None:
        return
    net = filter_metrics_by_type(metrics, "network")
    if not net:
        st.info("No network metrics yet. Run the Pi probe.")
        return

    rows = [network_metric_to_row(m) for m in net]
    df = metrics_to_dataframe(rows)
    df = df.sort_values("time")

    st.subheader("Latency (ms)")
    for col in ("gateway_latency_ms", "ap_latency_ms", "internet_latency_ms", "dns_latency_ms"):
        _render_chart_or_empty(df, col, col)

    st.subheader("Reliability")
    _render_chart_or_empty(df, "packet_loss_percent", "packet_loss_percent")
    _render_chart_or_empty(df, "jitter_ms", "jitter_ms")

    st.subheader("Quick Notes")
    latest = net[0]
    payload = latest.get("payload") or {}
    gw = payload.get("gateway_latency_ms")
    inet = payload.get("internet_latency_ms")
    dns = payload.get("dns_latency_ms")
    ap = payload.get("ap_latency_ms")
    loss = payload.get("packet_loss_percent")

    notes: list[str] = []
    if gw is not None and inet is not None and gw < 30 and inet and inet > 100:
        notes.append("- Gateway looks fine, internet is high → may be **WAN/ISP** latency.")
    if dns is not None and dns > 200:
        notes.append("- DNS latency is high → may be a **DNS** issue.")
    if ap is not None and ap > 30:
        notes.append("- AP latency is high → may be a **local AP** issue.")
    if loss is not None and loss >= 5:
        notes.append("- Packet loss is high → connection may be unstable.")
    if not notes:
        notes.append("- No notable anomaly at the moment.")
    for n in notes:
        st.markdown(n)


def render_mesh() -> None:
    st.header("Mesh VPN (meshlink)")
    metrics = _safe_load_metrics()
    if metrics is None:
        return
    mesh = filter_metrics_by_type(metrics, "mesh")
    if not mesh:
        st.info(
            "No mesh metrics yet. Start the meshlink agent collector: "
            "`collectors/meshlink_agent.py --config config/meshlink_agent.yaml` "
            "(see About / Setup)."
        )
        return

    # --- Latest state per (device, peer): a device may report MANY peers,
    # each as its own metric — grouping by device alone would hide peers.
    latest_by_pair = latest_per_peer(mesh)
    rows = [mesh_metric_to_row(m) for m in latest_by_pair.values()]
    df = pd.DataFrame(rows)

    established = df["established"].apply(lambda v: v is True)
    paths = df["path"].fillna("none")
    cols = st.columns(4)
    cols[0].metric("Peers Seen", len(df))
    cols[1].metric("Established", int(established.sum()))
    cols[2].metric("Direct Paths", int((paths == "direct").sum()))
    cols[3].metric("Relay Fallbacks", int((paths == "relay").sum()))

    st.subheader("Peer Status")
    table = pd.DataFrame(
        {
            "Peer": df["peer_id"],
            "Endpoint": df["endpoint"],
            "Path": paths,
            "RTT (ms)": df["rtt_ms"],
            "Rekeys": df["rekeys"],
            "Traffic (TX/RX)": [
                f"{fmt_bytes(tx)} / {fmt_bytes(rx)}"
                for tx, rx in zip(df["bytes_sent"], df["bytes_recv"])
            ],
            "Session Age (s)": df["session_age_s"].round(0),
            "Score": df["quality_score"],
            "Health": df["quality"].map(quality_label),
        }
    )
    st.dataframe(table, hide_index=True, use_container_width=True)

    # --- RTT trend over time ---
    hist = metrics_to_dataframe([mesh_metric_to_row(m) for m in mesh])
    if "rtt_ms" in hist.columns and hist["rtt_ms"].notna().any():
        st.subheader("Tunnel RTT Over Time (ms)")
        chart_df = hist[["time", "peer_id", "rtt_ms"]].dropna(subset=["rtt_ms"])
        if not chart_df.empty and "peer_id" in chart_df.columns and chart_df["peer_id"].nunique() > 1:
            pivot = chart_df.pivot_table(index="time", columns="peer_id", values="rtt_ms")
            st.line_chart(pivot)
        else:
            st.line_chart(chart_df.set_index("time")["rtt_ms"])

    # --- Diagnosis notes ---
    st.subheader("Diagnosis")
    seen_notes = False
    for m in mesh[:5]:
        rc = m.get("root_cause")
        if rc and rc != "healthy":
            st.markdown(
                f"- `{m.get('device_id')}` → **{root_cause_label(rc)}** "
                f"({fmt_time_ago(m.get('collected_at'))})"
            )
            seen_notes = True
    if not seen_notes:
        st.markdown("- All tunnels look healthy.")

    # --- Recent state-change events ---
    st.subheader("Recent Events")
    try:
        events = get_mesh_events(limit=10)
    except ApiUnavailable as exc:
        st.warning(str(exc))
        events = []
    if not events:
        st.caption("No mesh state-change events recorded yet.")
    event_icon = {"peer_down": "🔴", "peer_up": "🟢", "path_change": "🔀"}
    for ev in events:
        icon = event_icon.get(ev.get("kind"), "•")
        st.markdown(
            f"- {icon} `{ev.get('peer_id')}` — {ev.get('detail')} "
            f"({fmt_time_ago(ev.get('created_at'))})"
        )


def render_issues() -> None:
    st.header("Issues & Root Cause")
    metrics = _safe_load_metrics()
    if metrics is None:
        return
    if not metrics:
        st.info("No metrics yet.")
        return

    st.subheader("Recent Issues")
    rows = collect_recent_issues(metrics, limit=20)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.success("No active issues.")

    st.subheader("Root Cause Distribution")
    rc_counts: dict[str, int] = {}
    for m in metrics:
        rc = m.get("root_cause")
        if rc:
            rc_counts[rc] = rc_counts.get(rc, 0) + 1
    if rc_counts:
        df = pd.DataFrame(
            [{"root_cause": k, "label": root_cause_label(k), "count": v}
             for k, v in sorted(rc_counts.items(), key=lambda x: -x[1])]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No root cause information.")


def render_recommendations() -> None:
    st.header("Recommendations")
    metrics = _safe_load_metrics()
    if metrics is None:
        return
    if not metrics:
        st.info("No metrics yet.")
        return

    recs = collect_recent_recommendations(metrics, limit=15)
    if not recs:
        st.success("No active recommendations. Network looks healthy.")
        return

    for i, r in enumerate(recs, 1):
        st.markdown(f"**{i}.** {r}")


def render_raw_metrics() -> None:
    st.header("Raw Metrics")
    metrics = _safe_load_metrics()
    if metrics is None:
        return
    if not metrics:
        st.info("No metrics yet.")
        return

    rows = []
    for m in metrics:
        rows.append({
            "device_id": m.get("device_id"),
            "metric_type": m.get("metric_type"),
            "collected_at": fmt_timestamp(m.get("collected_at")),
            "quality": m.get("quality"),
            "quality_score": m.get("quality_score"),
            "root_cause": m.get("root_cause"),
            "issues": ", ".join(m.get("issues") or []),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("JSON Debug")
    st.json(metrics[:5])


def render_settings() -> None:
    st.header("⚙️ Settings")
    try:
        current = get_settings()
    except ApiUnavailable as exc:
        st.error(str(exc))
        return

    cols = st.columns(3)
    cols[0].metric("GET Auth", "on" if current.get("get_auth") else "off")
    cols[1].metric("Mesh Pubkey", "configured" if current.get("mesh_pubkey_set") else "missing")
    cols[2].metric("Backend", get_backend_url())

    st.subheader("Notifications (ntfy / webhook)")
    st.caption(
        "Mesh olaylarında (peer down/up, path değişimi) bildirim gönderilir. "
        "Örnek: https://ntfy.sh/benim-ag-kanalim — boş bırakmak kapatır."
    )
    new_url = st.text_input(
        "Notify URL",
        value=current.get("notify_url") or "",
        placeholder="https://ntfy.sh/my-topic",
    )
    token = st.text_input("API Token (POST için gerekli)", type="password",
                          value=os.getenv("HOMENETIQ_API_TOKEN", ""))
    if st.button("Save", type="primary"):
        try:
            update_settings({"notify_url": new_url.strip()}, token=token or None)
            st.success("Ayar kaydedildi ✅ (kalıcı: data/settings.json)")
            st.cache_data.clear()
        except ApiUnavailable as exc:
            st.error(f"Kaydedilemedi: {exc}")

    st.divider()
    st.subheader("Hızlı komutlar")
    st.code("./scripts/run-all.sh                      # tüm yığın (bu makine host)", language="bash")
    st.code("./scripts/join.sh <HOST_IP> <isim>       # ikinci cihaz katılımı", language="bash")
    st.code("make mesh-once                            # mesh sağlık örneği (tek tick)", language="bash")


def render_about() -> None:
    st.header("About / Setup")
    st.markdown(
        f"""
        **HomeNetIQ** is a self-hosted, local network intelligence platform.
        It measures network latency, Wi-Fi signal quality and likely root
        causes for problems.

        ### Supported roles
        - Backend host (Linux) + optional network probe
        - Linux Wi-Fi probe (`iw`)
        - macOS Wi-Fi probe (optional)
        - Your own router/AP (configure `targets` yourself)

        ### Backend connection
        - Backend URL: `HOMENETIQ_BACKEND_URL` (default `http://127.0.0.1:8080`)
        - API token: `HOMENETIQ_API_TOKEN` (**required** for dashboard reads; GET auth is on by default)
        - Currently connected to: `{get_backend_url()}`
        """
    )

    st.subheader("What this tool is NOT")
    st.markdown(
        """
        - ❌ Not a Wi-Fi hacking or attack tool.
        - ❌ Does not scan or attack neighboring networks.
        - ❌ Not an ISP speed-guarantee or SLA tool.
        - ❌ Not a replacement for a professional RF survey tool.
        - ❌ Not a cloud service — all data stays on your device.
        """
    )

    st.subheader("Privacy")
    st.markdown(
        """
        BSSID/MAC addresses are never sent in raw form. The default `redact`
        mode keeps only the last two octets. The optional `hash` mode uses
        SHA-256 with a user-supplied salt. There is **no fixed salt**.
        """
    )
