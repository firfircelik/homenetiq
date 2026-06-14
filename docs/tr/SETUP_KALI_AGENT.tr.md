# Kali Linux Wi-Fi Agent Kurulumu (Türkçe)

> 🇬🇧 English: [docs/SETUP_KALI_AGENT.md](../SETUP_KALI_AGENT.md)

> ⚠️ Bu agent **sadece kendi ağında, kendi cihazından** telemetry
> toplar. Başka ağları taramaz/saldırmaz.

## 1. Önkoşullar

- Kali Linux 2024+ veya Debian tabanlı herhangi bir Linux
- Python 3.11 veya 3.12
- `iw` paketi (Kali'de default kurulu)
- Aktif Wi-Fi bağlantısı (`iw dev` ile test et)
- Backend çalışıyor ve LAN'dan erişilebilir

## 2. Repo klonlama

```bash
git clone https://github.com/<user>/HomeNetIQ.git ~/homenetiq
cd ~/homenetiq
```

> systemd unit'i şablondur. `User=`, `WorkingDirectory=`, `ExecStart=`
> satırlarını düzenle.

## 3. Sanal ortam

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

Bkz. İngilizce dokümandaki alan tablosu.

## 5. İlk manuel çalıştırma

```bash
make kali-once
```

Olası hatalar:

- `Operation not permitted` (iw): root veya `CAP_NET_ADMIN` gerekli.
- `Wi-Fi interface bulunamadı`: wireless adaptör yok veya down.

## 6. Root / CAP_NET_ADMIN

İki seçenek:

- **A:** `User=root` (basit ama riskli).
- **B (önerilen):** Unit'te
  `CapabilityBoundingSet=CAP_NET_ADMIN` ve
  `AmbientCapabilities=CAP_NET_ADMIN` aktif et.

## 7. systemd

```bash
sudo cp systemd/homenetiq-kali-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now homenetiq-kali-agent
sudo systemctl status homenetiq-kali-agent --no-pager
```

## 8. Backend bağlantı kontrolü

```bash
# Backend kapalıyken
make kali-once
# {"ok": false, "error": "..."}, exit 1

# Backend açıkken
make kali-once
# {"ok": true, "backend_response": {...}}
```

## 9. Doğrulama

Pi tarafında:

```bash
curl http://127.0.0.1:8080/api/v1/devices
# Kali device_id görünmeli
```

## 10. Sık karşılaşılan hatalar

- Backend connection refused: Pi IP/port yanlış, firewall kontrolü.
- 401 Unauthorized: token uyuşmuyor.
- `Operation not permitted`: CAP_NET_ADMIN gerekli.
- Wi-Fi interface not found: `iw dev` çıktısını kontrol et.

Detaylar: `docs/tr/TROUBLESHOOTING.tr.md`.
