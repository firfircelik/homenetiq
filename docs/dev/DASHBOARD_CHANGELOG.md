# Dashboard Changelog

**Date:** 2026-06-14
**Scope:** Streamlit dashboard turned into a multi-page network intelligence panel.

## Added / changed files

| File | Status | Description |
|---|---|---|
| `dashboard/__init__.py` | new | Package init |
| `dashboard/api_client.py` | new | Backend HTTP client + error handling |
| `dashboard/formatters.py` | new | Pure formatting, labels, time, filter, flatten |
| `dashboard/pages.py` | new | `render_*` function for each page |
| `dashboard/streamlit_app.py` | refactor | Sidebar router + bootstrap (thin) |
| `docs/DASHBOARD.md` | new | Dashboard architecture, running, limitations |
| `docs/images/` | new | Screenshot placeholder directory |
| `README.md` | updated | Dashboard section + page list + access instructions |
| `tests/test_dashboard.py` | new | 28 tests (api_client, formatters, import) |

## Added pages

1. **Overview** — Overall health card, quality_score, root cause, latest sample, active/stale/offline counts, top issues, top recommendations
2. **Devices** — All devices table (status, last_seen, latest_quality, latest_quality_score)
3. **Wi-Fi Metrics** — RSSI/SNR/Tx rate time series, band distribution (bar), last SSID/BSSID/PHY/MCS
4. **Network Metrics** — Gateway/AP/Internet/DNS latency charts, packet loss, jitter, short notes
5. **Issues & Root Cause** — Recent issues table, root cause distribution
6. **Recommendations** — Deduped, prioritised recommendation list
7. **Raw Metrics** — Summary table + JSON debug view
8. **About / Setup** — Project description, connection info, privacy, "what this is not" section

## API endpoints used

| Page | Endpoint |
|---|---|
| All pages | `/api/v1/summary` (Overview) |
| Devices | `/api/v1/devices` |
| All pages | `/api/v1/metrics/latest?limit=200` |

No new backend endpoints were added; existing GET endpoints were sufficient.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `HOMENETIQ_BACKEND_URL` | `http://127.0.0.1:8080` | Backend root URL |
| `HOMENETIQ_API_TOKEN` | (empty) | Optional; when set, the `Authorization` header is added |

GET endpoints do not require auth, so the dashboard works without a token.

## Module structure

`streamlit_app.py` → `pages.py` (streamlit-dependent) → `api_client.py` (HTTP) + `formatters.py` (pure functions).

`api_client` and `formatters` are tested; `pages` and `streamlit_app` depend on streamlit and are verified manually.

## Empty data handling

- **Backend down:** every page shows `st.error("Cannot reach backend...")`; the app does not crash.
- **No metrics yet:** `st.info("No metrics received yet.")` or a page-specific informational message.
- **Field missing** (e.g. `packet_loss`): instead of a chart, "No data yet for this field".
- **Cache:** `@st.cache_data(ttl=10)` refreshes the backend every 10 seconds.

## Tests

| Test file | Test count |
|---|---|
| `tests/test_dashboard.py` | 28 (new) |
| Other tests | 63 (unchanged) |

**Total: 63 → 91 (28 new tests). All green.**

New tests:
- `api_client`: env fallback, error handling (connection error, HTTP error, JSON parse), Authorization header add/remove
- `formatters`: quality/root cause labels, time formatting, filtering, flattening, DataFrame, recommendation/issue collection
- import: dashboard modules (except streamlit) are importable

## Known limitations

1. **Streamlit 1.41 + starlette compatibility:** Python 3.14 has a streamlit+starlette import error. Production Pi (3.11/3.12) is fine. In test/CI, streamlit-dependent pages are not imported directly; only pure modules are tested.
2. **No CORS middleware:** not in the backend. Not an issue currently (dashboard calls the API server-side); will be needed when adding a browser-based UI.
3. **Lightweight charts:** only `st.line_chart`, `st.bar_chart`, `st.dataframe`, `st.metric`. Plotly/Altair are not used to stay Pi-friendly.
4. **Cache TTL 10s:** not too aggressive, not too passive. For a manual refresh, press `C` in Streamlit.
5. **No device-detail page:** all devices are in a single table; for trend graphs, `/api/v1/devices/{id}/latest` could power a separate page.

## Future improvements

1. **Device detail page:** drill-down using `/api/v1/devices/{id}/latest`.
2. **Time-range filter:** last 1h / 24h / 7d.
3. **Anomaly highlighting:** red rows for `quality != "good"`.
4. **Score summary:** average score across all devices.
5. **CSV export** from the Raw Metrics page.
6. **Trend indicators:** ↑/↓ arrows for RSSI/latency trends.
7. **Notification settings:** Slack/email webhook (v2).
8. **Comparative view:** two devices side by side.

## Run

```bash
pytest tests/ -v
# 91 passed
```

```bash
export HOMENETIQ_BACKEND_URL="http://192.168.1.50:8080"
streamlit run dashboard/streamlit_app.py
# http://localhost:8501
```
