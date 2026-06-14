# HomeNetIQ v1 — Engineering Review Report

**Date:** 2026-06-14
**Scope:** Full repo review (code + config + services + tests)
**Method:** Static reading + `pytest` run + end-to-end smoke test with FastAPI `TestClient`
**Rule:** Existing functionality preserved. Only the minimal fix needed to run tests was applied.

---

## 1. Current Architecture Summary

HomeNetIQ is a self-hosted network intelligence system that runs on a
local network. There are three main components, and they all send
metrics to the same REST API.

### Components

| Component | Location | Responsibility |
|---|---|---|
| **Backend (FastAPI)** | `backend/app/` | Metric ingest, quality classification, root cause prediction, SQLite storage, REST API |
| **Kali Wi-Fi Agent** | `collectors/kali_wifi_agent.py` | `iw` for signal/bitrate, `ping` for gateway/AP/internet latency, builds payload and POSTs to backend |
| **Pi Network Probe** | `probes/pi_network_probe.py` | Gateway/AP/internet ping + DNS latency, builds payload and POSTs to backend |
| **Streamlit Dashboard** | `dashboard/streamlit_app.py` | Reads backend's `/api/v1/summary`, `/devices`, `/metrics/latest` and renders tables + line charts |
| **SQLite DB** | `backend/app/database.py` (`init_db`) | `devices` and `metrics` tables, indices |
| **systemd services** | `systemd/*.service` | 3 units: backend, Kali agent, Pi probe |
| **Optional ClickHouse** | `database/clickhouse_schema.sql` | Not used in v1; reference schema for later time-series analytics |

### Data flow

```
Kali agent  ─┐
             ├─► POST /api/v1/metrics ─► FastAPI ─► quality.classify_quality()
Pi probe    ─┘                              │      └► root_cause.classify_root_cause()
                                            ▼
                                  SQLite (devices, metrics)
                                            ▲
                                            │
                       Streamlit dashboard ─┘  (GET /api/v1/*)
```

### API surface (`backend/app/main.py`)

- `GET  /health`
- `POST /api/v1/metrics` (Bearer token required)
- `GET  /api/v1/metrics/latest?limit=50`
- `GET  /api/v1/devices`
- `GET  /api/v1/devices/{device_id}/latest?limit=50`
- `GET  /api/v1/summary?limit=200`
- `GET  /api/v1/anomalies?limit=50`

### Configuration

Backend env vars (`backend/app/settings.py`): `HOMENETIQ_DB_PATH`,
`HOMENETIQ_API_TOKEN`, `HOMENETIQ_REQUIRE_AUTH`,
`HOMENETIQ_STALE_AFTER_SECONDS`, `HOMENETIQ_OFFLINE_AFTER_SECONDS`.
Example values are in `config/backend.env.example`.

Agent/probe config (YAML): `config/kali_agent.yaml.example` and
`config/pi_probe.yaml.example`.

---

## 2. What Works (Verified)

- **Test suite green:** all 4 tests in `tests/test_quality.py` pass.
  ```
  tests/test_quality.py::test_good_wifi_metric       PASSED
  tests/test_quality.py::test_poor_signal_metric     PASSED
  tests/test_quality.py::test_root_cause_wifi_issue  PASSED
  tests/test_quality.py::test_dns_issue              PASSED
  ```
- **Backend import + route registration:** `from backend.app.main import app` succeeds; 8 API routes (`/health` + 7 `/api/v1/*`) are bound to FastAPI.
- **E2E smoke test successful:** with `TestClient`, `POST /api/v1/metrics` → 401 without bearer, 200 with token; payload `{"rssi":-80,"snr":10,"tx_rate_mbps":20,"band":"2ghz"}` returns: `quality="poor"`, `issues=["weak_signal","low_snr","low_tx_rate","using_2ghz_band"]`, `root_cause="wifi_signal_issue"`. `GET /devices` and `/summary` correctly read the same DB.
- **Auth layer works:** `require_token` is applied only to `POST /metrics`, correctly returns `401`.
- **Quality classification logic is consistent:** if any "severe" issue is present or 4+ issues accumulate → `poor`; otherwise `warning`; else `good`.
- **Root cause classification order is deterministic:** AP → gateway → DNS → packet loss → Wi-Fi → WAN/ISP → 2.4 GHz → healthy → unknown. No overlap.
- **DB schema is consistent:** `init_db()` creates two tables + three indices; upsert/insert/query functions match the schema.
- **systemd units are internally consistent:** each has `Restart=always`, `RestartSec=5`, `After=network-online.target`.
- **ClickHouse schema is intentionally optional:** both `docs/ARCHITECTURE.md` and the SQL file's header comment make this clear.

