# PROJECT_STATUS

**HomeNetIQ v1.0.0 — release candidate**

## Goal

A self-hosted, Pi-friendly, simple network intelligence and telemetry
system that runs on the local network. v1 scope:

- Metric ingest + REST API
- Rule-based quality scoring (0-100) + issue + root cause
- Human-readable recommendations
- 4 agents: Kali/Linux Wi-Fi, macOS Wi-Fi, Pi/Linux network probe,
  meshlink VPN health (optional)
- Multi-page Streamlit dashboard
- systemd-based service management + one-command installer/run scripts

## What is NOT in v1 (deliberate)

- ❌ Wi-Fi hacking / sniffing / deauth (illegal and not needed)
- ❌ Neighbor-network scanning
- ❌ ISP speed guarantee / SLA measurement
- ❌ Professional RF survey tool
- ❌ OpenWrt / router management
- ❌ Cloud backend (data always stays local)
- ❌ ML-based anomaly detection (rule-based is enough)
- ❌ Mobile app
- ❌ Multi-tenant auth

## What IS in v1

- ✅ FastAPI backend + SQLite + migration
- ✅ Quality engine (4-tuple: quality, score, issues, explanations)
- ✅ Root cause classifier (10+ labels)
- ✅ Recommendation engine (English; Turkish in docs)
- ✅ 4 agents (Kali, macOS, Pi, meshlink health) — canonical payload + privacy
- ✅ Dashboard (9 pages, empty-data safe)
- ✅ 100 tests (100% green)
- ✅ systemd units + GitHub Actions CI
- ✅ docs/ (ARCHITECTURE, QUALITY_ENGINE, AGENTS, METRIC_CONTRACT, DASHBOARD, SETUP_*, TROUBLESHOOTING) + docs/tr/ for Turkish
- ✅ Makefile (test, run-backend, run-dashboard, kali-once, pi-probe-once)
- ✅ MIT License
- ✅ README.tr.md (Turkish README)

## v2 candidates (backlog — not in v1)

The following are deliberately out of v1 scope. v2 may consider them:

- 📊 **Trend analysis & push-based delivery:** v1 only shows the latest snapshot; trend over the last N metrics or WebSocket push in v2.
- 🧠 **ML-based anomaly detection:** v1 is rule-based; sufficient and explainable for the user.
- 🌐 **Browser probe:** `metric_type="browser"` is defined but no agent; v2 could ship a simple extension.
- 🏠 **OpenWrt / router management:** v1 is read-only; v2 may add router config writes.
- 📈 **Optional ClickHouse export:** schema is ready, ingestion is not. v2: "export to ClickHouse" job.
- 🪟 **macOS BSSID:** v1 doesn't include it (no offensive tool dependency). v2: `airport -I` integration.
- 🔐 **Multi-tenant auth:** v1 single-user. Production-grade identity layer in v2.
- 📱 **Mobile app / PWA:** v1 doesn't include it. v2+ candidate.
- 🌐 **i18n (TR/EN):** v1 English recommendations. v2: `tr` mapping.
- 🔁 **Exponential backoff:** v1 linear retry. v2: exponential.
- 🧪 **Mutation test (mutmut):** to measure test quality in v2.
- 🔌 **CORS middleware:** v1 doesn't include it. Will be needed for a browser UI.
- 📡 **Wi-Fi 6E / 6 GHz detail:** v1 has basic info; v2: channel utilization, OBSS, etc.
- 🔍 **Log query / search:** v1 has no logs; v2: structured logs + search.

## Test summary

```
$ pytest tests/ -v
====================== 100 passed in 12.0s ======================
```

## Post-v1 addendum: meshlink VPN health monitoring

Shipped after the v1.0.0 tag (see `docs/MESH_INTEGRATION.md`):

- New optional agent `collectors/meshlink_agent.py` — reads a
  [meshlink](https://github.com/firfircelik/network-project)
  `agent status --json` snapshot and posts one `metric_type="mesh"`
  metric per peer.
- Quality rules + root causes for tunnel health (`mesh_peer_offline`,
  `nat_traversal_limited`, ...), new thresholds, recommendations.
- Dashboard "Mesh VPN" page (peer table, direct/relay counts, RTT trend).
- `scripts/install.sh` (one-command setup incl. meshlink binaries and
  pinned-key capture) and `scripts/run-all.sh` (full local stack).
- Tests: 91 → 100.

## Release blocker status

| Blocker | Status |
|---|---|
| Backend won't start | ✅ Fixed (lifespan) |
| Test import broken | ✅ Fixed (`backend/__init__.py`) |
| Auth + token generation | ✅ Fixed |
| Dashboard backend connection | ✅ Fixed |
| Privacy: raw BSSID | ✅ Fixed (redact/hash) |
| Config user/path mismatch | ✅ Fixed (template notes) |
| CI | ✅ Fixed (GitHub Actions) |
| Python 3.11/3.12 compatibility | ✅ Verified |
| Python 3.14 warning | ✅ Documented |
| Agent error handling | ✅ Fixed (retry + exit code) |

## Release order

1. Mac mini: development + tests (here)
2. Push to GitHub
3. Raspberry Pi: clone, install, enable systemd
4. Kali MacBook Air: clone, install, enable systemd
5. (Optional) macOS: launchd or manual

Details: `RELEASE_READINESS_REPORT.md`.
