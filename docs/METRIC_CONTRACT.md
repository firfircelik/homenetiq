# Metric Payload Contract — v1.0

This document defines the standard format of the metric payload sent
from any agent to the backend. The backend accepts payloads that match
this contract; non-conforming payloads are rejected with HTTP 422.

## 1. Top-level fields

Body of `POST /api/v1/metrics` (JSON):

| Field | Type | Required | Description |
|---|---|---|---|
| `device_id` | string (≥2) | yes | Persistent device identifier (e.g. `"kali-macbook-air"`) |
| `device_type` | string | yes | `"wifi_probe"`, `"network_probe"`, `"browser_probe"` |
| `metric_type` | string | yes | `"wifi"`, `"network"`, `"dns"`, `"channel_scan"` |
| `payload` | object | yes | Metric-specific fields (below) |
| `device_name` | string | no | Display name |
| `os` | string | no | `"linux"`, `"kali-linux"`, `"macos"`, `"raspberry-pi-os"` |
| `agent_version` | string | no | Agent protocol version (default: `"1.0.0"`) |
| `collected_at` | ISO-8601 string | no | Collection time. If absent, the backend uses UTC now. |

## 2. Wi-Fi payload (canonical fields)

When `metric_type == "wifi"`, the `payload` should contain:

| Field | Type | Description |
|---|---|---|
| `ssid` | string | Network name |
| `bssid_redacted` | string | Last 2 octets (e.g. `"...:44:55"`), used when `privacy.mode == "redact"` |
| `bssid_hash` | string | SHA-256 first 12 hex chars, used when `privacy.mode == "hash"` |
| `frequency_mhz` | int | Center frequency |
| `band` | string | `"2.4GHz"`, `"5GHz"`, `"6GHz"`, `"unknown"` |
| `channel` | int | Channel number, 1-233 |
| `channel_width_mhz` | int | 20, 40, 80, 160, 320 |
| `rssi` | int | dBm |
| `noise` | int | dBm |
| `snr` | int | dB = `rssi - noise` |
| `tx_rate_mbps` | float | TX bitrate, Mbps |
| `rx_rate_mbps` | float | RX bitrate, Mbps |
| `mcs_index` | int | 0-11 |
| `phy_mode` | string | `"802.11n"`, `"802.11ac"`, `"802.11ax"` |
| `security` | string | `"WPA2 Personal"`, `"WPA3 Personal"` |

> The **raw BSSID is never sent**. Use `bssid_redacted` or
> `bssid_hash` per the privacy setting.

## 3. Network payload (canonical fields)

When `metric_type == "network"`:

| Field | Type | Description |
|---|---|---|
| `gateway_ip` | string | Measured gateway IP |
| `ap_ip` | string | Measured AP IP |
| `internet_ip` | string | Measured internet target |
| `gateway_latency_ms` | float? | Gateway ping avg |
| `ap_latency_ms` | float? | AP ping avg |
| `internet_latency_ms` | float? | Internet ping avg |
| `dns_latency_ms` | float? | DNS average |
| `packet_loss_percent` | float | 0-100 (100 = unreachable) |
| `jitter_ms` | float? | ping stddev/mdev |

## 4. Alias support (backwards compatibility)

The backend accepts these aliases; new payloads should use the
**canonical fields**:

| Canonical | Legacy alias |
|---|---|
| `rssi` | `signal` |
| `packet_loss_percent` | `packet_loss` |

Legacy short forms for `band` (`"2GHz"`, `"2G"`, `"2.4"`) are accepted
by the backend; agents should use the canonical `"2.4GHz"` form.

## 5. agent_version

- All agents add `agent_version` to the payload.
- Current version: `"1.0.0"` (defined in `agents/version.py`).
- The backend uses this field for logging/analytics; it does not error
  on version mismatch (backwards compatibility).
- If a future version changes a field's name or meaning, a new
  `metric_type` should be introduced or this document updated.

## 6. Example Wi-Fi payload

```json
{
  "device_id": "kali-macbook-air",
  "device_name": "Kali MacBook Air 2015",
  "device_type": "wifi_probe",
  "os": "kali-linux",
  "agent_version": "1.0.0",
  "metric_type": "wifi",
  "collected_at": "2026-06-14T17:45:01.123456+00:00",
  "payload": {
    "ssid": "HomeNetIQ-Lab",
    "bssid_redacted": "...:44:55",
    "frequency_mhz": 5180,
    "band": "5GHz",
    "channel": 36,
    "channel_width_mhz": 80,
    "rssi": -47,
    "noise": -95,
    "snr": 48,
    "tx_rate_mbps": 433.3,
    "rx_rate_mbps": 433.3,
    "mcs_index": 9,
    "phy_mode": "802.11ac",
    "security": "WPA2 Personal",
    "gateway_latency_ms": 1.2,
    "ap_latency_ms": 2.4,
    "internet_latency_ms": 18.5,
    "jitter_ms": 0.6,
    "packet_loss_percent": 0.0,
    "target_gateway_ip": "192.168.1.1",
    "target_ap_ip": "192.168.1.103",
    "target_internet_ip": "1.1.1.1",
    "interface": "wlan0"
  }
}
```

## 7. Example Network payload

```json
{
  "device_id": "raspberry-pi",
  "device_type": "network_probe",
  "os": "raspberry-pi-os",
  "agent_version": "1.0.0",
  "metric_type": "network",
  "collected_at": "2026-06-14T17:45:01.987654+00:00",
  "payload": {
    "gateway_ip": "192.168.1.1",
    "ap_ip": "192.168.1.103",
    "internet_ip": "1.1.1.1",
    "gateway_latency_ms": 1.1,
    "ap_latency_ms": 2.0,
    "internet_latency_ms": 19.2,
    "dns_latency_ms": 8.4,
    "jitter_ms": 0.5,
    "packet_loss_percent": 0.0
  }
}
```

> 🇹🇷 Türkçe: [docs/tr/METRIC_CONTRACT.tr.md](tr/METRIC_CONTRACT.tr.md)