---

## 3. What Is Broken or Risky

### 3.1 High priority

1. **`backend/` was not a Python package → test import broken.**
   `tests/test_quality.py` does `from backend.app.quality import ...` but `backend/__init__.py` did not exist. Pytest failed with `ModuleNotFoundError`.
   **Minimal fix applied:** added `backend/__init__.py` (single-line docstring). No behavior change, just enables package import.

2. **`FastAPI.on_event("startup")` is deprecated since FastAPI 0.93+ and removed in 0.137.**
   `backend/app/main.py:24` calls `init_db()` via `on_event`. Pinned 0.115.6 still works (TestClient context manager fires it), but the next FastAPI bump will silently break table creation and produce "no such table: devices".
   **Suggestion:** migrate to `lifespan` async context manager.

3. **`docs/ARCHITECTURE.md` mentions `Root Cause Engine` as if it were separate; in code it's called inline in the request handler.** Small but misleading. Architecture note should be updated.

### 3.2 Medium priority

4. **`config/backend.env.example` points the DB at `/home/pi/homenetiq/data/homenetiq.sqlite3`, but `systemd/homenetiq-backend.service` uses `WorkingDirectory=/home/pi/homenetiq/backend`.** `HOMENETIQ_DB_PATH` comes from EnvironmentFile, so it's not a runtime bug, but the README "Quick Start" doesn't create the `data/` directory. `database.py:19` resolves it at runtime via `parent.mkdir(parents=True, exist_ok=True)`, which is good, but undocumented.

5. **README "Quick Start" Kali step has an implicit path:**
   `README.md:30` says:
   ```
   python collectors/kali_wifi_agent.py --config config/kali_agent.yaml --once
   ```
   This must be run from the repo root (since the agent file lives in `collectors/`). The README has no `cd <repo>` step. Same issue for Pi: `systemd/homenetiq-pi-probe.service:9` uses `WorkingDirectory=/home/pi/homenetiq`; the service works because of that, but it's not reflected in the README.

6. **`systemd/homenetiq-kali-agent.service` runner path / username is inconsistent.**
   - `User=firat`, `WorkingDirectory=/home/firat/homenetiq`, `.venv` path `/home/firat/homenetiq/.venv` — Kali/MacBook personal.
   - Backend unit `User=pi`, `WorkingDirectory=/home/pi/homenetiq/backend` — Pi.
   - This may be intentional, but the README doesn't say "Kali = firat user"; deployment is confusing.

7. **Kali agent invokes `iw` without `sudo` / capability configuration.** README and systemd unit have no sudo / capability note. Practically most modern laptops allow `iw dev` read, but `iw dev <iface> link` requires `CAP_NET_ADMIN` on many systems. systemd service will likely start but log errors on every tick. Documentation missing.

8. **Dashboard reads `HOMENETIQ_API_TOKEN` env var (`dashboard/streamlit_app.py:7`) and `HOMENETIQ_BACKEND_URL`.** The README doesn't tell the user to set these env vars when starting Streamlit. Just running `streamlit run ...` will fail (POSTs are not made, but GETs would 401 because the dashboard sends the default token and it won't match).

9. **No CORS middleware in the backend.** Not a problem while the dashboard calls the API server-side, but a browser-based UI would need it.

10. **Test coverage is very narrow.** Only `quality` and `root_cause` are tested. `database.py` (init/upsert/insert/list), `models.py` (validation), API endpoints, `parse_iw_link`, `ping_stats`, DNS computation are not tested.

### 3.3 Low priority / Nice-to-have

11. **Empty `HomeNetIQ.md` file** (0 bytes) in the repo root. README.md already exists; this file should be deleted or given a purpose (e.g. project log, release notes).

12. **`tests/` has no `__init__.py` and no `conftest.py`.** When you run `pytest` from the repo root, the `backend` package is not on PYTHONPATH, so import fails. Therefore tests must be run with `PYTHONPATH=. pytest`. Cleaner solution: define `pythonpath = .` in `pytest.ini` or `pyproject.toml`.

