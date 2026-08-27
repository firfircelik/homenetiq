# Kali Linux Wi-Fi Agent Setup

This document describes how to install the HomeNetIQ Wi-Fi agent on a
Kali Linux (or other Linux) laptop. **It only collects telemetry from
your own device on your own network; it does not scan or attack other
networks.**

## 1. Prerequisites

- Kali Linux 2024+ or any Debian-based Linux
- Python 3.11 or 3.12
- `iw` package (preinstalled on Kali; if not: `sudo apt install iw`)
- An active Wi-Fi connection (test with `iw dev`)
- The backend running and reachable on the network (`YOUR_BACKEND_HOST:8080`;
  any Linux host — a Raspberry Pi is optional)

## 2. Clone the repo

```bash
git clone https://github.com/<user>/HomeNetIQ.git ~/homenetiq
cd ~/homenetiq
```

> **IMPORTANT:** The Kali systemd unit is a template. Before
> installation, edit the `User=`, `WorkingDirectory=`, and `ExecStart=`
> lines in `systemd/homenetiq-kali-agent.service` to match your paths.

## 3. Virtualenv

```bash
cd ~/homenetiq
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## 4. Config

```bash
cp config/kali_agent.yaml.example config/kali_agent.yaml
nano config/kali_agent.yaml
```

Fields to edit:

| Field | Example |
|---|---|
| `device.id` | `"linux-wifi-1"` (must be persistent and unique) |
| `device.name` | `"Linux Wi-Fi probe"` |
| `backend.url` | `"http://YOUR_BACKEND_HOST:8080/api/v1/metrics"` |
| `backend.token` | The `HOMENETIQ_API_TOKEN` from `backend/.env` on the Pi |
| `collector.interface` | `"auto"` (auto-detect first Wi-Fi interface) |
| `privacy.mode` | `"redact"` (recommended) or `"hash"` |
| `targets.gateway_ip` | Router LAN IP (your gateway; do not guess) |
| `targets.ap_ip` | your access point IP |
| `targets.internet_ip` | `1.1.1.1` or `8.8.8.8` |

## 5. First manual run

```bash
make kali-once
```

Expected: a JSON output with `ok: true` and a `metric_id` from the
backend.

Possible errors:

- **`Operation not permitted` (iw):** `iw dev <iface> link` requires root
  or `CAP_NET_ADMIN`.
- **`No Wi-Fi interface found`:** no wireless adapter, or the interface
  is down.

## 6. Root / CAP_NET_ADMIN

Two options:

### Option A: run the service as root (simple but risky)

Change `User=root` in `systemd/homenetiq-kali-agent.service`. **Not
recommended**, since the agent then runs as root in the background at
all times.

### Option B: CAP_NET_ADMIN without root (recommended)

1. Run the service as your normal Linux user (`YOUR_USER`).
2. In `systemd/homenetiq-kali-agent.service`, uncomment these two lines:
   ```
   CapabilityBoundingSet=CAP_NET_ADMIN
   AmbientCapabilities=CAP_NET_ADMIN
   ```
3. Reload the service.

This way the agent can run `iw` without being root.

## 7. Running as a systemd service

Edit the unit file, then:

```bash
sudo cp systemd/homenetiq-kali-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now homenetiq-kali-agent
sudo systemctl status homenetiq-kali-agent --no-pager
```

Log:

```bash
sudo journalctl -u homenetiq-kali-agent -f
```

## 8. Backend connectivity check

The agent POSTs to the backend on every tick. If the connection is
down, the agent writes an error to stderr and waits
`retry_delay_seconds`. To test:

```bash
# Backend down — run the agent with --once:
make kali-once
# Output: {"ok": false, "error": "..."}, exit 1

# Backend up:
make kali-once
# Output: {"ok": true, "backend_response": {"metric_id": ..., ...}}
```

## 9. Verification

On the Pi:

```bash
curl http://127.0.0.1:8080/api/v1/devices
# The Kali device_id should appear
```

On the dashboard:

- The **Devices** page shows the Kali device.
- The **Wi-Fi Metrics** page shows RSSI/SNR charts.
- The **Overview** page shows `Last Sample: "X seconds ago"`.

## 10. Common errors

See `docs/TROUBLESHOOTING.md`.

- **Backend connection refused:** wrong backend host/port; check firewall.
- **401 Unauthorized:** token mismatch; must match `HOMENETIQ_API_TOKEN` on the backend host.
- **`Operation not permitted`:** add CAP_NET_ADMIN or run as root
  temporarily.
- **Wi-Fi interface not found:** check `iw dev` output; if needed,
  set the interface name explicitly instead of `auto`.

> 🇹🇷 Türkçe: [docs/tr/SETUP_KALI_AGENT.tr.md](tr/SETUP_KALI_AGENT.tr.md)
