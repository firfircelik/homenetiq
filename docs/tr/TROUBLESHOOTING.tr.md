# Sorun Giderme (Türkçe)

> 🇬🇧 English: [docs/TROUBLESHOOTING.md](../TROUBLESHOOTING.md)

Sık karşılaşılan hatalar ve çözüm önerileri.

## Backend

### "Connection refused" / "Cannot reach backend"

Backend çalışmıyor veya farklı host:port'ta.

```bash
# Pi'de
sudo systemctl status homenetiq-backend
# veya manuel
.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8080
```

Dashboard tarafında `HOMENETIQ_BACKEND_URL` doğru mu?

```bash
export HOMENETIQ_BACKEND_URL="http://192.168.1.50:8080"
```

### 401 Unauthorized

`POST /api/v1/metrics` Bearer token gerekli.

```bash
curl -X POST http://127.0.0.1:8080/api/v1/metrics \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

Token uyuşmazlığı:

- `HOMENETIQ_API_TOKEN` (backend) ve `backend.token` (agent) aynı olmalı.
- Token değiştiyse tüm agent'ları güncelle.
- Test için `HOMENETIQ_REQUIRE_AUTH=false`.

### "no such table: devices"

DB init çalışmamış.

```bash
python3 -c "from backend.app.database import init_db; init_db()"
# DB bozuk ise yedekle ve sil
mv data/homenetiq.sqlite3 data/homenetiq.sqlite3.bak
```

### "Address already in use" (port 8080)

```bash
sudo lsof -i :8080
# veya farklı port kullan
HOMENETIQ_DB_PATH=... uvicorn backend.app.main:app --port 8081
```

## Agent'lar

### `iw` → "Operation not permitted"

`iw` root veya `CAP_NET_ADMIN` gerektirir.

- Geçici: `sudo` ile çalıştır.
- Kalıcı: systemd unit'te capability satırları.

### "Wi-Fi interface bulunamadı"

```bash
iw dev
ip link
```

Hiç Wi-Fi yoksa bu cihaz Wi-Fi probe olamaz. `auto` yerine interface
adını yaz.

### "SSID bulunamadı" (macOS)

Wi-Fi kapalı veya bağlı değil.

### "DNS yavaş"

Sorun cihazda değil, DNS resolver'da. `docs/tr/QUALITY_ENGINE.tr.md`
veya Dashboard **Recommendations** sayfasına bak.

### Backend connection refused (agent tarafı)

```bash
curl http://192.168.1.50:8080/health
```

Cevap yoksa Pi açık mı, firewall açık mı, IP doğru mu kontrol et.

Agent log'unda:

```
{"ok": false, "error": "Cannot reach backend..."}
```

Bu bir hata değil; agent doğru çalışıyor, backend erişilemiyor.
`retry_delay_seconds` sonra tekrar dener.

## Dashboard

### "No metrics received yet"

- Backend açık mı?
- Agent'lar çalışıyor mu?
- Token uyuşuyor mu?

### "Cannot reach backend: ..."

`HOMENETIQ_BACKEND_URL` doğru mu?

```bash
HOMENETIQ_BACKEND_URL=http://192.168.1.50:8080 \
  python3 -m streamlit run dashboard/streamlit_app.py
```

### Streamlit Python 3.14'te import hatası

Python 3.11 veya 3.12 kullan. `backend/requirements.txt` başlığına bak.

### Grafik boş / "No data yet for ..."

Payload'da o alan yok demektir. Beklenen, "No metrics received yet"
değil; sadece o alan eksik.

## systemd

### "Unit not found"

```bash
sudo systemctl daemon-reload
sudo systemctl list-unit-files | grep homenetiq
```

### Service başlamıyor, "status=203/EXEC"

`ExecStart` yolu yanlış. Kontrol:

```bash
ls -la /home/pi/homenetiq/.venv/bin/uvicorn
```

### "Permission denied" / .env okunamıyor

```bash
chmod 600 /home/pi/homenetiq/backend/.env
```

### Servis restart-loop

```bash
sudo journalctl -u homenetiq-backend -n 100 --no-pager
```

Elle çalıştır:

```bash
cd /home/pi/homenetiq
HOMENETIQ_API_TOKEN=test-tok python3 -m uvicorn backend.app.main:app
```

## Python / pip

### pydantic-core derleme hatası (Python 3.14)

Python 3.11 veya 3.12 kullan. `backend/requirements.txt` başlığına bak.

### "No module named 'streamlit'" (test sırasında)

```bash
pip install -r backend/requirements.txt
```
