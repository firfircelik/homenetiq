# HomeNetIQ v1 Mimari (Türkçe)

> 🇬🇧 English: [docs/ARCHITECTURE.md](../ARCHITECTURE.md)

## Amaç

Ev ağında Wi-Fi ve internet deneyimini ölçmek, sorunu sınıflandırmak ve
anlaşılır rapor üretmek.

## Bileşenler

| Bileşen | Konum | Sorumluluk |
|---|---|---|
| Backend (FastAPI) | `backend/app/` | HTTP API + SQLite storage. `init_db()` uygulama başlangıcında `lifespan` ile çalışır. |
| Quality modülü | `backend/app/quality.py` | `classify_quality()` — payload'dan kural tabanlı good/warning/poor + 0-100 skor + issue listesi + explanations |
| Root Cause modülü | `backend/app/root_cause.py` | `classify_root_cause()` — issue listesinden kök neden etiketi |
| Recommendations | `backend/app/recommendations.py` | `recommend()` — insan-okunabilir, uygulanabilir öneri listesi |
| Kali Wi-Fi Agent | `collectors/kali_wifi_agent.py` | `iw` + `ping` ile Wi-Fi ve ağ metrikleri |
| Pi Network Probe | `probes/pi_network_probe.py` | Gateway/AP/internet ping + DNS latency |
| macOS Wi-Fi Agent | `collectors/macos_wifi_agent.py` | `system_profiler` parser (macOS) |
| Dashboard | `dashboard/streamlit_app.py` | Streamlit UI; backend'in GET uçlarını çağırır |
| SQLite DB | `backend/app/database.py` | `devices` + `metrics` tabloları, indeksler |
| systemd unit'ler | `systemd/*.service` | 3 servis: backend, pi-probe, kali-agent |
| Opsiyonel ClickHouse | `database/clickhouse_schema.sql` | v1'de runtime'da kullanılmıyor; referans şema |

## Veri akışı

```
[Kali agent]  ─┐
[macOS agent] ─┼─► POST /api/v1/metrics ─► FastAPI endpoint
[Pi probe]    ─┘                              │
                                             ▼
                              quality.classify_quality()
                              root_cause.classify_root_cause()
                              recommendations.recommend()
                                             │
                                             ▼
                              SQLite (devices, metrics)
                                             ▲
                                             │
                       [Streamlit dashboard] │  GET /api/v1/*
                       (HOMENETIQ_BACKEND_URL)
```

> **Not:** Quality ve Root Cause ayrı servisler değildir; backend
> içinde `POST /api/v1/metrics` endpoint'i tarafından her istekte sırayla
> çağrılan saf fonksiyonlardır. Bu sayede açıklanabilir (explainable),
> deterministik ve kolay test edilebilir kalırlar.

## API yüzeyi

GET `/health` kimlik doğrulamasızdır. Diğer GET veri uçları
`HOMENETIQ_REQUIRE_GET_AUTH=true` (varsayılan) iken Bearer ister.
`POST /api/v1/metrics` her zaman token ister. `/api/v1/mesh/pubkey`
API token veya `HOMENETIQ_ENROLL_TOKEN` ister.

| Method | Path | Auth |
|---|---|---|
| GET  | `/health` | - |
| POST | `/api/v1/metrics` | Bearer token |
| GET  | `/api/v1/metrics/latest` | Bearer (varsayılan) |
| GET  | `/api/v1/devices` | Bearer (varsayılan) |
| GET  | `/api/v1/devices/{device_id}/latest` | Bearer (varsayılan) |
| GET  | `/api/v1/summary` | Bearer (varsayılan) |
| GET  | `/api/v1/anomalies` | Bearer (varsayılan) |
| GET  | `/api/v1/mesh/pubkey` | Bearer veya enroll token |

Backend'i public internete açmayın. LAN için uvicorn `127.0.0.1` dinlesin,
önüne Caddy koyun (`contrib/Caddyfile`).
