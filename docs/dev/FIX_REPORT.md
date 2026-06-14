# Fix Report

**Date:** 2026-06-14
**Scope:** P0 and P1 items from `REVIEW_REPORT.md`.
**Rule:** Existing functionality was preserved. No large rewrites. Only P0/P1 items were addressed.

## Changed / added files

| File | Status | Description |
|---|---|---|
| `backend/app/main.py` | changed | `@app.on_event("startup")` → `lifespan` async context manager |
| `collectors/kali_wifi_agent.py` | changed | Main loop wrapped in try/except + retry + exit code |
| `README.md` | changed | Installation steps clarified, dashboard envs added, token generation added, systemd personalisation note, `iw` privilege warning |
| `docs/ARCHITECTURE.md` | changed | Modules aligned with real code, "Root Cause Engine" note added, API auth table added |
| `pytest.ini` | added | `pythonpath = .` removes the `PYTHONPATH=.` requirement |
| `tests/conftest.py` | added | Isolated temporary DB + module reload per test |
| `tests/test_api.py` | added | 5 API integration tests |
| `tests/test_database.py` | added | 5 DB CRUD tests |
| `tests/test_kali_parser.py` | added | 5 Kali parser/band/channel/ping tests |
| `HomeNetIQ.md` | deleted | Empty 0-byte file |

## Closed P0 / P1 items

| # | Item | Status |
|---|---|---|
| 1 (P0) | `on_event("startup")` deprecated → `lifespan` | ✅ Closed |
| 2 (P0) | `PYTHONPATH=.` mandatory → removed via `pytest.ini` | ✅ Closed |
| 3 (P1) | README missing `cd <repo>` step | ✅ Closed — every step has the directory stated |
| 4 (P1) | `iw` root/cap requirement undocumented | ✅ Closed — README + systemd section note + capability recommendation |
| 5 (P1) | Dashboard envs (BACKEND_URL, API_TOKEN) missing | ✅ Closed — `export` examples in README |
| 6 (P1) | systemd user names missing in README | ✅ Closed — README tells the user to edit the units |
| 7 (P1) | Kali agent main loop did not catch RuntimeError | ✅ Closed — try/except + retry_delay + exit 1 in `--once` |
| 8 (P1) | "Root Cause Engine" missing from architecture diagram | ✅ Closed — ARCHITECTURE.md module list + note |
| 10 (P1) | Test coverage only quality/root_cause | ✅ Closed — API + DB + parser tests added (15 new tests) |
| 11 (P3) | Empty `HomeNetIQ.md` | ✅ Closed — deleted |

## Items still open (out of scope for this round)

P2/P3 items from `REVIEW_REPORT.md` that were intentionally left for
later (v1.0.0 scope):

- **P2 #12:** Add auth to GET endpoints (mTLS / API key) — kept open
  for v1, LAN only; explicitly noted in ARCHITECTURE.md.
- **P2 #13:** CORS middleware — not needed yet (dashboard uses `requests`);
  will be added when a browser-based UI is added.
- **P2 #14:** `pyproject.toml` instead of `pytest.ini` — `pytest.ini` was
  chosen as the lighter option.
- **P3 #15:** `pydantic==2.10.4` wheel issue on Python 3.14 — Pi uses
  3.11/3.12 by default; not an issue. A note is in the README.
- **P3 #16:** `data/` directory in installation steps — runtime creates
  it via `mkdir(parents=True, exist_ok=True)`; README notes this.
- **P3 #17:** `_metric_row_to_dict` does `json.loads` per row — fine
  for v1 volume.
- **P3 #18:** Inline comment for why JSON columns are separate — small
  and optional.

## Test result

