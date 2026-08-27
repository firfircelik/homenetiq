# Raspberry Pi Kurulumu (Türkçe)

> 🇬🇧 English: [docs/SETUP_RASPBERRY_PI.md](../SETUP_RASPBERRY_PI.md)

## 1. Önkoşullar

- Raspberry Pi OS Bookworm veya benzeri
- Python 3.11 veya 3.12
- İnternet erişimi (ilk pip install için)
- LAN'da sabit IP veya DHCP reservation (ör. `YOUR_BACKEND_HOST`)
- Boş port 8080 (backend) ve 8501 (dashboard)

## 2. Kullanıcı ve dizin

```bash
sudo useradd -m -s /bin/bash pi    # Pi OS'da zaten var
sudo -iu pi
git clone https://github.com/<user>/HomeNetIQ.git /home/YOUR_USER/homenetiq
cd /home/YOUR_USER/homenetiq
```

> systemd unit'leri şablondur. Önce `User=`, `WorkingDirectory=`,
> `ExecStart=`, `EnvironmentFile=` satırlarını düzenle.

## 3. Sanal ortam

```bash
cd /home/YOUR_USER/homenetiq
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## 4. Backend .env

```bash
cp config/backend.env.example backend/.env
nano backend/.env
```

```
HOMENETIQ_DB_PATH=/home/YOUR_USER/homenetiq/data/homenetiq.sqlite3
HOMENETIQ_API_TOKEN=<openssl rand -hex 32>
HOMENETIQ_REQUIRE_AUTH=true
HOMENETIQ_STALE_AFTER_SECONDS=120
HOMENETIQ_OFFLINE_AFTER_SECONDS=600
```

## 5. İlk manuel çalıştırma

```bash
make install
make test                    # 91 test
HOMENETIQ_API_TOKEN=test-tok bash scripts/run_backend_dev.sh
```

Sağlık kontrolü:

```bash
curl http://127.0.0.1:8080/health
```

## 6. Pi Network Probe

```bash
cp config/pi_probe.yaml.example config/pi_probe.yaml
nano config/pi_probe.yaml
# targets bölümünü düzenle
make pi-probe-once
```

## 7. systemd

Unit dosyalarını düzenle, sonra:

```bash
sudo cp systemd/homenetiq-backend.service  /etc/systemd/system/
sudo cp systemd/homenetiq-pi-probe.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now homenetiq-backend
sudo systemctl enable --now homenetiq-pi-probe
sudo systemctl status homenetiq-backend --no-pager
```

## 8. Dashboard'u LAN'a aç (opsiyonel)

```bash
HOMENETIQ_BACKEND_URL=http://YOUR_BACKEND_HOST:8080 \
nohup .venv/bin/streamlit run dashboard/streamlit_app.py \
  --server.address 0.0.0.0 --server.port 8501 \
  > logs/dashboard.log 2>&1 &
```

## 9. Health check

```bash
curl -s http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/api/v1/devices
curl -s http://127.0.0.1:8080/api/v1/metrics/latest?limit=5
curl -s http://127.0.0.1:8080/api/v1/summary
```

## 10. Sık karşılaşılan hatalar

Bkz. `docs/tr/TROUBLESHOOTING.tr.md`.

## 11. Yükseltme

```bash
cd /home/YOUR_USER/homenetiq
git pull
source .venv/bin/activate
pip install -r backend/requirements.txt
sudo systemctl restart homenetiq-backend
sudo systemctl restart homenetiq-pi-probe
```
