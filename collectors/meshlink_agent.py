"""meshlink VPN health agent.

Runs the meshlink project's machine-readable status snapshot
(`agent status --json`) and maps it into canonical HomeNetIQ metrics: one
metric per mesh peer, so the quality engine can score not only Wi-Fi/LAN/WAN
but also the encrypted overlay itself (direct vs relay path, tunnel RTT,
rekeys, session age).

meshlink is a separate Go project (https://github.com/firfircelik/network-project).
This agent only *reads* its status; it never configures or attacks anything.

Requires meshlink >= commit with `status --json` support.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Doğrudan `python collectors/meshlink_agent.py` ile çalıştırıldığında repo
# kökü sys.path'te olmaz; agents paketini bulabilmesi için ekliyoruz.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents import (
    AgentConfig,
    load_agent_config,
    now_iso,
    post_metric,
)

# --- Saf fonksiyonlar (test edilebilir) ---

# Pin the meshlink status JSON major. Unknown major is a hard error;
# extra fields on a known major are ignored. Missing schema_version is
# treated as 1 (pre-contract meshlink binaries).
STATUS_SCHEMA_MAJOR = 1


def schema_major(snapshot: dict[str, Any]) -> int:
    """Return the major version of a status snapshot."""
    raw = snapshot.get("schema_version")
    if raw is None:
        return 1
    if isinstance(raw, bool):
        raise RuntimeError(f"invalid schema_version: {raw!r}")
    if isinstance(raw, int):
        return raw
    text = str(raw).strip()
    head = text.split(".", 1)[0]
    try:
        return int(head)
    except ValueError as exc:
        raise RuntimeError(f"invalid schema_version: {raw!r}") from exc


def check_schema_version(snapshot: dict[str, Any]) -> None:
    """Reject an unknown major; extras on a known major are ignored later."""
    major = schema_major(snapshot)
    if major != STATUS_SCHEMA_MAJOR:
        raise RuntimeError(
            f"unsupported meshlink status schema_version major={major} "
            f"(want {STATUS_SCHEMA_MAJOR})"
        )


def parse_status_json(text: str) -> dict[str, Any]:
    """Parse `meshlink agent status --json` stdout into a dict.

    Tolerant of leading noise: finds the first '{' so stray output before the
    JSON document does not break ingestion.
    """
    start = text.find("{")
    if start == -1:
        raise RuntimeError("meshlink status output contains no JSON object")
    return json.loads(text[start:])


def build_argvs(extra: dict[str, Any]) -> list[str]:
    """Build the `meshlink agent status` argv from config's `meshlink:` section.

    When `probe_peer` is set, the status command pings that peer first from
    the same agent instance, so the snapshot reports a real path/RTT instead
    of a not-yet-established session.
    """
    m = extra.get("meshlink") or {}
    required = ("bin", "name", "keyfile", "coordinator", "coord_pubkey")
    missing = [k for k in required if not m.get(k)]
    if missing:
        raise RuntimeError(f"config 'meshlink' section missing field(s): {', '.join(missing)}")

    argv = [
        str(m["bin"]), "status", "--json",
        "--name", str(m["name"]),
        "--keyfile", str(m["keyfile"]),
        "--coordinator", str(m["coordinator"]),
        "--coord-pubkey", str(m["coord_pubkey"]),
    ]
    if m.get("data"):
        argv += ["--data", str(m["data"])]
    if m.get("stun"):
        argv += ["--stun", str(m["stun"])]
    if m.get("relay"):
        argv += ["--relay", str(m["relay"])]
    if m.get("probe_peer"):
        argv += ["--probe-peer", str(m["probe_peer"])]
    if m.get("preauth"):
        argv += ["--preauth", str(m["preauth"])]
    return argv


def payloads_from_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Map a meshlink status snapshot to one canonical payload per peer.

    When no peers are known yet, a single peer-less payload is emitted with
    `established=None` so the quality engine scores only registry visibility
    instead of falsely reporting a downed peer.
    """
    check_schema_version(snapshot)
    registry = snapshot.get("registry") or {}
    base = {
        "local_name": snapshot.get("name"),
        "registry_count": registry.get("count"),
        "coordinator_up_s": registry.get("up_s"),
    }
    if snapshot.get("registry_error"):
        base["registry_error"] = str(snapshot["registry_error"])

    peers = snapshot.get("peers") or []
    if not peers:
        out = dict(base)
        out["peer_id"] = ""
        out["established"] = None
        out["path"] = "none"
        return [out]

    out: list[dict[str, Any]] = []
    for p in peers:
        payload = dict(base)
        payload["peer_id"] = p.get("id")
        payload["established"] = bool(p.get("established"))
        payload["path"] = str(p.get("path") or "none").lower()
        rtt = p.get("rtt_ms")
        payload["rtt_ms"] = float(rtt) if rtt is not None else None
        payload["rekeys"] = int(p.get("rekeys") or 0)
        payload["session_age_s"] = float(p.get("age_s") or 0)
        payload["bytes_sent"] = int(p.get("bytes_sent") or 0)
        payload["bytes_recv"] = int(p.get("bytes_recv") or 0)
        # Endpoint is the peer's own advertised address on the user's own
        # network; apply_privacy-style redaction is unnecessary but we keep
        # the raw value out when empty.
        if p.get("endpoint"):
            payload["endpoint"] = str(p["endpoint"])
        out.append(payload)
    return out


def build_metric(cfg: AgentConfig, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "device_id": cfg.device_id,
        "device_name": cfg.device_name,
        "device_type": cfg.device_type,
        "os": cfg.os,
        "agent_version": cfg.agent_version,
        "metric_type": "mesh",
        "collected_at": now_iso(),
        "payload": payload,
    }


def collect_and_send(cfg: AgentConfig) -> list[dict[str, Any]]:
    """Run meshlink status, map to metrics, POST each one. Returns responses."""
    argv = build_argvs(cfg.extra)
    result = subprocess.run(
        argv, capture_output=True, text=True, timeout=cfg.timeout_seconds,
    )
    if result.returncode != 0:
        raise RuntimeError(f"meshlink status failed: {result.stderr.strip()[:300]}")

    snapshot = parse_status_json(result.stdout)
    responses = []
    for payload in payloads_from_snapshot(snapshot):
        metric = build_metric(cfg, payload)
        responses.append(
            post_metric(cfg.backend_url, metric, cfg.backend_headers(), timeout=cfg.timeout_seconds)
        )
    return responses


# --- Main loop ---

def main() -> int:
    parser = argparse.ArgumentParser(description="HomeNetIQ meshlink VPN health agent")
    parser.add_argument("--config", required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    try:
        cfg = load_agent_config(args.config)
    except Exception as exc:
        print(f"meshlink agent config error: {exc}", file=sys.stderr, flush=True)
        return 1

    while True:
        try:
            responses = collect_and_send(cfg)
            print(json.dumps({"ok": True, "metrics_sent": len(responses)}, ensure_ascii=False), flush=True)
        except KeyboardInterrupt:
            print("meshlink agent: stopped by user.", file=sys.stderr, flush=True)
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
