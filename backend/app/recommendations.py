"""Human-readable recommendations engine.

Each recommendation is short, actionable, and written in plain language so
that a non-technical user can act on it.
"""

from __future__ import annotations


_ISSUE_TIPS: dict[str, str] = {
    "weak_signal": (
        "The device may be too far from the access point. Move the probe "
        "closer to the AP and re-test, or reposition the AP."
    ),
    "low_snr": (
        "Signal-to-noise ratio is low. There may be local interference "
        "(microwave, Bluetooth) or channel conflict; try changing the AP channel."
    ),
    "low_tx_rate": (
        "TX rate is low. The link to the AP may be weak; try a closer AP "
        "or one that supports 5 GHz."
    ),
    "low_rx_rate": (
        "RX rate is low. Signal quality may be insufficient; check the "
        "Wi-Fi adapter or AP antenna."
    ),
    "low_local_throughput": (
        "Local network throughput is low. Check AP load or compare with a "
        "wired connection."
    ),
    "using_2ghz_band": (
        "Device is on the 2.4 GHz band. If possible, switch to a 5 GHz "
        "capable AP or use a different channel."
    ),
    "packet_loss": (
        "Packet loss detected. The connection may be unstable; check cables "
        "or AP placement."
    ),
    "high_jitter": (
        "Jitter is high. Real-time applications (video, gaming) may be "
        "affected; check network load."
    ),
    "high_gateway_latency": (
        "Gateway latency is high. Try restarting the modem or check LAN cables."
    ),
    "high_ap_latency": (
        "Access point latency is high. Try moving the AP or power-cycling it."
    ),
    "ap_unreachable": (
        "Cannot ping the access point. Check the AP power, cable, and IP assignment."
    ),
    "high_internet_latency": (
        "Internet latency is high. The issue may be on the ISP side; "
        "test at different times or contact your ISP."
    ),
    "slow_dns": (
        "DNS response time is high. Try a different DNS resolver "
        "(e.g. 1.1.1.1, 8.8.8.8) or check the modem's DNS proxy settings."
    ),
    "internet_unreachable": (
        "Cannot reach the internet target. Check ISP connection or modem status."
    ),
    "backend_or_probe_stale": (
        "No metrics received for a long time. Verify the probe or backend "
        "service is running."
    ),
    "mesh_peer_down": (
        "The mesh peer is registered but the encrypted tunnel is down. "
        "Check that the peer's meshlink agent is running and both sides "
        "can reach the coordinator."
    ),
    "mesh_no_path": (
        "No direct or relay path could be established. Check UDP connectivity "
        "and that the relay address is reachable from both peers."
    ),
    "mesh_relay_fallback": (
        "Traffic is flowing through the relay because no direct path was "
        "possible. This still works but adds latency; check NAT/firewall "
        "settings if you want the faster direct path."
    ),
    "high_mesh_latency": (
        "Tunnel round-trip time is high. If the path is relay, this is "
        "expected; otherwise check the load on both endpoints."
    ),
    "mesh_registry_empty": (
        "The coordinator registry is empty. Verify the agent registered "
        "successfully and the coordinator is running."
    ),
}


_ROOT_CAUSE_TIPS: dict[str, str] = {
    "healthy": "Network looks normal. Routine monitoring can continue.",
    "wifi_signal_issue": (
        "The issue is Wi-Fi signal strength. Optimize AP placement or channel."
    ),
    "wifi_congestion_issue": (
        "Wi-Fi noise or channel conflict may be the cause. Change the AP "
        "channel or use 5 GHz."
    ),
    "local_ap_issue": (
        "The issue is likely on the access point side. Restart the AP or "
        "reposition it."
    ),
    "gateway_or_lan_issue": (
        "There may be an issue in the local network (modem/cable). Check "
        "the modem and cables."
    ),
    "wan_or_isp_issue": (
        "The local network looks fine; latency may be on the WAN/ISP side. "
        "Contact your ISP or test at a different time."
    ),
    "dns_issue": (
        "The issue is on the DNS side. Try a different resolver or check "
        "DNS settings on the modem."
    ),
    "single_device_issue": (
        "Signal quality is good but packet loss is present; the issue may "
        "be on this device only. Reboot the device or check its Wi-Fi adapter."
    ),
    "probe_or_backend_issue": (
        "The issue may be on the probe or backend side. Verify the "
        "homenetiq-backend and probe services are running."
    ),
    "mesh_peer_offline": (
        "The remote mesh peer is not answering. Check that its meshlink "
        "agent is running and both sides can reach the coordinator."
    ),
    "nat_traversal_failed": (
        "Neither a direct nor a relay path could be established between "
        "the peers. Verify the relay is reachable and UDP is not blocked."
    ),
    "nat_traversal_limited": (
        "The peers are connected through the relay because direct hole "
        "punching failed (typical for symmetric NATs). The tunnel works, "
        "but with extra latency."
    ),
    "mesh_path_degraded": (
        "The tunnel path has high latency. Compare direct vs relay in the "
        "mesh status; relay paths are naturally slower."
    ),
    "coordinator_registration_issue": (
        "No peers are visible in the coordinator registry. Check that the "
        "agents registered successfully and share the coordinator's pinned "
        "public key."
    ),
    "unknown_issue": (
        "Could not classify the issue. As more metrics are collected, a "
        "more precise root cause will appear."
    ),
}


def recommend(issues: list[str], root_cause: str) -> list[str]:
    """Produce a list of recommendations based on issues and root cause.

    The returned list is deduped and ordered: first the root-cause tip,
    then the per-issue tips.
    """

    seen: set[str] = set()
    out: list[str] = []

    tip = _ROOT_CAUSE_TIPS.get(root_cause)
    if tip and tip not in seen:
        out.append(tip)
        seen.add(tip)

    for code in issues:
        tip = _ISSUE_TIPS.get(code)
        if tip and tip not in seen:
            out.append(tip)
            seen.add(tip)

    if not out:
        out.append("Not enough data yet. A few more metrics will produce a recommendation.")
    return out
