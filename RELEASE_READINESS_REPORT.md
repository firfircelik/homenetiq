# HomeNetIQ v1.0.0 — Release Readiness Report

**Date:** 2026-06-14
**Version:** v1.0.0
**Status:** ✅ Release Candidate — ready to push to GitHub

## Final test result

```
$ pytest tests/ -v
====================== 91 passed, 1757 warnings in 7.55s ======================
```

91/91 green. Test distribution:

| Test file | Tests | Scope |
|---|---|---|
| `tests/test_api.py` | 5 | API integration (lifespan, auth, ingest, devices, latest) |
| `tests/test_database.py` | 5 | DB CRUD (init, upsert, insert, filter, stale/offline) |
| `tests/test_kali_parser.py` | 15 | Kali + macOS parser + Pi payload + privacy + ping |
| `tests/test_agent_utils.py` | 13 | HTTP client, retry/backoff, config loader, headers |
| `tests/test_dashboard.py` | 28 | api_client, formatters, filter, import |
| `tests/test_quality.py` | 4 | quality + root cause (legacy) |
| `tests/test_quality_engine.py` | 21 | quality scoring, recommendations, helpers |
| **Total** | **91** | |

## Changed / added files (this round)

| File | Status | Description |
|---|---|---|
| `Makefile` | new | `make test/install/run-backend/run-dashboard/kali-once/macos-once/pi-probe-once/clean` |
| `scripts/run_backend_dev.sh` | refactor | From repo root: `uvicorn backend.app.main:app` |
| `scripts/run_dashboard.sh` | new | Streamlit launcher |
| `scripts/run_kali_once.sh` | new | One-tick Kali runner + config check |
| `scripts/run_pi_probe_once.sh` | new | One-tick Pi probe + config check |
| `systemd/homenetiq-backend.service` | fix | `app.main:app` → `backend.app.main:app`; template note; `.venv` path fixed |
| `systemd/homenetiq-pi-probe.service` | fix | `.venv` path fixed; template note |
| `systemd/homenetiq-kali-agent.service` | update | `CAP_NET_ADMIN` comments; template note |
| `backend/requirements.txt` | comment | Python 3.11/3.12 recommendation note |
| `.gitignore` | new | config, .env, sqlite, venv, cache, secrets |
| `.github/workflows/ci.yml` | new | Python 3.11 + 3.12 matrix, pytest |
| `PROJECT_STATUS.md` | new | What's in / what's not in v1 |
| `RELEASE_NOTES_v1.0.0.md` | new | Release notes |
| `docs/SETUP_RASPBERRY_PI.md` | new | Pi setup |
| `docs/SETUP_KALI_AGENT.md` | new | Kali setup |
| `docs/SETUP_MACOS_AGENT.md` | new | macOS setup |
| `docs/TROUBLESHOOTING.md` | new | Common errors |
| `RELEASE_READINESS_REPORT.md` | new | This file |
| `README.md` | no change needed | Previous round already covers all commands |

## Closed release blockers

| Blocker | Fix |
|---|---|
| Backend won't start (lifespan deprecated) | ✅ FastAPI lifespan async context manager |
| Test import broken (`backend/__init__.py` missing) | ✅ Added |
| `pytest tests/` failed (PYTHONPATH needed) | ✅ `pytest.ini` with `pythonpath = .` |
| Dashboard envs undocumented | ✅ README + docs/DASHBOARD.md |
| BSSID/MAC privacy | ✅ `redact`/`hash` agent utils |
| Old import path in systemd units | ✅ `backend.app.main:app` + WorkingDirectory fixed |
| Wrong `.venv` path in backend unit | ✅ Fixed |
| Kali service `iw` capability note missing | ✅ Added via commented lines |
| Config user/path mismatch | ✅ Template notes ("edit before use") |
| Python 3.14 compatibility | ✅ Documented (3.11/3.12 recommended) |
| `run_backend_dev.sh` old command | ✅ Updated to repo root + new uvicorn target |
| Missing scripts | ✅ run_dashboard, run_kali_once, run_pi_probe_once |
| No CI | ✅ GitHub Actions added |
| Honesty (don't claim features that don't exist) | ✅ "Not in v1" section in PROJECT_STATUS |

## Known limitations (honest) — still relevant

