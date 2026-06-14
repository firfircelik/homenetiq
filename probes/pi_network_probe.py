"""Raspberry Pi (and other Linux) network probe.

Only pings gateway/AP/internet on the user's own network and measures DNS
latency. Does NOT scan or attack neighboring networks.

System commands: `ping` (no root required; DNS via `socket.getaddrinfo`).
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from typing import Any

from agents import (
    AgentConfig,
    load_agent_config,
    now_iso,
    ping_stats,
    post_metric,
)


# --- DNS latency (pure, easy to test on the agent side) ---

def dns_latency_ms(domain: str) -> float | None:
    """Total time for DNS resolution of a domain in milliseconds. None on failure."""
    start = time.perf_counter()
    try:
        socket.getaddrinfo(domain, 80)
    except socket.gaierror:
        return None
    return round((time.perf_counter() - start) * 1000, 3)


# --- Network payload generation (pure) ---

def build_network_payload(targets: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
    """Build measurements for gateway/AP/internet/DNS with canonical fields.

    The `targets` dict accepts these keys:
      - gateway_ip, ap_ip, internet_ip (required)
      - dns_domains (optional list)
    """

    gateway = ping_stats(targets["gateway_ip"], timeout=timeout)
    ap = ping_stats(targets["ap_ip"], timeout=timeout)
    internet = ping_stats(targets["internet_ip"], timeout=timeout)

    dns_values: list[float] = []
    for d in targets.get("dns_domains", []) or []:
        v = dns_latency_ms(d)
        if v is not None:
            dns_values.append(v)
    avg_dns = round(sum(dns_values) / len(dns_values), 3) if dns_values else None

    return {
        "gateway_ip": targets["gateway_ip"],
        "ap_ip": targets["ap_ip"],
        "internet_ip": targets["internet_ip"],
        "gateway_latency_ms": gateway["avg_ms"],
        "ap_latency_ms": ap["avg_ms"],
        "internet_latency_ms": internet["avg_ms"],
        "jitter_ms": internet["jitter_ms"],
        "packet_loss_percent": internet["packet_loss_percent"],
        "dns_latency_ms": avg_dns,
    }


def build_metric(cfg: AgentConfig, extra_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "device_id": cfg.device_id,
        "device_name": cfg.device_name,
        "device_type": cfg.device_type,
        "os": cfg.os,
        "agent_version": cfg.agent_version,
        "metric_type": "network",
        "collected_at": now_iso(),
        "payload": extra_payload,
    }


def collect_and_send(cfg: AgentConfig, targets: dict[str, Any], *, once: bool) -> dict[str, Any]:
    payload = build_network_payload(targets, timeout=cfg.timeout_seconds)
    metric = build_metric(cfg, payload)
    return post_metric(cfg.backend_url, metric, cfg.backend_headers(), timeout=cfg.timeout_seconds)


# --- Main loop ---

def main() -> int:
    parser = argparse.ArgumentParser(description="HomeNetIQ Pi/Linux network probe")
    parser.add_argument("--config", required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    try:
        cfg = load_agent_config(args.config)
    except Exception as exc:
        print(f"Pi probe config error: {exc}", file=sys.stderr, flush=True)
        return 1

    targets = cfg.extra.get("targets", {})
    missing = [k for k in ("gateway_ip", "ap_ip", "internet_ip") if k not in targets]
    if missing:
        print(f"Config'te eksik target: {', '.join(missing)}", file=sys.stderr, flush=True)
        return 1

    while True:
        try:
            result = collect_and_send(cfg, targets, once=args.once)
            print(json.dumps({"ok": True, "backend_response": result}, ensure_ascii=False), flush=True)
        except KeyboardInterrupt:
            print("Pi probe: stopped by user.", file=sys.stderr, flush=True)
            return 0
        except Exception as exc:
            print(
                json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False),
                file=sys.stderr, flush=True,
            )
            if args.once:
                return 1
            time.sleep(cfg.retry_delay_seconds)
            continue

        if args.once:
            return 0
        time.sleep(cfg.interval_seconds)


if __name__ == "__main__":
    sys.exit(main())
