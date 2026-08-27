"""HomeNetIQ Streamlit dashboard — thin router.

All UI lives in `dashboard/pages.py`. This file is just configuration,
the sidebar router, and bootstrap.
"""

from __future__ import annotations

import streamlit as st

from dashboard import pages


PAGES = [
    ("Overview", "📊", pages.render_overview),
    ("Devices", "🖥️", pages.render_devices),
    ("Wi-Fi Metrics", "📶", pages.render_wifi_metrics),
    ("Network Metrics", "🌐", pages.render_network_metrics),
    ("Mesh VPN", "🔐", pages.render_mesh),
    ("Issues & Root Cause", "🧩", pages.render_issues),
    ("Recommendations", "💡", pages.render_recommendations),
    ("Raw Metrics", "🔍", pages.render_raw_metrics),
    ("Settings", "⚙️", pages.render_settings),
    ("About / Setup", "ℹ️", pages.render_about),
]


def main() -> None:
    st.set_page_config(page_title="HomeNetIQ", layout="wide", initial_sidebar_state="expanded")
    st.title("HomeNetIQ Dashboard")
    st.caption("Home network and Wi-Fi telemetry — local & self-hosted")

    with st.sidebar:
        st.header("Pages")
        labels = [f"{icon}  {name}" for name, icon, _ in PAGES]
        choice = st.radio("", labels, label_visibility="collapsed")
        st.divider()
        st.caption("local telemetry — any Linux/macOS host (Pi optional)")

    for name, _icon, render in PAGES:
        if choice.endswith(name):
            render()
            return
    st.warning("No page selected.")


if __name__ == "__main__":
    main()