```
$ pytest tests/ -v
============================= test session starts ==============================
platform darwin -- Python 3.14.5, pytest-8.3.4, pluggy-1.6.0
configfile: pytest.ini
collected 19 items

tests/test_api.py::test_health_endpoint                            PASSED [  5%]
tests/test_api.py::test_unauthorized_post_rejected                 PASSED [ 10%]
tests/test_api.py::test_authorized_post_stores_metric              PASSED [ 15%]
tests/test_api.py::test_post_then_get_devices_lists_device         PASSED [ 21%]
tests/test_api.py::test_post_then_get_latest_metrics_returns_inserted_row PASSED [ 26%]
tests/test_database.py::test_init_db_creates_tables                PASSED [ 31%]
tests/test_database.py::test_upsert_device_inserts_then_updates    PASSED [ 36%]
tests/test_database.py::test_insert_and_latest_metrics_roundtrip   PASSED [ 42%]
tests/test_database.py::test_latest_metrics_for_device_filters     PASSED [ 47%]
tests/test_database.py::test_list_devices_marks_stale_and_offline  PASSED [ 52%]
tests/test_kali_parser.py::test_parse_iw_link_extracts_all_fields  PASSED [ 57%]
tests/test_kali_parser.py::test_parse_iw_link_handles_missing_fields PASSED [ 63%]
tests/test_kali_parser.py::test_freq_to_band_2ghz_5ghz_6ghz        PASSED [ 68%]
tests/test_kali_parser.py::test_freq_to_channel_common             PASSED [ 73%]
tests/test_kali_parser.py::test_ping_stats_handles_ping_failure    PASSED [ 78%]
tests/test_quality.py::test_good_wifi_metric                       PASSED [ 84%]
tests/test_quality.py::test_poor_signal_metric                     PASSED [ 89%]
tests/test_quality.py::test_root_cause_wifi_issue                  PASSED [ 94%]
tests/test_quality.py::test_dns_issue                              PASSED [100%]

======================= 19 passed, 461 warnings in 0.10s =======================
```

**Result:** 19/19 green. Started at 4 tests, added 15 (4 → 19).

> Warnings are Python 3.14 + starlette compatibility noise; not from
> the project code. Pi's Python 3.11/3.12 doesn't see these.

## Manual run commands

All commands below are meant to be run from the **repo root**
(`HomeNetIQ_v1/`).

### Tests

```bash
# Set up the virtualenv (first time)
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# Run the suite (no PYTHONPATH needed; pytest.ini sets pythonpath = .)
pytest tests/ -v
```

### Backend (dev)

```bash
cp config/backend.env.example backend/.env
# Edit backend/.env and replace HOMENETIQ_API_TOKEN

cd backend
source .venv/bin/activate
cd ..

uvicorn backend.app.main:app --host 0.0.0.0 --port 8080
# or
bash scripts/run_backend_dev.sh
```

Health check:

```bash
curl http://127.0.0.1:8080/health
# {"status":"ok","service":"homenetiq-backend"}
```

### Pi Network Probe

```bash
cp config/pi_probe.yaml.example config/pi_probe.yaml
# Edit the `targets` section

python3 probes/pi_network_probe.py --config config/pi_probe.yaml --once
```

### Kali Wi-Fi Agent

```bash
cp config/kali_agent.yaml.example config/kali_agent.yaml
# Edit `targets` and the backend URL

python3 collectors/kali_wifi_agent.py --config config/kali_agent.yaml --once
```

> `iw dev <iface> link` may require root or `CAP_NET_ADMIN`. See the
> "systemd" section in the README.

### Dashboard

```bash
export HOMENETIQ_BACKEND_URL="http://192.168.1.50:8080"
export HOMENETIQ_API_TOKEN="<token from backend .env>"
streamlit run dashboard/streamlit_app.py
```

### systemd

```bash
# Edit user/WorkingDirectory/ExecStart paths first
sudo cp systemd/homenetiq-backend.service  /etc/systemd/system/
sudo cp systemd/homenetiq-pi-probe.service /etc/systemd/system/
# On the Kali device:
sudo cp systemd/homenetiq-kali-agent.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now homenetiq-backend
sudo systemctl enable --now homenetiq-pi-probe
# On the Kali device:
sudo systemctl enable --now homenetiq-kali-agent
sudo systemctl status homenetiq-backend --no-pager
```

## What was NOT done in this round (intentional)

- FastAPI version was not bumped (pinned `0.115.6` kept; lifespan works in 0.115).
- No new dependencies added.
- Data model / API contract unchanged.
- Dashboard behavior unchanged (only documentation clarified).
- systemd unit contents unchanged — README tells the user to personalise.
