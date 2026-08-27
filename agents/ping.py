"""Cross-platform ping statistics.

`ping` output is consistent on Linux and macOS, so a single parser works
on both. On failure, avg/min/max/jitter are None and packet_loss_percent
is 100 (representing "target unreachable").

Goal: only ping allowed targets (gateway, AP, internet, DNS). No scanning
or attacking of other networks.
"""

from __future__ import annotations

import re
import subprocess
from typing import Optional


def _build_ping_cmd(target: str, count: int) -> list[str]:
    return ["ping", "-c", str(count), target]


def ping_stats(target: str, count: int = 5, timeout: int = 15) -> dict[str, Optional[float]]:
    """Ping a target N times and return min/avg/max/jitter/loss.

    All latency values are in milliseconds; packet_loss_percent is 0-100.
    On failure, avg/min/max/jitter are None and packet_loss_percent is 100.
    """

    if not str(target or "").strip():
        return _unreachable()

    try:
        result = subprocess.run(
            _build_ping_cmd(target, count),
            capture_output=True, text=True, timeout=timeout,
        )
        output = result.stdout
    except subprocess.TimeoutExpired:
        return _unreachable()
    except Exception:
        return _unreachable()

    loss_match = re.search(r"([\d.]+)%\s+packet loss", output)
    rtt_match = re.search(
        r"rtt min/avg/max/(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", output
    )
    return {
        "avg_ms": float(rtt_match.group(2)) if rtt_match else None,
        "min_ms": float(rtt_match.group(1)) if rtt_match else None,
        "max_ms": float(rtt_match.group(3)) if rtt_match else None,
        "jitter_ms": float(rtt_match.group(4)) if rtt_match else None,
        "packet_loss_percent": float(loss_match.group(1)) if loss_match else None,
    }


def _unreachable() -> dict[str, Optional[float]]:
    return {
        "avg_ms": None, "min_ms": None, "max_ms": None,
        "jitter_ms": None, "packet_loss_percent": 100.0,
    }
