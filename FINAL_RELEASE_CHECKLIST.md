# FINAL_RELEASE_CHECKLIST — HomeNetIQ v1.0.0

**Date:** 2026-06-14
**Version:** v1.0.0
**Status:** ✅ Release Candidate

This file is the final readiness check for the v1.0.0 release. When
all items are green, the release is shippable.

## Test result

```
$ pytest tests/ -v
====================== 91 passed, 1757 warnings in 7.63s ======================
```

- 91/91 green
- 7 test files: `test_api`, `test_database`, `test_kali_parser`, `test_agent_utils`, `test_dashboard`, `test_quality`, `test_quality_engine`
- Existing 91 tests still pass (this release polish round made zero test changes)

`make test` gives the same result:

```
$ make test
====================== 91 passed, 1757 warnings in 7.08s ======================
```

Syntax check (every Python file parses):

```
$ python -m compileall -q backend collectors probes agents dashboard
# exit=0, 25 files
```

## CI status

- ✅ `.github/workflows/ci.yml` exists
- ✅ Python 3.11 + 3.12 matrix
- ✅ Every push and PR runs `pytest tests/ -v`

The first GitHub Actions run triggers automatically after the first push.

## LICENSE

- ✅ `LICENSE` file present
- ✅ **MIT License**
- ✅ Copyright: `Copyright (c) 2026 Firat Celik`
- ✅ README "License" section links to it

## README

- ✅ Project name: **HomeNetIQ v1.0.0**
- ✅ Badges: status, Python version, test count, license
- ✅ Architecture: Pi / Kali / macOS / AP roles clear
- ✅ Setup steps aligned with `Makefile` and `scripts/`
- ✅ `make install` + `make test` recommended
- ✅ Privacy section
- ✅ "What this tool is NOT" list
- ✅ "Not a Wi-Fi hacking tool" note preserved
- ✅ License section
- ✅ All docs links (SETUP_*, TROUBLESHOOTING, PROJECT_STATUS, RELEASE_NOTES, RELEASE_READINESS, FINAL_RELEASE_CHECKLIST, DOCS_LANGUAGE_CHANGELOG)

## Release notes

- ✅ `RELEASE_NOTES_v1.0.0.md` exists
- ✅ Sections: Summary, Backend, Quality Engine, Recommendations, Agents, Dashboard, Packaging & Release, Docs, Tests (table), Known limitations, Breaking changes, Upgrading, Contributors, License, Acknowledgements
- ✅ Test table 91/91
- ✅ 10+ known limitations explicitly listed
- ✅ LICENSE reference

## PROJECT_STATUS

- ✅ `PROJECT_STATUS.md` exists
- ✅ "In v1" and "Not in v1" separate lists
- ✅ **v2 candidates** separate section (backlog): trend analysis, ML, browser probe, OpenWrt, ClickHouse export, macOS BSSID, multi-tenant auth, mobile app, i18n, exponential backoff, mutation test, CORS, Wi-Fi 6E reporting, log query
- ✅ Test summary present
- ✅ Release blocker table present

## Git tag commands

```bash
# Add everything
git add -A
git commit -m "v1.0.0 — initial release

- FastAPI backend + SQLite + quality engine
- 3 agents: Kali Wi-Fi, macOS Wi-Fi, Pi network probe
- Streamlit dashboard (8 pages)
- 91/91 test
- MIT License
"

# Tag
git tag -a v1.0.0 -m "HomeNetIQ v1.0.0 — initial release"
git push origin main
git push origin v1.0.0
```

GitHub release view:

```
Releases → v1.0.0
- Title: HomeNetIQ v1.0.0
- Description: (content of RELEASE_NOTES_v1.0.0.md)
- This is a pre-release: no
```

## GitHub push commands (first time)

```bash
# If no remote yet
git remote add origin git@github.com:firatcelik/homenetiq.git

# If branch is main
git branch -M main
git push -u origin main
git push origin v1.0.0
```

## Real device deployment order

```
Mac mini (dev) ✅
   ↓ git push
GitHub repo (tag: v1.0.0)
   ↓ git clone
   ├──► Raspberry Pi   (backend + pi probe + dashboard)
   ├──► Kali MB Air    (Wi-Fi agent)
   └──► Mac mini       (optional macOS Wi-Fi agent)
```

Steps:

1. **Mac mini (development)** — `pytest tests/ -v` ✅ 91 passed (here)
2. **Push to GitHub** — `git push origin main && git push origin v1.0.0`
3. **Raspberry Pi** — `docs/SETUP_RASPBERRY_PI.md`:
   ```bash
   git clone https://github.com/<user>/HomeNetIQ.git /home/pi/homenetiq
   cd /home/pi/homenetiq
   make install
   cp config/backend.env.example backend/.env
   # Edit .env and replace HOMENETIQ_API_TOKEN
   make test                    # 91 passed
   make run-backend            # manual test
   # Edit systemd unit paths, then:
   sudo cp systemd/homenetiq-backend.service  /etc/systemd/system/
   sudo cp systemd/homenetiq-pi-probe.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now homenetiq-backend
   sudo systemctl enable --now homenetiq-pi-probe
   ```