13. **`_metric_row_to_dict` does `json.loads` per row** — fine for small data volumes; should be considered if `latest_metrics(limit=1000)` becomes common. Not a concern for v1.

14. **Schema documentation is sparse.** `init_db()` does not explain in comments why `payload_json` and `issues_json` are kept as separate columns. A short comment would help readability.

15. **`scripts/run_backend_dev.sh` uses `cd` and `--reload`** (script does `cd "$(dirname "$0")/../backend"` — acceptable, just a note).

16. **`requirements.txt` pins `pydantic==2.10.4`.** Python 3.14 has no wheel for pydantic-core 2.10. Pi uses 3.11/3.12, so this is fine, but a note would help contributors.

17. **Default API token `"change-me-local-token"`.** Conscious choice for local network, but a real security issue if exposed to the internet. The README says "never expose to internet"; good.

18. **`run()` in `collectors/kali_wifi_agent.py:18` and `probes/pi_network_probe.py:18` does not raise `subprocess.CalledProcessError` but logs the error in the message — this has no effect because `ping_stats` swallows it with `try/except Exception`. However, when `iw dev` fails, `detect_wifi_interface` raises `RuntimeError`; the agent's main loop does not catch it, so the systemd service enters an infinite restart loop.

---

## 4. Prioritised fix list

| # | Level | Topic | Suggested action |
|---|---|---|---|
| 1 | **P0** | Test import broken (`backend/__init__.py` missing) | ✅ Done |
| 2 | **P0** | `on_event("startup")` deprecated | Migrate to `lifespan` async context manager |
| 3 | **P1** | README missing `cd <repo>` step for agent/probe commands | Add a directory note in the README |
| 4 | **P1** | `iw` root/cap requirement undocumented | Add a note in README + systemd unit; recommend `CAP_NET_ADMIN` |
| 5 | **P1** | Dashboard envs (BACKEND_URL, API_TOKEN) missing | Add `export ...` examples in the README |
| 6 | **P1** | systemd user names not reflected in README | Add a "Pi=pi, Kali=firat" note |
| 7 | **P1** | Kali agent main loop does not catch RuntimeError | Top-level try/except + log + short retry |
| 8 | **P2** | Test coverage only quality/root_cause | Add tests for `database`, `models`, `parse_iw_link`, `ping_stats` |
| 9 | **P2** | `tests/` package not arranged + no `pytest.ini` / `pyproject.toml` | Set `pythonpath = .` |
| 10 | **P2** | Architecture diagram mentions "Root Cause Engine" | Update `docs/ARCHITECTURE.md` |
| 11 | **P3** | Empty `HomeNetIQ.md` | Delete or document its purpose |
| 12 | **P3** | No CORS middleware | Add when a browser UI is added |
| 13 | **P3** | pydantic 2.10.4 doesn't compile on Python 3.14 | Document that Pi uses 3.11/3.12 |
| 14 | **P3** | `data/` directory in `backend.env.example` is created at runtime | Add `mkdir -p ~/homenetiq/data` to setup steps |

---

## 5. Recommended v1.0 Completion Checklist

Done: ✔  Missing: ☐

### Infrastructure & setup
- ☐ `pyproject.toml` or `pytest.ini` with `pythonpath = .`
- ☐ `backend/` is a package; CI step to verify
- ☐ `lifespan` with `init_db` (replacing deprecated `on_event`)
- ☐ README: full setup guide (Pi + Kali + Dashboard)
- ☐ Install script: `scripts/install_pi.sh`, `scripts/install_kali.sh`

### Configuration
- ☐ `.env.example` shown in README
- ☐ Token generation suggestion (`openssl rand -hex 32`) in README
- ☐ systemd user/WorkingDirectory in README

### Security
- ☐ Token only applied to POST (GETs open) — intentional; document
- ☐ Warning that `change-me-local-token` must be changed in production
- ☐ CORS policy when needed

### Observability
- ☐ Backend JSON log (uvicorn access log is enough; request_id would help)
- ☐ Agent/probe log: one summary line per tick + full traceback on error
- ☐ systemd `StandardOutput=journal` verified