These are intentionally out of v1; v2 will revisit:

- **ML-based anomaly detection:** rule-based v1 is sufficient and explainable.
- **Multi-tenant auth:** single user, single network. Production-grade identity is v2.
- **Trend analysis / push-based delivery:** v1 shows the latest snapshot only. WebSocket or per-device push in v2.
- **OpenWrt / router management:** v1 is read-only. v2 may add router config writes.
- **ClickHouse is optional:** v1 uses SQLite. ClickHouse schema is reference only.
- **macOS BSSID:** v1 doesn't include it (no offensive tool dependency). v2: `airport -I`.
- **Browser probe:** `metric_type="browser"` is defined but no agent.
- **Python 3.14 + pydantic 2.10 wheel:** Python 3.14 + pydantic 2.10.4 has a compile error. README recommends 3.11/3.12.

## Real device deployment order

```
┌─────────────────┐
│ Mac mini (dev)  │  code written here, 91/91 tests passed
└────────┬────────┘
         │ git push
         ▼
┌─────────────────┐
│   GitHub repo   │  tag: v1.0.0
└────────┬────────┘
         │ git clone (on each device)
         ├──────────────────┬──────────────────┐
         ▼                  ▼                  ▼
  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │ Raspberry Pi │   │ Kali MB Air  │   │ Mac mini     │
  │ (backend +   │   │ (Wi-Fi agent)│   │ (optional    │
  │  pi probe +  │   │              │   │  macOS Wi-Fi │
  │  dashboard)  │   │              │   │  agent)      │
  └──────────────┘   └──────────────┘   └──────────────┘
```

**Order:**

1. **Mac mini (development)** — code lives here. `make test` passed.
2. **Push to GitHub** — `git tag v1.0.0 && git push origin v1.0.0`
3. **Raspberry Pi:**
   - `docs/SETUP_RASPBERRY_PI.md` steps
   - Backend + Pi probe + Dashboard on the same Pi
   - systemd enable
4. **Kali MacBook Air:**
   - `docs/SETUP_KALI_AGENT.md`
   - `make kali-once` to test
   - systemd enable (with CAP_NET_ADMIN)
5. **(Optional) Mac mini Wi-Fi agent:**
   - `docs/SETUP_MACOS_AGENT.md`
   - launchd or manual

## Manual smoke test (no agents required)

```bash
# 1. From repo root, with venv active
cd /home/pi/homenetiq
source .venv/bin/activate

# 2. Tests
make test                 # 91 passed

# 3. Start backend (separate terminal)
HOMENETIQ_API_TOKEN=test-tok bash scripts/run_backend_dev.sh

# 4. Health (new terminal)
curl http://127.0.0.1:8080/health
# {"status":"ok","service":"homenetiq-backend"}

# 5. Manual metric POST
curl -X POST http://127.0.0.1:8080/api/v1/metrics \
  -H "Authorization: Bearer test-tok" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id":"smoke-1",
    "device_type":"network_probe",
    "metric_type":"network",
    "payload":{"internet_latency_ms":42,"packet_loss_percent":0}
  }'

# 6. List devices
curl http://127.0.0.1:8080/api/v1/devices
# [{"device_id":"smoke-1","status":"active",...}]

# 7. Pi probe --once
make pi-probe-once
# {"ok":true,"backend_response":{"metric_id":...,"quality":"good",...}}

# 8. Dashboard
bash scripts/run_dashboard.sh
# http://localhost:8501
# Overview: Last Sample "X seconds ago"
# Devices: smoke-1, raspberry-pi should appear
# Wi-Fi Metrics: nothing yet (only the Pi probe ran)
# Network Metrics: latency graphs from smoke-1 should appear
```

## Git tag suggestion

```bash
git add -A
git commit -m "v1.0.0 — initial release"
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

## Previous reports

- `docs/dev/REVIEW_REPORT.md` — initial engineering review
- `docs/dev/FIX_REPORT.md` — P0/P1 fixes
- `docs/dev/QUALITY_ENGINE_CHANGELOG.md` — quality engine improvements
- `docs/dev/AGENT_CONTRACT_CHANGELOG.md` — agent contract
- `docs/dev/DASHBOARD_CHANGELOG.md` — dashboard improvements
- `RELEASE_READINESS_REPORT.md` — this file
