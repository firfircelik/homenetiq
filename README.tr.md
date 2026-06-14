# HomeNetIQ v1.0.0 (Türkçe)

> 🇬🇧 English documentation: [README.md](README.md)

HomeNetIQ, ev ağı ve Wi-Fi bağlantı kalitesini ölçen self-hosted bir
network intelligence projesidir. Sadece kendi cihazından ve kendi
ağından telemetry toplar; **Wi-Fi hacking, komşu ağ taraması veya
saldırı aracı değildir**.

## Mimari

- **Raspberry Pi** — Backend API + SQLite database + network probe
- **Kali Linux MacBook Air** — Wi-Fi probe
- **TP-Link TL-WR850N** — Lab AP
- **Opsiyonel Mac mini** — ikinci probe veya geliştirme cihazı

> Tüm komutlar **repo kök dizininden** (`HomeNetIQ_v1/`) çalıştırılır.
> Sadece `pip install` ve `python -m venv` adımları backend venv'i için
> `backend/` altında yapılır.

## Hızlı Kurulum

### 1. API Token Üret

```bash
openssl rand -hex 32
```

> `change-me-local-token` değeri yalnızca README ve örnek konfig
> dosyalarında geçer. Üretimde **kullanma**.

### 2. Raspberry Pi Backend

```bash
cp config/backend.env.example backend/.env
# backend/.env içinde HOMENETIQ_API_TOKEN değiştir
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
uvicorn backend.app.main:app --host 0.0.0.0 --port 8080
```

### 3. Pi Network Probe

```bash
cp config/pi_probe.yaml.example config/pi_probe.yaml
# targets bölümünü düzenle
python3 probes/pi_network_probe.py --config config/pi_probe.yaml --once
```

### 4. Kali Wi-Fi Agent

```bash
cp config/kali_agent.yaml.example config/kali_agent.yaml
# targets ve backend URL düzenle
python3 collectors/kali_wifi_agent.py --config config/kali_agent.yaml --once
```

> `iw` root veya `CAP_NET_ADMIN` gerektirebilir. systemd service
> kurulumunda `AmbientCapabilities=CAP_NET_ADMIN` ekle.

### 5. Dashboard

```bash
export HOMENETIQ_BACKEND_URL="http://192.168.1.50:8080"
export HOMENETIQ_API_TOKEN="<yukarıda ürettiğin token>"
streamlit run dashboard/streamlit_app.py
```

`http://localhost:8501` adresinde açılır.

## systemd

`systemd/` dizinindeki 3 unit'i cihazına göre düzenle
(`User=`, `WorkingDirectory=`, `ExecStart=`, `EnvironmentFile=`).
Kali service için `iw` çalıştıracaksa capability satırları gerekli.

```bash
sudo cp systemd/homenetiq-backend.service   /etc/systemd/system/
sudo cp systemd/homenetiq-pi-probe.service  /etc/systemd/system/
sudo cp systemd/homenetiq-kali-agent.service /etc/systemd/system/   # Kali'de
sudo systemctl daemon-reload
sudo systemctl enable --now homenetiq-backend
sudo systemctl enable --now homenetiq-pi-probe
sudo systemctl enable --now homenetiq-kali-agent   # Kali'de
```

## Testler

```bash
make install
make test                    # 91 test
```

## Güvenlik & Privacy

Bu proje sadece kendi ev/lab ağında kullanılmalıdır. BSSID/MAC adresleri
ham gönderilmiyor; `redact` (varsayılan) veya `hash` modu.

## Bu araç ne değildir?

- ❌ Wi-Fi hacking veya saldırı aracı değildir.
- ❌ Komşu ağ tarama/saldırı yapmaz.
- ❌ ISP hız garantisi veren bir araç değildir.
- ❌ Profesyonel RF survey tool yerine geçmez.
- ❌ Bulut servisi değildir.

## Sınırlamalar (v1, honest)

- **ClickHouse** opsiyonel; v1 runtime'da kullanılmıyor.
- **OpenWrt / router management** v1'de yok.
- **Browser probe** v1'de yok (metric_type tanımlı, agent yok).
- **ML tabanlı anomaly** v1'de yok; rule-based.
- **Lisans:** MIT — [LICENSE](LICENSE) dosyasına bak.

## Daha fazla (Türkçe)

- Mimari: [docs/tr/ARCHITECTURE.tr.md](docs/tr/ARCHITECTURE.tr.md)
- Kalite motoru: [docs/tr/QUALITY_ENGINE.tr.md](docs/tr/QUALITY_ENGINE.tr.md)
- Agent'lar: [docs/tr/AGENTS.tr.md](docs/tr/AGENTS.tr.md)
- Payload sözleşmesi: [docs/tr/METRIC_CONTRACT.tr.md](docs/tr/METRIC_CONTRACT.tr.md)
- Dashboard: [docs/tr/DASHBOARD.tr.md](docs/tr/DASHBOARD.tr.md)
- Pi kurulum: [docs/tr/SETUP_RASPBERRY_PI.tr.md](docs/tr/SETUP_RASPBERRY_PI.tr.md)
- Kali kurulum: [docs/tr/SETUP_KALI_AGENT.tr.md](docs/tr/SETUP_KALI_AGENT.tr.md)
- macOS kurulum: [docs/tr/SETUP_MACOS_AGENT.tr.md](docs/tr/SETUP_MACOS_AGENT.tr.md)
- Sorun giderme: [docs/tr/TROUBLESHOOTING.tr.md](docs/tr/TROUBLESHOOTING.tr.md)
