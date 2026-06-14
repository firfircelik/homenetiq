# Documentation Language Cleanup Changelog

**Date:** 2026-06-14
**Scope:** Internationalization of repo for public open-source release.
**Goal:** English as the primary documentation language, Turkish preserved.

## Summary

- All code comments and docstrings → **English**
- All user-facing log/error messages → **English** (where they were in Turkish)
- All primary docs (`README.md`, `docs/*.md`) → **English**
- All changelog and report files → **English**
- Turkish preserved in:
  - `README.tr.md` (Turkish README)
  - `docs/tr/*.tr.md` (Turkish mirrors of all user-facing docs)
- One regression caught and fixed: a docstring in `macos_wifi_agent.py` had a sample that was outside the docstring delimiters, breaking import.

## Files converted from Turkish → English

### Python source (comments, docstrings, log strings)

| File | Change |
|---|---|
| `agents/__init__.py` | rewritten |
| `agents/version.py` | rewritten |
| `agents/config_loader.py` | rewritten |
| `agents/http_client.py` | rewritten |
| `agents/ping.py` | rewritten |
| `agents/privacy.py` | rewritten |
| `agents/time_utils.py` | rewritten |
| `backend/app/main.py` | docstring, description, error message, comment |
| `backend/app/database.py` | docstrings (2) |
| `backend/app/models.py` | docstrings (3) |
| `backend/app/quality.py` | rewritten (all `explanations` strings + docstring) |
| `backend/app/recommendations.py` | rewritten (all 24 recommendation strings + 2 docstrings) |
| `backend/app/root_cause.py` | rewritten |
| `backend/app/settings.py` | docstring |
| `backend/app/thresholds.py` | docstring + comment |
| `collectors/kali_wifi_agent.py` | docstring + 4 user-facing strings |
| `collectors/macos_wifi_agent.py` | docstring + 4 user-facing strings (also fixed docstring delimiter bug) |
| `probes/pi_network_probe.py` | docstring + 2 user-facing strings |
| `dashboard/api_client.py` | docstring + 1 user-facing error |
| `dashboard/formatters.py` | rewritten (all label/format strings) |
| `dashboard/pages.py` | rewritten (all 8 page render functions) |
| `dashboard/streamlit_app.py` | docstring + 2 user-facing strings |
| `dashboard/__init__.py` | docstring |

### Tests

| File | Change |
|---|---|
| `tests/conftest.py` | rewritten (docstrings + comments) |
| `tests/test_api.py` | docstring + 2 function docstrings |
| `tests/test_agent_utils.py` | 2 comment + 1 assertion updates (assertion now checks "not found" substring) |
| `tests/test_dashboard.py` | docstrings + 3 assertion updates (English label values) |
| `tests/test_database.py` | docstring + 4 comments |
| `tests/test_kali_parser.py` | docstring + 3 comments |
| `tests/test_quality.py` | 1 comment block |
| `tests/test_quality_engine.py` | docstring + 7 comments |

### Documentation (English)

| File | Status |
|---|---|
| `README.md` | rewritten |
| `docs/ARCHITECTURE.md` | rewritten |
| `docs/QUALITY_ENGINE.md` | rewritten |
| `docs/AGENTS.md` | rewritten |
| `docs/METRIC_CONTRACT.md` | rewritten |
| `docs/DASHBOARD.md` | rewritten |
| `docs/SETUP_RASPBERRY_PI.md` | rewritten |
| `docs/SETUP_KALI_AGENT.md` | rewritten |
| `docs/SETUP_MACOS_AGENT.md` | rewritten |
| `docs/TROUBLESHOOTING.md` | rewritten |

### Reports / changelogs (English)

| File | Status |
|---|---|
| `docs/dev/REVIEW_REPORT.md` | rewritten |
| `docs/dev/FIX_REPORT.md` | rewritten |
| `docs/dev/QUALITY_ENGINE_CHANGELOG.md` | rewritten |
| `docs/dev/AGENT_CONTRACT_CHANGELOG.md` | rewritten |
| `docs/dev/DASHBOARD_CHANGELOG.md` | rewritten |
| `PROJECT_STATUS.md` | rewritten |
| `RELEASE_NOTES_v1.0.0.md` | rewritten |
| `RELEASE_READINESS_REPORT.md` | rewritten |
| `FINAL_RELEASE_CHECKLIST.md` | rewritten (was already English) |

## Turkish documentation (preserved)

### New Turkish files