### Tests
- ☐ Quality and root cause tests (✔ existing)
- ☐ DB CRUD tests (init, upsert, insert, latest, summary)
- ☐ Models validation tests (e.g. `device_id` min_length=2)
- ☐ Agent parser tests (`parse_iw_link`, `freq_to_band`, `freq_to_channel`, `ping_stats`)
- ☐ API integration test (POST→GET with TestClient)
- ☐ CI: pytest on GitHub Actions or GitLab CI (matrix: py3.11 + py3.12)

### Documentation
- ☐ Update `docs/ARCHITECTURE.md` to reflect real modules
- ☐ `docs/SETUP.md` — setup from scratch (Pi OS image, venv, systemd enable)
- ☐ `docs/USAGE.md` — dashboard usage, when an alert matters
- ☐ `docs/SECURITY.md` — why and how local-only
- ☐ Remove empty `HomeNetIQ.md`

### Data & analytics
- ☐ ClickHouse may remain optional; in addition to the schema, consider a minimal "export to CSV" CLI

---

## 6. Exact run commands

All commands are meant to be run from the **repo root**
(`HomeNetIQ_v1/`).

### 6.1 Backend

Development mode (auto-reload):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../config/backend.env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Or with the helper script:

```bash
bash scripts/run_backend_dev.sh
```

Production (Pi) — with `systemd/homenetiq-backend.service`:

```bash
sudo cp systemd/homenetiq-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now homenetiq-backend
sudo systemctl status homenetiq-backend
```

### 6.2 Pi Network Probe

```bash
cd <repo_root>
cp config/pi_probe.yaml.example config/pi_probe.yaml
# Edit the `targets` section for your network

python3 probes/pi_network_probe.py --config config/pi_probe.yaml --once
```

As a service:

```bash
sudo cp systemd/homenetiq-pi-probe.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now homenetiq-pi-probe
```

### 6.3 Kali Wi-Fi Agent

> Note: `iw` commands may require root or `CAP_NET_ADMIN` on some systems. When running via systemd, either run the service as root or add `CapabilityBoundingSet=CAP_NET_ADMIN` and `AmbientCapabilities=CAP_NET_ADMIN`.

```bash
cd <repo_root>
cp config/kali_agent.yaml.example config/kali_agent.yaml
# Edit `targets` and the backend URL

python3 collectors/kali_wifi_agent.py --config config/kali_agent.yaml --once
```

As a service:

```bash
sudo cp systemd/homenetiq-kali-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now homenetiq-kali-agent
```

### 6.4 Dashboard

```bash
export HOMENETIQ_BACKEND_URL="http://127.0.0.1:8080"
export HOMENETIQ_API_TOKEN="change-me-local-token"
streamlit run dashboard/streamlit_app.py
```

The dashboard opens at <http://localhost:8501>. If the backend is on
a different host, set `HOMENETIQ_BACKEND_URL` accordingly.

### 6.5 Tests

```bash
# Virtualenv (recommended)
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# Run the suite
PYTHONPATH=. pytest tests/ -v
```

Or with `pyproject.toml` / `pytest.ini` setting `pythonpath = .`:

```bash
pytest tests/ -v
```

Expected output:

```
tests/test_quality.py::test_good_wifi_metric       PASSED
tests/test_quality.py::test_poor_signal_metric     PASSED
tests/test_quality.py::test_root_cause_wifi_issue  PASSED
tests/test_quality.py::test_dns_issue              PASSED
============================== 4 passed in 0.10s ===============================
```

### 6.6 Health check

After the backend is up:

```bash
curl http://127.0.0.1:8080/health
# {"status":"ok","service":"homenetiq-backend"}

curl http://127.0.0.1:8080/api/v1/devices
# []  (empty when there are no metrics yet)

curl -X POST http://127.0.0.1:8080/api/v1/metrics \
  -H "Authorization: Bearer change-me-local-token" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id":"manual-test",
    "device_type":"wifi_probe",
    "metric_type":"wifi",
    "payload":{"rssi":-65,"snr":25,"tx_rate_mbps":120}
  }'
```

---

## 7. The only change made in this review

- **`backend/__init__.py`** was added (single-line docstring). This is
  required for `tests/test_quality.py`'s `from backend.app...` import
  to work. It does not change behavior, only enables packaging.

No source file, configuration, systemd unit, requirements, or test
was modified or deleted.
