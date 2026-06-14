# HomeNetIQ Agent'lar (Türkçe)

> 🇬🇧 English: [docs/AGENTS.md](../AGENTS.md)

## Amaç

HomeNetIQ, kullanıcının **kendi cihazlarından** ve **kendi ağından**
telemetry toplar. Agent'lar:

- Başka ağları tarama/saldırı yapmaz.
- Komşu ağlara deauth/sniff yapmaz.
- Şifre deneme veya test amaçlı olmayan herhangi bir etkinlik YAPMAZ.
- Sadece izin verilen hedeflere (gateway, AP, internet, DNS) ping atar.

## Agent listesi

| Agent | Konum | OS | Tipik Kullanım |
|---|---|---|---|
| Kali/Linux Wi-Fi agent | `collectors/kali_wifi_agent.py` | Linux (Kali, Raspbian) | `iw` ile Wi-Fi telemetry |
| macOS Wi-Fi agent | `collectors/macos_wifi_agent.py` | macOS | `system_profiler` ile Wi-Fi telemetry |
| Pi/Linux Network Probe | `probes/pi_network_probe.py` | Linux (Pi vb.) | Ağ gecikmeleri ve DNS |

## Ortak altyapı

`agents/` paketi:

- `agents/config_loader.py` — YAML config + doğrulama
- `agents/http_client.py` — POST + retry/backoff
- `agents/ping.py` — Cross-platform `ping` parser
- `agents/privacy.py` — BSSID redact/hash
- `agents/time_utils.py` — ISO-8601 UTC
- `agents/version.py` — `AGENT_PROTOCOL_VERSION`

## Privacy

BSSID/MAC **hiçbir zaman** ham gönderilmez.

- `redact` (varsayılan): son 2 oktet (`...:44:55`).
- `hash`: SHA-256 ilk 12 hex; opsiyonel `privacy.salt`.
- **Sabit salt YOK.**

Sadece kullanıcının kendi ağına bağlıyken kendi cihazından telemetry
toplanır.

## Yeni agent geliştirme

1. `agents/` ortak modüllerini kullan.
2. Canonical payload üret (`docs/METRIC_CONTRACT.md`).
3. `agent_version` ekle.
4. **Saf fonksiyonlar** yaz; test edilebilir olmalı.
5. `collect_and_send` ve `main` `try/except` ile sarmala; `--once`
   modunda hata olursa `exit 1`.
6. Yeni agent için: `collectors/<ad>.py` veya `probes/<ad>.py`,
   `config/<ad>.yaml.example`, `tests/test_<ad>.py`.

## Çalıştırma

```bash
python3 collectors/kali_wifi_agent.py --config config/kali_agent.yaml --once
python3 collectors/macos_wifi_agent.py --config config/macos_agent.yaml --once
python3 probes/pi_network_probe.py --config config/pi_probe.yaml --once
```

## Testler

```bash
pytest tests/ -v
```
