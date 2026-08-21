# HomeNetIQ v1.0.0

![Status: Release Candidate](https://img.shields.io/badge/status-release--candidate-blue)
![Python: 3.11 | 3.12](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Tests: 100/100](https://img.shields.io/badge/tests-100%2F100-brightgreen)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

HomeNetIQ is a self-hosted network intelligence platform that measures the
quality of your home network and Wi-Fi connection. It only collects
telemetry from your own devices on your own network — it is **not a
Wi-Fi hacking tool, not a neighbor-network scanner, and not an attack
tool**.

It can also monitor the health of a [meshlink](https://github.com/firfircelik/network-project)
encrypted P2P mesh VPN — tunnel path (direct/relay), RTT, rekeys and peer
availability become part of the same quality score and dashboard. See
[docs/MESH_INTEGRATION.md](docs/MESH_INTEGRATION.md).

> 🇹🇷 Turkish documentation: [README.tr.md](README.tr.md)

## Architecture

- **Raspberry Pi** — Backend API + SQLite database + network probe (latency + DNS)
- **Kali Linux MacBook Air** — Wi-Fi probe (`iw` + ping)
- **TP-Link TL-WR850N** — Lab access point
- **Optional Mac mini** — Second probe or development host

> All commands below are meant to be run from the **repo root**
> (`HomeNetIQ_v1/`). The only exception is `pip install` and
> `python -m venv`, which are run inside the backend virtualenv.

## Quick Start

### 1. Generate an API token

The backend and agents/probes share a Bearer token. Always use a random
token in production:

```bash
# 32-byte hex token, plenty strong for local use
openssl rand -hex 32
```

> The value `change-me-local-token` only appears in this README and the
> example config files. It is **for local testing only** and must not be
> used on an internet-exposed installation.

### 2. Raspberry Pi backend

```bash
# From the repo root
cp config/backend.env.example backend/.env

# Edit backend/.env and replace HOMENETIQ_API_TOKEN with the value you generated
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# The database directory (where HOMENETIQ_DB_PATH points) is created
# automatically on first run. No manual mkdir needed. If you prefer,
# you can pre-create it: mkdir -p "$(dirname <HOMENETIQ_DB_PATH>)"

cd ..   # back to repo root
uvicorn backend.app.main:app --host 0.0.0.0 --port 8080
# or use the helper script: bash scripts/run_backend_dev.sh
```

Health check:

```bash
curl http://127.0.0.1:8080/health
# {"status":"ok","service":"homenetiq-backend"}
```

### 3. Pi network probe (same Pi)

```bash
# From the repo root
cp config/pi_probe.yaml.example config/pi_probe.yaml
# Edit the `targets` section to match your network

python3 probes/pi_network_probe.py --config config/pi_probe.yaml --once
```

### 4. Kali Linux Wi-Fi agent

```bash
# From the repo root
cp config/kali_agent.yaml.example config/kali_agent.yaml
# Edit `targets` and the backend URL (the Pi's LAN IP)

python3 collectors/kali_wifi_agent.py --config config/kali_agent.yaml --once
```

> **Note:** `iw dev <iface> link` may require root or `CAP_NET_ADMIN` on
> some systems. If you get "Operation not permitted" running as a normal
> user, either run as root or add `AmbientCapabilities=CAP_NET_ADMIN`
> to the systemd service (see the "systemd" section below).

### 5. Dashboard (any device)

The dashboard calls the backend's GET endpoints. **GET endpoints do not
require auth** (only `POST /api/v1/metrics` requires the token). The
dashboard only needs the backend URL.

```bash
# Point at the backend running on the Pi
export HOMENETIQ_BACKEND_URL="http://192.168.1.50:8080"
# (The token is technically not required for GETs, but exporting it now
# means the same variable will work if auth is added later.)
export HOMENETIQ_API_TOKEN="<token you generated above>"

streamlit run dashboard/streamlit_app.py
```

The dashboard opens at <http://localhost:8501>.

#### Dashboard pages

| Page | What it shows |
|---|---|
| Overview | Overall health, latest quality score, top issues, top recommendations |
| Devices | Device list with status and latest quality |
| Wi-Fi Metrics | RSSI/SNR/Tx-rate time series, band distribution |
| Network Metrics | Gateway/AP/internet latency, packet loss, jitter, short notes |
| Mesh VPN | meshlink tunnel health: peer table, direct/relay paths, RTT trend, rekeys |
| Issues & Root Cause | Recent issues and root-cause distribution |
| Recommendations | Deduped, prioritised recommendation list |
| Raw Metrics | Raw JSON view (debug) |
| About / Setup | Project description, connection info, privacy |

#### Access from another device

```bash
# On the Pi, expose the dashboard on the LAN
streamlit run dashboard/streamlit_app.py --server.address 0.0.0.0 --server.port 8501

# On the Mac
export HOMENETIQ_BACKEND_URL="http://192.168.1.50:8080"
streamlit run dashboard/streamlit_app.py
# Browser: http://<pi-ip>:8501
```

Details: `docs/DASHBOARD.md`.

### 6. Optional: Mesh VPN monitoring (meshlink)

If you run a [meshlink](https://github.com/firfircelik/network-project)
encrypted P2P mesh, HomeNetIQ can score its health too — tunnel path
(direct/relay), RTT, rekeys and peer availability on the same dashboard.

One-command setup (builds/installs meshlink binaries, generates the config,
captures the coordinator's pinned public key, writes systemd units):

```bash
./scripts/install.sh
sudo systemctl enable --now homenetiq-mesh-agent   # Linux/systemd
```

Manual alternative:

```bash
cp config/meshlink_agent.yaml.example config/meshlink_agent.yaml
# Edit the `meshlink:` section: bin, name, keyfile, coordinator,
# coord_pubkey (from the coordinator log) and optionally probe_peer.

make mesh-once    # one tick; drop --once for the continuous loop
```

Details: `docs/MESH_INTEGRATION.md`.

## systemd services

There are 4 unit files in `systemd/`. **They must be edited for your
device before being installed: hard-coded user/path values are placeholders.**
(`scripts/install.sh` fills them in automatically.)

Before copying a unit:

1. Replace `User=<YOUR_USER>` with the Linux account that will run the service.
2. Replace `WorkingDirectory=/home/<YOUR_USER>/homenetiq` (and any
   `/home/<YOUR_USER>/homenetiq/backend` paths) with your repo location.
3. Update `EnvironmentFile=` and `.venv` paths accordingly.
4. For the **Kali** service: if it needs to run `iw`, add the following
   capability lines (so the service runs without root):

   ```ini
   CapabilityBoundingSet=CAP_NET_ADMIN
   AmbientCapabilities=CAP_NET_ADMIN
   NoNewPrivileges=true
   ```

Install:

```bash
sudo cp systemd/homenetiq-backend.service   /etc/systemd/system/
sudo cp systemd/homenetiq-pi-probe.service  /etc/systemd/system/
# On the Kali device:
sudo cp systemd/homenetiq-kali-agent.service /etc/systemd/system/
# On the meshlink host (optional, VPN health monitoring):
sudo cp systemd/homenetiq-mesh-agent.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now homenetiq-backend
sudo systemctl enable --now homenetiq-pi-probe
# On the Kali device:
sudo systemctl enable --now homenetiq-kali-agent
# On the meshlink host (optional):
sudo systemctl enable --now homenetiq-mesh-agent
sudo systemctl status homenetiq-backend --no-pager
```

## Tests

```bash
# Set up the venv and run the suite
make install
make test                    # runs all 100 tests
```

Or manually:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# Run the test suite (no PYTHONPATH needed; pytest.ini sets pythonpath = .)
pytest tests/ -v
```

Expected: `100 passed`.

Other Makefile targets:

```bash
make install            # install venv + dependencies
make test               # pytest
make run-backend        # uvicorn --reload
make run-dashboard      # streamlit
make kali-once          # Kali agent: one tick
make macos-once         # macOS agent: one tick
make pi-probe-once      # Pi probe: one tick
make mesh-once          # meshlink VPN health agent: one tick
make clean              # __pycache__ + .pytest_cache
```

## Security & Privacy

This project is for your own home/lab network only. It is not designed to
scan, attack, or collect data from networks you don't own. Do not expose
the backend directly to the public internet. Never commit the API token
in `.env` to version control.

Agents never send BSSID/MAC addresses in raw form. The default `redact`
mode keeps only the last two octets (e.g. `...:44:55`). The optional
`hash` mode uses SHA-256 with a user-supplied salt; there is **no fixed
salt**. Neighbor-network lists, MAC vendor info, and any data outside
the user's own device/network are **not** collected or sent.

## What this tool is NOT

- ❌ Not a Wi-Fi hacking, deauth, or sniffing tool.
- ❌ Not a tool for scanning or attacking neighboring networks.
- ❌ Not an ISP speed-guarantee or SLA measurement tool.
- ❌ Not a replacement for a professional RF survey tool.
- ❌ Not a cloud service — all data stays on your device.

## Honesty & limitations (v1)

- **ClickHouse** is optional and not used at runtime. The schema file is
  reference only.
- **OpenWrt / router management** is not included (read-only observations
  only in v1).
- **Browser probe** is not implemented (the `metric_type` exists in the
  contract but no agent is provided).
- **ML-based anomaly detection** is not included; v1 is rule-based.
- **License:** see [LICENSE](LICENSE) — MIT.
- See `PROJECT_STATUS.md` and `RELEASE_NOTES_v1.0.0.md` for the full list.

## More

- Architecture: `docs/ARCHITECTURE.md`
- Quality engine (score, issues, root cause, recommendations): `docs/QUALITY_ENGINE.md`
- Agents: `docs/AGENTS.md`
- Metric payload contract: `docs/METRIC_CONTRACT.md`
- Dashboard: `docs/DASHBOARD.md`
- Mesh VPN monitoring (meshlink): `docs/MESH_INTEGRATION.md`
- Pi setup: `docs/SETUP_RASPBERRY_PI.md`
- Kali setup: `docs/SETUP_KALI_AGENT.md`
- macOS setup: `docs/SETUP_MACOS_AGENT.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`
- Project status: `PROJECT_STATUS.md`
- Release notes: `RELEASE_NOTES_v1.0.0.md`
- Release readiness: `RELEASE_READINESS_REPORT.md`
- Language cleanup changelog: `DOCS_LANGUAGE_CHANGELOG.md`
- Final checklist: `FINAL_RELEASE_CHECKLIST.md`
- Initial push report: `INITIAL_PUSH_REPORT.md`
- Development notes (historical): `docs/dev/`

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE)
for the full text.

```
MIT License — Copyright (c) 2026 Firat Celik
```
