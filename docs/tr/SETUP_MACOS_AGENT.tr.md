# macOS Wi-Fi Agent Kurulumu (Türkçe)

> 🇬🇧 English: [docs/SETUP_MACOS_AGENT.md](../SETUP_MACOS_AGENT.md)

## 1. Önkoşullar

- macOS 12+ (Monterey veya üstü)
- Python 3.11 veya 3.12 (Homebrew veya python.org installer)
- Aktif Wi-Fi bağlantısı
- `system_profiler` (default kurulu)
- Backend çalışıyor ve erişilebilir

## 2. Repo klonlama

```bash
git clone https://github.com/<user>/HomeNetIQ.git ~/homenetiq
cd ~/homenetiq
```

## 3. Sanal ortam

```bash
cd ~/homenetiq
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## 4. Config

```bash
cp config/macos_agent.yaml.example config/macos_agent.yaml
nano config/macos_agent.yaml
```

## 5. İlk manuel çalıştırma

```bash
make macos-once
```

## 6. Sürekli çalıştırma

İki seçenek:

- **A:** terminal / tmux
- **B (önerilen):** launchd

launchd plist örneği İngilizce `docs/SETUP_MACOS_AGENT.md` içinde var
(bu repoda yok). Kendi yaz, `~/Library/LaunchAgents/` altına koy.

## 7. Doğrulama

```bash
curl http://127.0.0.1:8080/api/v1/devices
# macOS device_id görünmeli
```

## 8. Bilinen sınırlamalar (v1)

- **BSSID:** `system_profiler` ham BSSID vermez. v2'de `airport -I` düşünülebilir.
- **launchd plist:** repoda yok; kendi yaz.

## 9. Sık karşılaşılan hatalar

- Backend connection refused: Pi IP/port yanlış, macOS firewall.
- 401 Unauthorized: token uyuşmuyor.
- SSID bulunamadı: Wi-Fi kapalı.

Detaylar: `docs/tr/TROUBLESHOOTING.tr.md`.
