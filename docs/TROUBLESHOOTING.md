# Troubleshooting

Common errors and how to fix them. If your error is not here, see
`docs/SETUP_*.md` or `docs/AGENTS.md`.

## Backend

### "Connection refused" / "Cannot reach backend"

Cause: backend is not running, or it's on a different host:port.

Check:

```bash
# On the Pi
sudo systemctl status homenetiq-backend
# or run manually
.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8080
```

On the dashboard side, is `HOMENETIQ_BACKEND_URL` correct?

```bash
export HOMENETIQ_BACKEND_URL="http://192.168.1.50:8080"
```

### 401 Unauthorized

`POST /api/v1/metrics` requires a Bearer token.

```bash
curl -X POST http://127.0.0.1:8080/api/v1/metrics \
  -H "Authorization: Bearer <token from backend .env>" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

Token mismatch:

- `HOMENETIQ_API_TOKEN` in the backend and `backend.token` in the
  agent must be the same.
- After changing the token, update every agent too.
- You can disable auth for testing by setting
  `HOMENETIQ_REQUIRE_AUTH=false`.

### "no such table: devices"

DB init did not run. Either lifespan didn't fire, or the DB file is
corrupt.

```bash
# Manual init
python3 -c "from backend.app.database import init_db; init_db()"

# If the DB is corrupt, back it up and remove it
mv data/homenetiq.sqlite3 data/homenetiq.sqlite3.bak
# Then restart the backend
```

### "Address already in use" (port 8080)

```bash
sudo lsof -i :8080
# Kill the PID from the output, or use a different port
HOMENETIQ_DB_PATH=... uvicorn backend.app.main:app --port 8081
```

### Backend won't start, no error in logs

Check the journal:

```bash
sudo journalctl -u homenetiq-backend -n 50 --no-pager
```

Run it manually to get a traceback:

```bash
cd /home/pi/homenetiq
HOMENETIQ_API_TOKEN=test-tok python3 -m uvicorn backend.app.main:app
```

## Agents (Kali, macOS, Pi probe)

### `iw dev` or `iw dev wlan0 link` → "Operation not permitted"

`iw` requires root or `CAP_NET_ADMIN`. Options:

- Temporary: run the agent with `sudo`.
- Permanent: enable in the systemd unit:
  `CapabilityBoundingSet=CAP_NET_ADMIN` and
  `AmbientCapabilities=CAP_NET_ADMIN`.

Details: `docs/SETUP_KALI_AGENT.md` § "Root / CAP_NET_ADMIN".

### "No Wi-Fi interface found"

```bash
iw dev
ip link
```

If there is no Wi-Fi interface at all, this device cannot be used as a
Wi-Fi probe. Use only the Pi probe.

If `iw dev` does show an interface, set the interface name explicitly
in `config/kali_agent.yaml` (`collector.interface: wlan0` etc.) instead
of `auto`.

### "No SSID found" (macOS)

Wi-Fi is off or not connected. Check System Preferences > Network > Wi-Fi.

### "DNS response time is high" (slow DNS)

The issue is not the device; it's the DNS resolver. See
`docs/QUALITY_ENGINE.md` or the dashboard **Recommendations** page.

### Backend connection refused (agent side)

The agent can't reach the backend. Check:

```bash
# From the agent device (Kali, macOS, Pi)
curl http://192.168.1.50:8080/health
```

If you don't get a response:

- Is the Pi on? `ping 192.168.1.50`
- Did the Pi firewall block 8080? `sudo ufw allow 8080`
- Is the backend still running? `systemctl status homenetiq-backend`
- Wrong IP: check `HOMENETIQ_BACKEND_URL` or `backend.url` in config.

In the agent log:

```
{"ok": false, "error": "ApiUnavailable: Cannot reach backend..."}
```

This is not a bug — it means the agent is reporting a problem correctly.
The agent retries after `retry_delay_seconds`.

## Dashboard

### "No metrics received yet"

- Is the backend up? (see above)
- Are the agents running? `systemctl status` or try `--once`.
- Does the agent log show `ok: true`?
- Is the token consistent?

### "Cannot reach backend: ..."

Is `HOMENETIQ_BACKEND_URL` correct? Start manually:

```bash
HOMENETIQ_BACKEND_URL=http://192.168.1.50:8080 \
  python3 -m streamlit run dashboard/streamlit_app.py
```

### Streamlit import error on Python 3.14

Python 3.14 + starlette compatibility issue. Use Python 3.11 or 3.12.
See the note at the top of `backend/requirements.txt`.

### Empty chart / "No data yet for ..."

That field is not present in the payload. Wi-Fi metrics may not have
`rssi`/`snr` when the device is disconnected. This is expected, not
"No metrics received yet" — only that specific field is missing.

## systemd

### "Unit not found"

```bash
sudo systemctl daemon-reload
sudo systemctl list-unit-files | grep homenetiq
```

### Service won't start, "status=203/EXEC"

`ExecStart` path is wrong. Check:

```bash
# On the Pi
ls -la /home/pi/homenetiq/.venv/bin/uvicorn
# or
ls -la /home/pi/homenetiq/.venv/bin/python
```

The path in the unit's `ExecStart` must match.

### "Permission denied" / cannot read .env

Verify the `EnvironmentFile` is readable by the user:

```bash
ls -l /home/pi/homenetiq/backend/.env
chmod 600 /home/pi/homenetiq/backend/.env
```

### Service in a restart loop

Check the log:

```bash
sudo journalctl -u homenetiq-backend -n 100 --no-pager
```

A repeated exception usually means a config error or a DB permission
issue. Run manually:

```bash
cd /home/pi/homenetiq
HOMENETIQ_API_TOKEN=test-tok python3 -m uvicorn backend.app.main:app
```

## Python / pip

### pydantic-core build error (Python 3.14)

```
× Failed to build installable wheels for some pyproject.toml based projects
╰─▶ pydantic-core
```

Solution: use Python 3.11 or 3.12. See `backend/requirements.txt` for details.

### "No module named 'streamlit'" (during test)

Streamlit is not needed for tests, but if something imports it:

```bash
pip install -r backend/requirements.txt
```

Streamlit is only required for the dashboard; unit tests don't import
it.

> 🇹🇷 Türkçe: [docs/tr/TROUBLESHOOTING.tr.md](tr/TROUBLESHOOTING.tr.md)
