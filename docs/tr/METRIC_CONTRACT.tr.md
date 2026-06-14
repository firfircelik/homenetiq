# Metric Payload Sözleşmesi — v1.0 (Türkçe)

> 🇬🇧 English: [docs/METRIC_CONTRACT.md](../METRIC_CONTRACT.md)

`POST /api/v1/metrics` body'si (JSON) — alanlar, tipler ve kurallar
İngilizce dokümandakiyle aynıdır. Burada özet:

## Üst seviye alanlar

| Alan | Tip | Zorunlu |
|---|---|---|
| `device_id` | string (≥2) | evet |
| `device_type` | string | evet |
| `metric_type` | string | evet |
| `payload` | object | evet |
| `device_name` | string | hayır |
| `os` | string | hayır |
| `agent_version` | string | hayır (varsayılan `"1.0.0"`) |
| `collected_at` | ISO-8601 string | hayır |

## Wi-Fi payload (canonical)

ssid, bssid_redacted veya bssid_hash, frequency_mhz, band (canonical:
`2.4GHz` / `5GHz` / `6GHz`), channel, channel_width_mhz, rssi, noise,
snr, tx_rate_mbps, rx_rate_mbps, mcs_index, phy_mode, security.

> BSSID **ham haliyle gönderilmez**.

## Network payload (canonical)

gateway_ip, ap_ip, internet_ip, gateway_latency_ms, ap_latency_ms,
internet_latency_ms, dns_latency_ms, packet_loss_percent, jitter_ms.

## Alias desteği

| Canonical | Eski alias |
|---|---|
| `rssi` | `signal` |
| `packet_loss_percent` | `packet_loss` |

## agent_version

Tüm agent'lar payload'a `agent_version` ekler (`agents/version.py`'de
tanımlı). Şu an `"1.0.0"`.
