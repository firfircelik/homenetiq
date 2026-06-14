# Agent Contract Changelog

**Date:** 2026-06-14
**Scope:** All agents/collectors, payload standard, privacy behavior, shared infrastructure.

## Standardized payload fields

All agents use the same canonical field names:

### Top-level (required + optional)
- `device_id`, `device_type`, `metric_type`, `payload` — required
- `device_name`, `os`, `agent_version`, `collected_at` — optional

### Wi-Fi payload (canonical)
`ssid`, `bssid_redacted` or `bssid_hash` (no raw BSSID), `frequency_mhz`,
`band` (canonical: `2.4GHz` / `5GHz` / `6GHz`), `channel`,
`channel_width_mhz`, `rssi`, `noise`, `snr`, `tx_rate_mbps`,
`rx_rate_mbps`, `mcs_index`, `phy_mode`, `security`.

### Network payload (canonical)
`gateway_ip`, `ap_ip`, `internet_ip`, `gateway_latency_ms`,
`ap_latency_ms`, `internet_latency_ms`, `dns_latency_ms`,
`packet_loss_percent`, `jitter_ms`.

### Alias support (backwards compatibility)
The backend accepts these aliases; agents use the canonical names:
- `signal` → `rssi`
- `packet_loss` → `packet_loss_percent`
- `2GHz`/`2G`/`2.4` → `2.4GHz` (normalized by the quality engine)

## Updated / added agents

| Agent | File | Status |
|---|---|---|
| Kali/Linux Wi-Fi | `collectors/kali_wifi_agent.py` | Refactor — canonical payload + privacy + shared utils |
| macOS Wi-Fi | `collectors/macos_wifi_agent.py` | New — `system_profiler` parser + canonical payload |
| Pi/Linux Network Probe | `probes/pi_network_probe.py` | Refactor — canonical payload + shared utils |

## New shared infrastructure (`agents/`)

- `agents/version.py` — `AGENT_PROTOCOL_VERSION = "1.0.0"`
- `agents/config_loader.py` — YAML config reader + `AgentConfig` dataclass + validation
- `agents/http_client.py` — `post_metric` + `post_metric_with_retry`
- `agents/ping.py` — Cross-platform `ping_stats` (parser)
- `agents/privacy.py` — `bssid_redact`, `bssid_hash`, `apply_privacy`
- `agents/time_utils.py` — `now_iso` (UTC ISO-8601)

Code duplication is significantly reduced: `run`, `ping_stats`, `time.sleep`,
`datetime.now` etc. now live in a single place.

## Privacy behavior

- BSSID/MAC **never** sent in raw form.
- Default `redact` mode: last 2 octets (`...:44:55`).
- `hash` mode: SHA-256 first 12 hex, optional user salt.
- **No fixed salt:** without a salt, the same BSSID produces the same hash; with a salt, the same salt + same BSSID produces the same hash.
- Only the user's own network's telemetry is collected. Neighbor-network lists, MAC vendor info, and any data outside the user's own device/network are **not** collected or sent.

## agent_version

- Every agent adds `agent_version` to the payload (default `"1.0.0"`).
- Defined in a single place: `agents/version.py`.
- The backend uses this for logging/analytics; version mismatch does not cause an error.

## Tests

| Test file | Test count | Scope |
|---|---|---|
| `tests/test_kali_parser.py` | 15 (rewritten) | Kali parser, macOS parser, Pi payload, privacy, ping |
| `tests/test_agent_utils.py` | 13 (new) | HTTP, retry/backoff, config loader, headers |
| `tests/test_quality.py` | 4 | Existing quality tests (unchanged) |
| `tests/test_quality_engine.py` | 21 | Quality engine (unchanged) |
| `tests/test_api.py` | 5 | API integration (unchanged) |
| `tests/test_database.py` | 5 | DB CRUD (unchanged) |

**Total: 40 → 63 (23 new tests). All green.**

## Run

```bash
pytest tests/ -v
# 63 passed
```

## Known limitations

- **macOS BSSID:** `system_profiler SPAirPortDataType` does not expose
  the raw BSSID. `wdutil info` or `airport -I` could be added; this was
  not done (we don't want to depend on offensive/scanning tools). For
  now, the macOS agent does not send BSSID; it works with
  SSID/channel/signal/noise only.
- **`iw` CAP_NET_ADMIN:** The Kali agent calls `iw`; some systems
  require root or `CAP_NET_ADMIN`. Documented in the README.
- **Retry backoff is linear:** not exponential. Sufficient for LAN
  scenarios; v2 may add exponential for WAN scenarios.
- **Agent auto-update is not supported:** agents run at a static
  version; updating is the operator's responsibility.

## Future improvements

1. **macOS BSSID via `airport -I`** (not offensive, just current connection info).
2. **Trend-aware agent:** add the average of the last 5 measurements to the payload.
3. **Push-based delivery:** backend can add `long-poll` or WebSocket.
4. **Multi-band reporting:** the Kali agent can measure 2.4 + 5 GHz simultaneously.
5. **Browser probe:** simple extension for `metric_type="browser"`.
