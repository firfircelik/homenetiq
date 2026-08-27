# macOS Wi-Fi Agent Setup

This document describes how to install the HomeNetIQ Wi-Fi agent on a
macOS host (or any other Mac). **It only collects telemetry from
your own device on your own network.**

## 1. Prerequisites

- macOS 12+ (Monterey or later)
- Python 3.11 or 3.12 (Homebrew or python.org installer)
- An active Wi-Fi connection
- `system_profiler` (preinstalled at `/usr/sbin/system_profiler`)
- The backend running and reachable on the network

## 2. Clone the repo

```bash
git clone https://github.com/<user>/HomeNetIQ.git ~/homenetiq
cd ~/homenetiq
```

## 3. Virtualenv

```bash
cd ~/homenetiq
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

> macOS 14+ (Sonoma) ships Python 3.13; if you have 3.14, see the note
> at the top of `backend/requirements.txt`.

## 4. Config

```bash
cp config/macos_agent.yaml.example config/macos_agent.yaml
nano config/macos_agent.yaml
```

Fields to edit (same schema as the Kali agent):

| Field | Example |
|---|---|
| `device.id` | `"macos-wifi-1"` |
| `device.name` | `"macOS Wi-Fi probe"` |
| `backend.url` | `"http://YOUR_BACKEND_HOST:8080/api/v1/metrics"` |
| `backend.token` | The `HOMENETIQ_API_TOKEN` from the Pi |
| `privacy.mode` | `"redact"` (recommended) |
| `targets.gateway_ip` | Router LAN IP |
| `targets.ap_ip` | AP IP |
| `targets.internet_ip` | `1.1.1.1` |

## 5. First manual run

```bash
make macos-once
```

Expected: a JSON output with `ok: true` and a `metric_id` from the
backend.

Possible errors:

- **`No SSID found`:** Wi-Fi is off or not connected.
- **`system_profiler` error:** may require root (rare).

## 6. Continuous operation

Two options:

### Option A: terminal / tmux (simple, for development)

```bash
# Lower the interval in config (e.g. 30s)
source .venv/bin/activate
python3 collectors/macos_wifi_agent.py --config config/macos_agent.yaml
# Ctrl+C to stop
```

### Option B: launchd (recommended)

> A launchd plist example is **not** in the repo for v1; the snippet
> below is reference only. In production write your own plist and put
> it under `~/Library/LaunchAgents/`.

Example plist (`~/Library/LaunchAgents/com.homenetiq.macos-agent.plist`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.homenetiq.macos-agent</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/<USER>/homenetiq/.venv/bin/python</string>
    <string>/Users/<USER>/homenetiq/collectors/macos_wifi_agent.py</string>
    <string>--config</string>
    <string>/Users/<USER>/homenetiq/config/macos_agent.yaml</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/<USER>/homenetiq</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/<USER>/homenetiq/logs/macos-agent.log</string>
  <key>StandardErrorPath</key><string>/Users/<USER>/homenetiq/logs/macos-agent.err</string>
</dict>
</plist>
```

Load:

```bash
mkdir -p ~/homenetiq/logs
launchctl load ~/Library/LaunchAgents/com.homenetiq.macos-agent.plist
launchctl list | grep homenetiq
launchctl unload ~/Library/LaunchAgents/com.homenetiq.macos-agent.plist  # stop
```

Replace `<USER>`, `<homenetiq>` etc. with your own values.

## 7. Verification

On the Pi:

```bash
curl http://127.0.0.1:8080/api/v1/devices
# The macOS device_id should appear
```

On the dashboard:

- The **Devices** page shows the macOS device.
- The **Wi-Fi Metrics** page shows measurements from macOS.

## 8. Known limitations (v1)

- **BSSID:** `system_profiler SPAirPortDataType` does not expose the
  raw BSSID. The macOS agent therefore does not produce
  `bssid_redacted`/`bssid_hash`; it works with SSID/channel/signal/noise
  only. For richer Wi-Fi info, v2 may integrate `airport -I` (not an
  offensive tool, just connection information).
- **launchd plist:** not in the repo for v1; reference only.

## 9. Common errors

See `docs/TROUBLESHOOTING.md`.

- **Backend connection refused:** wrong Pi IP/port; check the macOS
  firewall.
- **401 Unauthorized:** token mismatch; must match the Pi's `.env`.
- **No SSID found:** Wi-Fi is off or not connected; check the menu bar.

> 🇹🇷 Türkçe: [docs/tr/SETUP_MACOS_AGENT.tr.md](tr/SETUP_MACOS_AGENT.tr.md)
