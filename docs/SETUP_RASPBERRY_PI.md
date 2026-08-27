# Raspberry Pi Setup

This document is **one** way to run HomeNetIQ — a Raspberry Pi is optional.
Any Linux host (VM, NUC, old laptop) works the same; substitute paths and
`User=` accordingly. There is no required SKU.

This walkthrough installs the backend, an optional network probe, and the
dashboard. The goal is a single command that starts everything, with the
service managed by systemd.

## 1. Prerequisites

- Raspberry Pi OS Bookworm (Debian 12) or similar
- Python 3.11 or 3.12 (default on Pi OS; check with `python3 --version`)
- Internet access (for the first `pip install`)
- A static LAN IP or DHCP reservation (e.g. `YOUR_BACKEND_HOST`)
- Free ports 8080 (backend) and 8501 (dashboard)

## 2. User and directory

In this example the user is `pi` and the repo lives at
`/home/YOUR_USER/homenetiq`:

```bash
sudo useradd -m -s /bin/bash pi    # already exists on default Pi OS
sudo -iu pi
git clone https://github.com/<user>/HomeNetIQ.git /home/YOUR_USER/homenetiq
cd /home/YOUR_USER/homenetiq
```

> **IMPORTANT:** The systemd unit files are templates. Before
> installation, edit the `User=`, `WorkingDirectory=`, `ExecStart=`, and
> `EnvironmentFile=` lines in `systemd/homenetiq-backend.service` and
> `systemd/homenetiq-pi-probe.service` to match your paths.

## 3. Virtualenv and dependencies

```bash
cd /home/YOUR_USER/homenetiq
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

> On Python 3.14 you may hit a pydantic-core wheel build issue; 3.11/3.12
> is recommended. See the note at the top of `backend/requirements.txt`.

## 4. Backend .env

```bash
cp config/backend.env.example backend/.env
nano backend/.env
```

Production values:

```
HOMENETIQ_DB_PATH=/home/YOUR_USER/homenetiq/data/homenetiq.sqlite3
HOMENETIQ_API_TOKEN=<output of `openssl rand -hex 32`>
HOMENETIQ_REQUIRE_AUTH=true
HOMENETIQ_STALE_AFTER_SECONDS=120
HOMENETIQ_OFFLINE_AFTER_SECONDS=600
```

The `data/` directory is created automatically at runtime.

## 5. First manual run

Run it manually first, then move to systemd:

```bash
cd /home/YOUR_USER/homenetiq
make install
make test                    # pytest should pass
HOMENETIQ_API_TOKEN=test-tok bash scripts/run_backend_dev.sh
```

In a separate terminal, health check:

```bash
curl http://127.0.0.1:8080/health
# {"status":"ok","service":"homenetiq-backend"}

curl -X POST http://127.0.0.1:8080/api/v1/metrics \
  -H "Authorization: Bearer test-tok" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id":"pi-manual","device_type":"network_probe",
    "metric_type":"network",
    "payload":{"internet_latency_ms":40}
  }'
```

The response should include `quality`, `issues`, `root_cause`,
`quality_score`, `explanations`, and `recommendations`.

Try the dashboard manually too:

```bash
# Another terminal on the same Pi
make run-dashboard
# http://<pi-ip>:8501
```

## 6. Pi network probe

```bash
cp config/pi_probe.yaml.example config/pi_probe.yaml
nano config/pi_probe.yaml
# Fill in gateway_ip, ap_ip, internet_ip, dns_domains for your network
```

Test it once:

```bash
make pi-probe-once
# Expect JSON output with "ok": true
```

## 7. systemd services

First edit the unit files (your user/WorkingDirectory/ExecStart paths):

```bash
nano systemd/homenetiq-backend.service
nano systemd/homenetiq-pi-probe.service
```

Then install:

```bash
sudo cp systemd/homenetiq-backend.service  /etc/systemd/system/
sudo cp systemd/homenetiq-pi-probe.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now homenetiq-backend
sudo systemctl enable --now homenetiq-pi-probe
sudo systemctl status homenetiq-backend --no-pager
sudo systemctl status homenetiq-pi-probe --no-pager
```

Logs:

```bash
sudo journalctl -u homenetiq-backend -f
sudo journalctl -u homenetiq-pi-probe -f
```

## 8. Expose the dashboard on the LAN (optional)

Streamlit binds to localhost by default. To expose on the LAN:

```bash
# Extra systemd unit, or via nohup:
HOMENETIQ_BACKEND_URL=http://YOUR_BACKEND_HOST:8080 \
nohup .venv/bin/streamlit run dashboard/streamlit_app.py \
  --server.address 0.0.0.0 --server.port 8501 \
  > logs/dashboard.log 2>&1 &
```

You can also write a small systemd unit for it. See the Dashboard
section in the README.

## 9. Health check commands (on the Pi)

```bash
# Backend
curl -s http://127.0.0.1:8080/health

# Devices (GET auth is on by default)
curl -s -H "Authorization: Bearer $HOMENETIQ_API_TOKEN" \
  http://127.0.0.1:8080/api/v1/devices

# Latest metrics
curl -s -H "Authorization: Bearer $HOMENETIQ_API_TOKEN" \
  http://127.0.0.1:8080/api/v1/metrics/latest?limit=5

# Summary
curl -s -H "Authorization: Bearer $HOMENETIQ_API_TOKEN" \
  http://127.0.0.1:8080/api/v1/summary
```

## 10. Common errors

See `docs/TROUBLESHOOTING.md`. Summary:

- **Backend won't start:** `journalctl -xe` or run
  `python3 -m uvicorn backend.app.main:app` manually.
- **`no such table: devices`:** init_db didn't run. Run manually:
  `python3 -c "from backend.app.database import init_db; init_db()"`.
- **401 Unauthorized:** `HOMENETIQ_API_TOKEN` mismatch; agent and
  backend must share the same token.
- **port 8080 already in use:** `sudo lsof -i :8080` to find who has it.

## 11. Upgrading (later)

```bash
cd /home/YOUR_USER/homenetiq
git pull
source .venv/bin/activate
pip install -r backend/requirements.txt
sudo systemctl restart homenetiq-backend
sudo systemctl restart homenetiq-pi-probe
```

If the DB schema changes, `init_db()` auto-migrates. No manual
intervention required.

> 🇹🇷 Türkçe: [docs/tr/SETUP_RASPBERRY_PI.tr.md](tr/SETUP_RASPBERRY_PI.tr.md)
