# HomeNetIQ v1 Architecture

## Purpose

Measure Wi-Fi and internet quality on a home network, classify problems,
and produce human-readable reports.

## Components

| Component | Location | Responsibility |
|---|---|---|
| Backend (FastAPI) | `backend/app/` | HTTP API + SQLite storage. `init_db()` runs at app startup via the `lifespan` context manager. |
| Quality module | `backend/app/quality.py` | `classify_quality()` — rule-based good/warning/poor decision + issue list + 0-100 score + explanations. |
| Root Cause module | `backend/app/root_cause.py` | `classify_root_cause()` — labels the likely problem location from the issue list. |
| Recommendations | `backend/app/recommendations.py` | `recommend()` — human-readable, actionable recommendation list. |
| Kali Wi-Fi agent | `collectors/kali_wifi_agent.py` | `iw` + `ping` Wi-Fi and network metrics. |
| Pi network probe | `probes/pi_network_probe.py` | Gateway/AP/internet ping + DNS latency. |
| macOS Wi-Fi agent | `collectors/macos_wifi_agent.py` | `system_profiler` parser for macOS. |
| Dashboard | `dashboard/streamlit_app.py` | Streamlit UI that calls backend GET endpoints. |
| SQLite DB | `backend/app/database.py` | `devices` + `metrics` tables, indices. |
| systemd units | `systemd/*.service` | 3 services: backend, Pi probe, Kali agent. |
| Optional ClickHouse | `database/clickhouse_schema.sql` | Not used at runtime in v1; reference schema for later. |

## Data flow

```
[Kali agent]  ─┐
[macOS agent] ─┼─► POST /api/v1/metrics ─► FastAPI endpoint
[Pi probe]    ─┘                              │
                                             ▼
                              quality.classify_quality()
                              root_cause.classify_root_cause()
                              recommendations.recommend()
                                             │
                                             ▼
                              SQLite (devices, metrics)
                                             ▲
                                             │
                       [Streamlit dashboard] │  GET /api/v1/*
                       (HOMENETIQ_BACKEND_URL)
```

> **Note:** Quality and Root Cause are not separate services. They are
> pure functions called inline by the `POST /api/v1/metrics` endpoint
> for each request. This keeps the rules explainable, deterministic,
> and easy to test.

## API surface

GET `/health` is unauthenticated. All other GET data endpoints require a
Bearer token when `HOMENETIQ_REQUIRE_GET_AUTH` is true (the default).
`POST /api/v1/metrics` always requires the token. `/api/v1/mesh/pubkey`
needs the API token or `HOMENETIQ_ENROLL_TOKEN`.

| Method | Path | Auth |
|---|---|---|
| GET  | `/health` | - |
| POST | `/api/v1/metrics` | Bearer token |
| GET  | `/api/v1/metrics/latest` | Bearer (default) |
| GET  | `/api/v1/devices` | Bearer (default) |
| GET  | `/api/v1/devices/{device_id}/latest` | Bearer (default) |
| GET  | `/api/v1/summary` | Bearer (default) |
| GET  | `/api/v1/anomalies` | Bearer (default) |
| GET  | `/api/v1/mesh/pubkey` | Bearer or enroll token |

Do not expose the backend to the public internet. For LAN access, bind
uvicorn to `127.0.0.1` and put Caddy in front (`contrib/Caddyfile`).

> 🇹🇷 Türkçe: [docs/tr/ARCHITECTURE.tr.md](tr/ARCHITECTURE.tr.md)
