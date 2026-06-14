# Release Notes — v1.0.0

**Date:** 2026-06-14
**Version:** v1.0.0
**Status:** Release Candidate (RC)

## Summary

HomeNetIQ is now a self-hosted network intelligence platform that can
be deployed on a Raspberry Pi + Kali MacBook Air + optional macOS
Wi-Fi probe, with all data staying on the user's own network.

## What's new

### Backend
- FastAPI + lifespan async context manager (replaces deprecated `on_event`)
- Bearer token auth (POST endpoints); GET endpoints open (LAN)
- SQLite + automatic migration (new columns via ALTER TABLE)
- 7 REST endpoints: `/health`, `/api/v1/metrics`, `/api/v1/metrics/latest`, `/api/v1/devices`, `/api/v1/devices/{id}/latest`, `/api/v1/summary`, `/api/v1/anomalies`

### Quality Engine
- 0-100 `quality_score` (per payload)
- 14 issue codes (weak_signal, low_snr, packet_loss, slow_dns, using_2ghz_band, ...)
- 14 root cause labels (healthy, wifi_signal_issue, wan_or_isp_issue, dns_issue, ...)
- Threshold dataclass for single-place threshold management
- Cumulative severe-issue penalty
- Alias support: `signal`↔`rssi`, `packet_loss`↔`packet_loss_percent`

### Recommendations
- Human-readable English recommendations
- Root-cause + per-issue tips
- Deduped, prioritised order

### Agents
- `agents/` shared package: config, http, ping, privacy, time, version
- `AGENT_PROTOCOL_VERSION = "1.0.0"`
- Canonical Wi-Fi payload (ssid, bssid_redacted/hash, band, channel, rssi, snr, ...)
- Canonical Network payload (gateway_latency_ms, internet_latency_ms, packet_loss_percent, jitter_ms, ...)
- **Privacy:** BSSID/MAC never sent in raw form. `redact` (default) or `hash` + user salt
- Kali/Linux Wi-Fi agent (refactor): `iw dev <iface> link` parser
- macOS Wi-Fi agent (new): `system_profiler SPAirPortDataType` parser
- Pi/Linux network probe (refactor): ping + DNS latency
- Error handling: try/except + retry_delay + exit 1 (--once)

### Dashboard
- 8 pages: Overview, Devices, Wi-Fi Metrics, Network Metrics, Issues & Root Cause, Recommendations, Raw Metrics, About/Setup
- 10s cache, clear error when backend is down
- Empty-data safe (no metrics yet → informative message)
- `HOMENETIQ_BACKEND_URL` and `HOMENETIQ_API_TOKEN` env vars

### Packaging & Release
- `Makefile`: `make install`, `make test`, `make run-backend`, `make run-dashboard`, `make kali-once`, `make macos-once`, `make pi-probe-once`, `make clean`
- 4 helper scripts: `run_backend_dev.sh`, `run_dashboard.sh`, `run_kali_once.sh`, `run_pi_probe_once.sh`
- `.github/workflows/ci.yml` (Python 3.11 + 3.12 matrix)
- `.gitignore` (config, .env, sqlite, venv, cache)
- systemd unit templates (user/path edit notes)

### Docs
- `docs/ARCHITECTURE.md`
- `docs/QUALITY_ENGINE.md`
- `docs/AGENTS.md`
- `docs/METRIC_CONTRACT.md`
- `docs/DASHBOARD.md`
- `docs/SETUP_RASPBERRY_PI.md`
- `docs/SETUP_KALI_AGENT.md`
- `docs/SETUP_MACOS_AGENT.md`
- `docs/TROUBLESHOOTING.md`
- `docs/tr/*.tr.md` (Turkish mirrors of all user-facing docs)
- `README.tr.md` (Turkish README)
- `PROJECT_STATUS.md`
- `RELEASE_NOTES_v1.0.0.md` (this file)

## Tests

```
$ pytest tests/ -v
====================== 91 passed, 1757 warnings in 7.21s ======================
```

| Test file | Test | Scope |
|---|---|---|
| `tests/test_api.py` | 5 | API integration (lifespan, auth, ingest, devices, latest) |
| `tests/test_database.py` | 5 | DB CRUD (init, upsert, insert, filter, stale/offline) |
| `tests/test_kali_parser.py` | 15 | Kali + macOS parser + Pi payload + privacy + ping |
| `tests/test_agent_utils.py` | 13 | HTTP client, retry/backoff, config loader, headers |
| `tests/test_dashboard.py` | 28 | api_client, formatters, filter, import |
| `tests/test_quality.py` | 4 | quality + root cause (legacy) |
| `tests/test_quality_engine.py` | 21 | quality scoring, recommendations, helpers |
| **Total** | **91** | |

## Known limitations

- **Python 3.14 + pydantic 2.10:** no wheel, source compile needed. Python 3.11/3.12 recommended (Pi OS default).
- **Streamlit 1.41 + Python 3.14:** starlette import error. Pi (3.11/3.12) is fine.
- **macOS BSSID:** `system_profiler SPAirPortDataType` does not expose raw BSSID. v2 may add `airport -I` integration (not an offensive tool).
- **DNS latency:** only `socket.getaddrinfo`; no DNSSEC, resolver chain, EDNS.
- **Single device = single view:** engine evaluates a single payload in isolation; cross-device correlation / trend analysis is v2.
- **ClickHouse:** `database/clickhouse_schema.sql` is **not** used in v1; reference only.
- **OpenWrt / router management:** v1 doesn't include it; read-only.
- **Browser probe:** `metric_type="browser"` is defined but no agent.
- **ML-based anomaly:** v1 is rule-based. v2 may add.
- **LICENSE = MIT:** new for this release.

## Breaking changes

- `pytest tests/ -v` no longer needs `PYTHONPATH=.` (`pytest.ini` sets `pythonpath = .`).
- `agent_version` is a new payload field (optional; backend accepts it, doesn't require it).
- `classify_quality` now returns `(quality, issues, score, explanations)` 4-tuple.

## Upgrading

From v0 (if any): `init_db()` performs automatic ALTER TABLE migration.
Existing DBs are not broken.

## Contributors

- Lead developer: Firat Celik
- AI pair-programming: MiniMax M3 (opencode)

## License

Distributed under the **MIT License**. See [LICENSE](../LICENSE) for the
full text.

```
MIT License — Copyright (c) 2026 Firat Celik
```

## Acknowledgements

Thanks to the Raspberry Pi, Kali Linux, and Streamlit communities.
