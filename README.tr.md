# HomeNetIQ (Türkçe)

> 🇬🇧 English documentation: [README.md](README.md)

HomeNetIQ, **senin** ağının kalitesini ölçen self-hosted bir panodur.
Varsayılan router, Pi veya AP yoktur: `make init` ile token üretir,
`targets` alanlarını sen doldurursun.

İsteğe bağlı: [meshlink](https://github.com/firfircelik/network-project)
mesh VPN sağlığı. HomeNetIQ mesh'i **izler**, meshlink mesh'i **işletir**.

## Hızlı kurulum

```bash
make init
set -a && source backend/.env && set +a
make install
make run-backend   # 127.0.0.1:8080, GET auth açık
```

## Mimari

Kendi ağını bağla. Tipik roller (donanım serbest):

- **Backend** — FastAPI + SQLite (herhangi bir Linux)
- **Wi-Fi probe** — Linux (`iw`) ve/veya macOS
- **Ağ probe** — gateway / AP / internet gecikmesi (backend ile aynı makine olabilir)
- **Senin router ve AP** — `targets` sen doldurursun

> Tüm komutlar **repo kökünden** çalıştırılır.
> `pip install` ve `python -m venv` backend sanal ortamında yapılır.

## Hızlı Kurulum (detay)

İngilizce README'deki `make init` akışını izleyin. Raspberry Pi zorunlu
değildir. API `127.0.0.1` dinler; LAN için `contrib/Caddyfile`.

### 3. Ağ probe (isteğe bağlı host)

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
export HOMENETIQ_BACKEND_URL="http://YOUR_BACKEND_HOST:8080"
export HOMENETIQ_API_TOKEN="<yukarıda ürettiğin token>"
streamlit run dashboard/streamlit_app.py
```

`http://localhost:8501` adresinde açılır.

### 6. Opsiyonel: Mesh VPN izleme (meshlink)

[meshlink](https://github.com/firfircelik/network-project) şifreli
P2P mesh'inin sağlığını da izlemek istersen — tünel yolu (direct/relay),
RTT, rekey ve peer durumu aynı dashboard'da:

```bash
./scripts/install.sh          # meshlink binary + config + systemd kurulumu
sudo systemctl enable --now homenetiq-mesh-agent

# veya tam yığını tek komutla (backend + dashboard dahil):
./scripts/run-all.sh          # Dashboard: http://localhost:8501
```

#### Diğer cihazdan katılma (tek komut)

İkinci cihazda (aynı LAN) anahtar kopyalamaya gerek yok:

```bash
./scripts/join.sh YOUR_COORDINATOR_HOST linux   # <host-ip> [isim]
```

Pinli coordinator public key'ini host backend'inden kendisi çeker ve
mesh agent'ı otomatik başlatır.

Bildirimler: `HOMENETIQ_NOTIFY_URL=https://ntfy.sh/<kanal>` ile mesh olayları
(peer down/up, path değişimi) telefonuna düşer; ⚙️ Settings sayfasından canlı
düzenlenebilir. Gerçek overlay trafik: `sudo ./scripts/tun-pair.sh server|client`.
Detay: `docs/MESH_INTEGRATION.md`.

## systemd

`systemd/` dizinindeki 4 unit'i cihazına göre düzenle
(`User=`, `WorkingDirectory=`, `ExecStart=`, `EnvironmentFile=`).
Kali service için `iw` çalıştıracaksa capability satırları gerekli.
(`scripts/install.sh` bu alanları otomatik doldurur.)

```bash
sudo cp systemd/homenetiq-backend.service   /etc/systemd/system/
sudo cp systemd/homenetiq-pi-probe.service  /etc/systemd/system/
sudo cp systemd/homenetiq-kali-agent.service /etc/systemd/system/   # Kali'de
sudo cp systemd/homenetiq-mesh-agent.service /etc/systemd/system/  # mesh host'ta
sudo systemctl daemon-reload
sudo systemctl enable --now homenetiq-backend
sudo systemctl enable --now homenetiq-pi-probe
sudo systemctl enable --now homenetiq-kali-agent   # Kali'de
sudo systemctl enable --now homenetiq-mesh-agent   # mesh host'ta
```

## Testler

```bash
make install
make test                    # 100 test
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