| File | Notes |
|---|---|
| `README.tr.md` | Mirrors `README.md` in Turkish; English link at top. |
| `docs/tr/ARCHITECTURE.tr.md` | Mirrors `docs/ARCHITECTURE.md`. |
| `docs/tr/QUALITY_ENGINE.tr.md` | Mirrors `docs/QUALITY_ENGINE.md`. |
| `docs/tr/AGENTS.tr.md` | Mirrors `docs/AGENTS.md`. |
| `docs/tr/METRIC_CONTRACT.tr.md` | Mirrors `docs/METRIC_CONTRACT.md`. |
| `docs/tr/DASHBOARD.tr.md` | Mirrors `docs/DASHBOARD.md`. |
| `docs/tr/SETUP_RASPBERRY_PI.tr.md` | Mirrors `docs/SETUP_RASPBERRY_PI.md`. |
| `docs/tr/SETUP_KALI_AGENT.tr.md` | Mirrors `docs/SETUP_KALI_AGENT.md`. |
| `docs/tr/SETUP_MACOS_AGENT.tr.md` | Mirrors `docs/SETUP_MACOS_AGENT.md`. |
| `docs/tr/TROUBLESHOOTING.tr.md` | Mirrors `docs/TROUBLESHOOTING.md`. |

### Cross-links

Every English doc ends with:
> 🇹🇷 Türkçe: [docs/tr/FILE.tr.md](tr/FILE.tr.md)

The Turkish `README.tr.md` ends with:
> 🇬🇧 English documentation: [README.md](README.md)

## Code comments cleanup summary

- **Bug fix during cleanup:** in `collectors/macos_wifi_agent.py`, the
  docstring for `parse_system_profiler` had a multi-line sample that
  started outside the closing `"""`. This had been working before, but
  during the rewrite the bug would have surfaced as `IndentationError`.
  Fixed by placing the sample inside the docstring.
- **Quality recommendations:** 14 issue tips + 10 root cause tips all
  translated to English.
- **Quality explanations:** all reason strings now in English
  (e.g. `"RSSI -80 dBm below threshold (-75 dBm)"`).
- **Agent error messages:** `iw dev` interface errors, config errors,
  "stopped by user" — all English.
- **Dashboard UI text:** page titles, info messages, captions, "What
  this tool is NOT" — all English.
- **API error messages:** `"Invalid or missing API token"` (was
  Turkish).
- **Test assertions:** updated to match English label/format strings
  (3 dashboard tests, 1 agent utils substring check).

## Files explicitly NOT touched

- `LICENSE` (English MIT, already in English)
- `pytest.ini` (no prose)
- `Makefile` (commands in English)
- `config/*.example` (config keys in English, values mostly empty)
- `database/clickhouse_schema.sql` (SQL, no prose)
- `.github/workflows/ci.yml` (YAML)
- `HomeNetIQ.md` (user file, not ours; pre-existing content preserved)

## Test result

```
$ pytest tests/ -v
====================== 91 passed, 1757 warnings in 7.58s ======================
```

- 91/91 green
- 0 tests changed in count (this round only changed language of comments + label/format assertions)
- `make test` → same result
- `python -m compileall -q backend collectors probes agents dashboard` → exit 0 (25 files)

## Honesty preserved

These critical notes appear in **both** English and Turkish docs:
- "Not a Wi-Fi hacking tool"
- ClickHouse optional
- OpenWrt / router management is future work
- ML-based anomaly detection is not included
- Browser probe is not included
- Limitations section is preserved

## Recommended structure for the public repo

```
/
├── README.md                  # English (primary)
├── README.tr.md               # Turkish mirror
├── LICENSE                    # MIT
├── Makefile
├── pytest.ini
├── .gitignore
├── .github/workflows/ci.yml
├── agents/                    # shared package
├── backend/                   # FastAPI + SQLite
├── collectors/                # Kali, macOS agents
├── probes/                    # Pi probe
├── dashboard/                 # Streamlit
├── config/*.example
├── database/clickhouse_schema.sql
├── docs/                      # English (primary)
│   ├── ARCHITECTURE.md
│   ├── QUALITY_ENGINE.md
│   ├── AGENTS.md
│   ├── METRIC_CONTRACT.md
│   ├── DASHBOARD.md
│   ├── SETUP_RASPBERRY_PI.md
│   ├── SETUP_KALI_AGENT.md
│   ├── SETUP_MACOS_AGENT.md
│   ├── TROUBLESHOOTING.md
│   ├── images/
│   └── tr/                    # Turkish mirrors
│       └── *.tr.md
├── scripts/                   # 4 helper scripts
├── systemd/                   # 3 unit templates
└── tests/                     # 91 tests
```

Rule of thumb: **English for everything by default; Turkish lives in
`README.tr.md` and `docs/tr/`**. No code file contains Turkish.