4. **Kali MacBook Air** — `docs/SETUP_KALI_AGENT.md`:
   ```bash
   git clone https://github.com/<user>/HomeNetIQ.git ~/homenetiq
   cd ~/homenetiq
   make install
   cp config/kali_agent.yaml.example config/kali_agent.yaml
   # Edit targets and backend URL
   make kali-once               # one-tick test
   # Edit unit, enable CAP_NET_ADMIN, then:
   sudo cp systemd/homenetiq-kali-agent.service /etc/systemd/system/
   sudo systemctl enable --now homenetiq-kali-agent
   ```
5. **(Optional) Mac mini Wi-Fi agent** — `docs/SETUP_MACOS_AGENT.md`:
   ```bash
   make macos-once
   # launchd plist (not in repo; write your own)
   ```

## Manual smoke test (after all devices are ready)

```bash
# Backend on the Pi
make run-backend
# → http://0.0.0.0:8080

# Separate terminal on the Pi
curl http://127.0.0.1:8080/health

# On the Pi (or any other device)
make run-dashboard
# → http://localhost:8501

# Pi probe
make pi-probe-once
# → {"ok": true, "backend_response": {...}}

# On the Kali
make kali-once
# → {"ok": true, "backend_response": {...}}

# In the dashboard:
# - Overview: Last Sample should be fresh
# - Devices: pi + kali should be present
# - Wi-Fi Metrics: RSSI/SNR charts from Kali
# - Network Metrics: latency charts from Pi
# - Recommendations: action items
```

## Final file inventory

```
HomeNetIQ/
├── LICENSE                              ← MIT
├── README.md                            ← English
├── README.tr.md                         ← Turkish
├── Makefile                             ← 8 targets
├── pytest.ini                           ← pythonpath = .
├── .gitignore                           ← present
├── PROJECT_STATUS.md                    ← v2 candidates
├── RELEASE_NOTES_v1.0.0.md              ← sections
├── RELEASE_READINESS_REPORT.md          ← present
├── docs/dev/FIX_REPORT.md                        ← P0/P1 fixes
├── docs/dev/REVIEW_REPORT.md                     ← engineering review
├── docs/dev/QUALITY_ENGINE_CHANGELOG.md          ← present
├── docs/dev/AGENT_CONTRACT_CHANGELOG.md          ← present
├── docs/dev/DASHBOARD_CHANGELOG.md               ← present
├── DOCS_LANGUAGE_CHANGELOG.md           ← present
├── FINAL_RELEASE_CHECKLIST.md           ← this file
├── agents/                              ← 7 modules
│   ├── __init__.py
│   ├── config_loader.py
│   ├── http_client.py
│   ├── ping.py
│   ├── privacy.py
│   ├── time_utils.py
│   └── version.py
├── backend/
│   ├── __init__.py
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── database.py
│       ├── main.py
│       ├── models.py
│       ├── quality.py
│       ├── recommendations.py
│       ├── root_cause.py
│       ├── settings.py
│       └── thresholds.py
├── collectors/
│   ├── kali_wifi_agent.py
│   └── macos_wifi_agent.py
├── probes/
│   └── pi_network_probe.py
├── dashboard/
│   ├── __init__.py
│   ├── api_client.py
│   ├── formatters.py
│   ├── pages.py
│   └── streamlit_app.py
├── config/
│   ├── backend.env.example
│   ├── kali_agent.yaml.example
│   ├── macos_agent.yaml.example
│   └── pi_probe.yaml.example
├── database/
│   └── clickhouse_schema.sql            ← optional, not used in v1
├── docs/                                ← English
│   ├── AGENTS.md
│   ├── ARCHITECTURE.md
│   ├── DASHBOARD.md
│   ├── METRIC_CONTRACT.md
│   ├── QUALITY_ENGINE.md
│   ├── SETUP_KALI_AGENT.md
│   ├── SETUP_MACOS_AGENT.md
│   ├── SETUP_RASPBERRY_PI.md
│   ├── TROUBLESHOOTING.md
│   ├── images/
│   │   └── README.md
│   └── tr/                              ← Turkish mirrors
│       ├── AGENTS.tr.md
│       ├── ARCHITECTURE.tr.md
│       ├── DASHBOARD.tr.md
│       ├── METRIC_CONTRACT.tr.md
│       ├── QUALITY_ENGINE.tr.md
│       ├── SETUP_KALI_AGENT.tr.md
│       ├── SETUP_MACOS_AGENT.md
│       ├── SETUP_RASPBERRY_PI.tr.md
│       └── TROUBLESHOOTING.tr.md
├── scripts/
│   ├── run_backend_dev.sh
│   ├── run_dashboard.sh
│   ├── run_kali_once.sh
│   └── run_pi_probe_once.sh
├── systemd/
│   ├── homenetiq-backend.service
│   ├── homenetiq-kali-agent.service
│   └── homenetiq-pi-probe.service
├── tests/                               ← 91 tests
│   ├── conftest.py
│   ├── test_agent_utils.py
│   ├── test_api.py
│   ├── test_dashboard.py
│   ├── test_database.py
│   ├── test_kali_parser.py
│   ├── test_quality.py
│   └── test_quality_engine.py
└── .github/
    └── workflows/
        └── ci.yml
```

## Final sign-off

- ✅ All tests pass
- ✅ CI configured
- ✅ LICENSE present (MIT)
- ✅ README + Release Notes + Project Status ready
- ✅ Git tag commands ready
- ✅ Installation order + smoke test documented
- ✅ English primary, Turkish mirrored under docs/tr/

**v1.0.0 is ready to ship.**
