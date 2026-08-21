# HomeNetIQ Dashboard

A Streamlit-based local dashboard. It connects to the backend API and
turns metrics into human-readable charts, tables, and explanations.

## Page structure

9 pages, selectable from the sidebar:

| Page | Content |
|---|---|
| Overview | Overall health, latest quality score, latest sample, device status counts, top issues, top recommendations |
| Devices | All devices, latest quality/score, status (active/stale/offline) |
| Wi-Fi Metrics | RSSI/SNR/Tx-rate time series, band distribution, latest connection info |
| Network Metrics | Gateway/AP/internet/DNS latency, packet loss, jitter, short notes |
| Mesh VPN | meshlink tunnel health: peer table (established/path/RTT/rekeys), direct vs relay counts, RTT trend, diagnosis notes |
| Issues & Root Cause | Recent issues (code + explanation), root-cause distribution |
| Recommendations | Deduped, prioritised recommendation list |
| Raw Metrics | Table + JSON debug view |
| About / Setup | Project description, connection info, privacy, "what this is not" |

The Mesh VPN page appears with data once the meshlink health agent
(`collectors/meshlink_agent.py`) has reported at least one `mesh` metric —
see `docs/MESH_INTEGRATION.md`.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `HOMENETIQ_BACKEND_URL` | `http://127.0.0.1:8080` | Backend root URL |
| `HOMENETIQ_API_TOKEN` | (empty) | Optional. GET endpoints do not require auth; if a token is set, the `Authorization` header is added. |

> GET endpoints do not require auth in v1, so the dashboard works
> without a token. If auth is added later, the same variable will work.

## Running the dashboard

```bash
# On the Pi alongside the backend
streamlit run dashboard/streamlit_app.py

# From another device (must be able to reach the Pi)
export HOMENETIQ_BACKEND_URL="http://192.168.1.50:8080"
streamlit run dashboard/streamlit_app.py

# To expose on the LAN (default port 8501)
streamlit run dashboard/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

## Module structure

```
dashboard/
  __init__.py
  api_client.py     # Backend HTTP requests + error handling
  formatters.py     # Pure functions: labels, time, filter, flatten
  pages.py          # render_* function for each page
  streamlit_app.py  # Sidebar router + bootstrap
```

`pages.py` and `streamlit_app.py` depend on Streamlit. `api_client` and
`formatters` are pure modules and are unit-tested; without them, the
dashboard cannot import its helpers.

## Empty data handling

- **Backend down:** every page shows `st.error("Cannot reach backend...")`;
  the app does not crash.
- **No metrics yet:** `st.info("No metrics received yet.")` or a
  page-specific informational message.
- **Field missing** (e.g. `packet_loss` never measured): instead of a
  chart, "No data yet for this field".
- **Cache:** `_cached_*` refreshes from the backend every 10 seconds.
  For a manual refresh, press `C` in Streamlit or call `st.rerun()`.

## Backend API usage

| Page | Endpoint |
|---|---|
| Overview | `/api/v1/summary`, `/api/v1/devices`, `/api/v1/metrics/latest` |
| Devices | `/api/v1/devices`, `/api/v1/metrics/latest` |
| Wi-Fi Metrics | `/api/v1/metrics/latest` (filter: `metric_type=="wifi"`) |
| Network Metrics | `/api/v1/metrics/latest` (filter: `metric_type=="network"`) |
| Issues & Root Cause | `/api/v1/metrics/latest` |
| Recommendations | `/api/v1/metrics/latest` |
| Raw Metrics | `/api/v1/metrics/latest` |

## Known limitations

- **Streamlit 1.41 + starlette compatibility:** Python 3.14 has an
  import error between Streamlit and starlette. On a Pi (Python 3.11/3.12)
  this is not a problem. Only an issue in test/CI on 3.14.
- **No CORS:** the backend has no CORS middleware. Currently not needed
  (dashboard calls the API server-side). Will be needed if a
  browser-based UI is added.
- **Lightweight charts:** only `st.line_chart`, `st.bar_chart`,
  `st.dataframe`, `st.metric`. Plotly/Altair are not used to stay
  Pi-friendly.
- **Cache TTL 10s:** neither too aggressive nor too passive. For a
  manual refresh, press `C` in Streamlit.

## Future improvements

1. **Device detail page** using `/api/v1/devices/{id}/latest`.
2. **Time-range filter** (last 1h / 24h / 7d).
3. **Anomaly highlighting** (red rows for `quality != "good"`).
4. **Score summary** (average score across all devices).
5. **CSV export** of the Raw Metrics page.
6. **Charts-only toggle** for a kiosk-style display.

> 🇹🇷 Türkçe: [docs/tr/DASHBOARD.tr.md](tr/DASHBOARD.tr.md)
