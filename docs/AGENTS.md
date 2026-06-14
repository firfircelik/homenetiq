# HomeNetIQ Agents

This document describes all agents/collectors in v1 and how to develop
new ones.

## Purpose

HomeNetIQ collects telemetry from the **user's own devices** on the
**user's own network**. These agents:

- Do not scan, attack, or deauth neighboring networks.
- Do not sniff, probe, or perform password testing.
- Only ping the allowed targets (gateway, AP, internet, DNS).

## Agent list

| Agent | Location | OS | Typical use |
|---|---|---|---|
| Kali/Linux Wi-Fi agent | `collectors/kali_wifi_agent.py` | Linux (Kali, Raspbian, etc.) | `iw`-based Wi-Fi telemetry |
| macOS Wi-Fi agent | `collectors/macos_wifi_agent.py` | macOS | `system_profiler`-based Wi-Fi telemetry |
| Pi/Linux Network Probe | `probes/pi_network_probe.py` | Linux (Pi, etc.) | Network latency and DNS |

## Shared infrastructure

All agents share the `agents/` package:

- `agents/config_loader.py` — YAML config reader + validation
- `agents/http_client.py` — POST + retry/backoff
- `agents/ping.py` — Cross-platform `ping` parser
- `agents/privacy.py` — BSSID redact/hash
- `agents/time_utils.py` — ISO-8601 UTC timestamp
- `agents/version.py` — `AGENT_PROTOCOL_VERSION`

## Payload generation

Each agent produces a canonical payload by `metric_type`. See
[`docs/METRIC_CONTRACT.md`](METRIC_CONTRACT.md).

## Privacy behavior

BSSID/MAC addresses are **never** sent in raw form. Two modes:

- `redact` (default): only the last two octets are kept (`...:44:55`).
  Consistent across reconnects, but unidentifiable.
- `hash`: SHA-256 first 12 hex chars. The user's `privacy.salt` in
  config is optional; with a salt, the same salt + same BSSID produces
  the same hash (allowing joinability across agents). There is **no
  fixed salt**.

The only network identifier stored is the SSID (the user's own
network name). MAC addresses, vendor info, and neighbor-network lists
are **not stored or sent**.

## Developing a new agent

To add a new agent:

1. Use the shared `agents/` modules (config, http, ping, privacy, time).
2. Produce a canonical payload (`docs/METRIC_CONTRACT.md`).
3. Add `agent_version` to the payload
   (`agents.version.AGENT_PROTOCOL_VERSION`).
4. Write **pure functions** like `payload_iw_link`,
   `parse_system_profiler`, or `build_network_payload`; these are
   what you test.
5. Wrap the `collect_and_send` and `main` functions with a
   `try/except` for error handling; in `--once` mode, return `exit 1`
   on error.
6. For the new agent, add:
   - `collectors/<name>.py` or `probes/<name>.py`
   - `config/<name>.yaml.example`
   - `tests/test_<name>.py`

## Run examples

```bash
# Kali/Linux
python3 collectors/kali_wifi_agent.py --config config/kali_agent.yaml --once

# macOS
python3 collectors/macos_wifi_agent.py --config config/macos_agent.yaml --once

# Pi probe
python3 probes/pi_network_probe.py --config config/pi_probe.yaml --once
```

## Tests

- `tests/test_kali_parser.py` — Kali parser + macOS parser + Pi payload + privacy
- `tests/test_agent_utils.py` — HTTP, retry/backoff, config loader

Run with `pytest tests/ -v`.

> 🇹🇷 Türkçe: [docs/tr/AGENTS.tr.md](tr/AGENTS.tr.md)
