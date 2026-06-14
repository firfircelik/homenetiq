# HomeNetIQ — Quality Engine

This document describes how the v1 quality score, issue detection, root
cause classification, and recommendation generation work. All rules
live under `backend/app/`:

| Module | Responsibility |
|---|---|
| `thresholds.py` | All threshold values in one dataclass |
| `quality.py` | Payload → quality, issues, quality_score, explanations |
| `root_cause.py` | Issue list → root cause label |
| `recommendations.py` | Issues + root cause → human-readable recommendations |

## 1. How the score is computed

`classify_quality(metric_type, payload)` returns a 4-tuple:

- `quality`: `"good"` (80-100), `"warning"` (50-79), `"poor"` (0-49)
- `issues`: machine-readable code list
- `quality_score`: 0-100 integer
- `explanations`: short human-readable reason for each issue

Start: 100 points. Each detected issue subtracts a specific penalty
(e.g. `weak_signal` -25, `low_snr` -15). When multiple "severe" issues
accumulate, a cumulative penalty applies:

| Severe issue count | Extra penalty |
|---|---|
| 1 | 0 |
| 2 | -5 |
| 3+ | -10 |

The score is then clamped to `[0, 100]` and mapped to a category.

## 2. Issue codes

Payload fields that can trigger an issue:

| Code | Trigger | Default penalty |
|---|---|---|
| `weak_signal` | `rssi`/`signal` < -75 dBm | -25 |
| `low_snr` | `snr` < 15 dB | -15 |
| `low_tx_rate` | `tx_rate_mbps` < 50 | -10 |
| `low_rx_rate` | `rx_rate_mbps` < 50 | -8 |
| `low_local_throughput` | `local_throughput_mbps` < 20 | -8 |
| `using_2ghz_band` | band is 2.4 GHz | -5 |
| `packet_loss` | `packet_loss_percent`/`packet_loss` > 5% | -25 (high), -10 (warning) |
| `high_jitter` | `jitter_ms` > 30 (warning: 10) | -10 / -4 |
| `high_gateway_latency` | `gateway_latency_ms` > 30 | -12 |
| `high_ap_latency` | `ap_latency_ms` > 30 | -10 |
| `ap_unreachable` | `ap_latency_ms` > 60 | -30 |
| `high_internet_latency` | `internet_latency_ms` > 100 (very high: 150) | -12 / -25 |
| `slow_dns` | `dns_latency_ms` > 200 | -10 |
| `internet_unreachable` | packet_loss = 100% | -40 |

## 3. Root cause list

`classify_root_cause(metric_type, payload, issues)` returns one of:

| Root cause | Meaning |
|---|---|
| `healthy` | No issues |
| `wifi_signal_issue` | Signal strength / RSSI / SNR is low |
| `wifi_congestion_issue` | Signal is fine but SNR is low, or 2.4 GHz + packet loss |
| `local_ap_issue` | AP latency is high or AP is unreachable |
| `gateway_or_lan_issue` | Gateway latency is high (LAN/modem side) |
| `wan_or_isp_issue` | Only internet latency is high |
| `dns_issue` | Only DNS is slow, nothing else is bad |
| `single_device_issue` | Signal is fine but packet loss is present; isolated to this device |
| `probe_or_backend_issue` | Both AP and internet are unreachable; probe or backend side |
| `unknown_issue` | None of the above matches |

Order matters: the most specific condition is checked first.

## 4. Recommendation logic

`recommend(issues, root_cause)` produces recommendations from a static
dictionary. The root-cause tip comes first, followed by per-issue tips.
The output is deduped.

Examples:

- `weak_signal` + `wifi_signal_issue` →
  - "The issue is Wi-Fi signal strength. Optimize AP placement or channel."
  - "The device may be too far from the access point. Move the probe closer to the AP and re-test, or reposition the AP."
- `high_internet_latency` + `wan_or_isp_issue` →
  - "The local network looks fine; latency may be on the WAN/ISP side. Contact your ISP."
- `slow_dns` + `dns_issue` →
  - "The issue is on the DNS side. Try a different resolver or check DNS settings on the modem."

## 5. Payload field mapping

The engine accepts the following aliases:

| Logical field | Accepted payload keys |
|---|---|
| RSSI | `rssi`, `signal` |
| Packet loss | `packet_loss_percent`, `packet_loss` |
| Band | `band` (any string; "2GHz", "2.4GHz", "2G" etc. are normalized) |

Unknown keys are ignored; this way agents can send new fields without
breaking the API.

## 6. Known limitations (v1)

- **Single device, single snapshot:** the engine evaluates a single
  payload in isolation. It does not see trends (e.g. "RSSI has been
  falling for 5 minutes").
- **Score/category boundary:** e.g. a single `slow_dns` issue subtracts
  only 10 points, so `quality` can still be "good" while the root cause
  is `dns_issue`. This is intentional: "good network, slightly slow
  DNS". v2 may refine category boundaries.
- **Recommendations are static:** not personalised for the installation
  or device.
- **No cross-payload correlation:** metrics from multiple devices are
  not compared.
- **Thresholds are hard-coded:** in a frozen `Thresholds` dataclass.
  Not yet overridable via YAML/env (deliberately out of v1 scope).

## 7. API contract (backwards compatible)

`POST /api/v1/metrics` response:

```json
{
  "status": "stored",
  "metric_id": 42,
  "device_id": "kali-1",
  "quality": "poor",
  "quality_score": 38,
  "issues": ["weak_signal", "low_snr"],
  "root_cause": "wifi_signal_issue",
  "explanations": ["RSSI -80 dBm below threshold (-75 dBm)", "SNR 8 dB below threshold (15 dB)"],
  "recommendations": [
    "The issue is Wi-Fi signal strength. Optimize AP placement or channel.",
    "The device may be too far from the access point. Move the probe closer to the AP and re-test, or reposition the AP.",
    "Signal-to-noise ratio is low. There may be local interference (microwave, Bluetooth) or channel conflict; try changing the AP channel."
  ]
}
```

Old clients can ignore `quality_score`, `explanations`, and
`recommendations`. `quality`, `issues`, and `root_cause` continue to
be returned as before.

## 8. Test summary

- `tests/test_quality.py` — old tests, updated to the new 4-tuple signature.
- `tests/test_quality_engine.py` — new: score, normalize, alias,
  recommendation, 9 scenarios + 3 helper unit tests.

> 🇹🇷 Türkçe: [docs/tr/QUALITY_ENGINE.tr.md](tr/QUALITY_ENGINE.tr.md)
