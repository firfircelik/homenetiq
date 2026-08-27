**HomeNetIQ**

**Tüm Kodlar, Mantık, Mimari ve Çalıştırma Rehberi**

_Self-hosted backend + Wi-Fi probe + your own access point_

Hazırlanma tarihi: 11.06.2026

**Kısa özet:** HomeNetIQ, ev ağındaki Wi-Fi ve internet bağlantısını ölçen, metrikleri Raspberry Pi üzerinde çalışan backend'e toplayan, kalite skoru ve kök neden sınıflandırması yapan açık kaynak bir home network intelligence projesidir.

# İçindekiler

- 1\. Projenin amacı ve ürün mantığı
- 2\. Cihaz rolleri ve ağ topolojisi
- 3\. Modüller ve hangi kod nerede çalışacak
- 4\. Dosya yapısı
- 5\. Raspberry Pi backend kurulumu ve kodları
- 6\. Kali Linux Wi-Fi probe/collector kodları
- 7\. Raspberry Pi network probe kodları
- 8\. Kalite skoru ve root cause engine
- 9\. Streamlit dashboard kodları
- 10\. Servis olarak çalıştırma
- 11\. Test planı, QA ve hata ayıklama
- 12\. Veritabanı, DBA notları ve büyütme planı
- 13\. Roadmap ve sonraki sürümler

# 1\. Projenin Amacı ve Ürün Mantığı

HomeNetIQ'nin amacı sadece Wi-Fi sinyal gücünü ölçmek değildir. Asıl amaç, ev ağındaki bağlantı deneyimini uçtan uca ölçmek ve "problem nerede?" sorusuna veriyle cevap vermektir.

**Ürün fikri:** Kullanıcı "internetim yavaş" dediğinde sistem Wi-Fi sinyali mi, kanal kalabalığı mı, DNS mi, router mı, yoksa ISP/WAN tarafı mı problemli bunu ayırmaya çalışır.

| **Alan**      | **Ne Ölçülür?**                                 | **Neden Önemli?**                                               |
| ------------- | ----------------------------------------------- | --------------------------------------------------------------- |
| Wi-Fi link    | RSSI, signal, bitrate, band, channel, BSSID     | Cihazın access point ile kablosuz bağlantı kalitesini gösterir. |
| Local network | AP latency, gateway latency, packet loss        | Ev içi ağda sorun var mı anlamaya yarar.                        |
| Internet/WAN  | 1.1.1.1 ping, DNS latency, internet packet loss | ISP veya upstream problem ayrımı için kullanılır.               |
| Cihaz sağlığı | last_seen, device_type, probe status            | Collector cihazları aktif mi, veri taze mi kontrol edilir.      |
| Analiz        | quality score, issues, root cause               | Ham metrikleri anlaşılır teşhis sonucuna çevirir.               |

# 2\. Cihaz Rolleri ve Ağ Topolojisi

Bu projede cihazların rolleri net ayrılır. Karmaşayı azaltmak için her cihazın tek ana görevi vardır.

| **Cihaz**                     | **Rol**                             | **Nerede?**         | **Görevi**                                                                     |
| ----------------------------- | ----------------------------------- | ------------------- | ------------------------------------------------------------------------------ |
| Ana modem/router              | Gateway                             | YOUR_GATEWAY_IP         | İnternet çıkışı ve ana ağ geçidi.                                              |
| your access point          | Lab Access Point                    | YOUR_AP_IP       | YOUR_SSID Wi-Fi ağını yayınlar. DHCP kapalı kalır.                         |
| Raspberry Pi                  | Backend + network probe             | Ethernet            | FastAPI backend, SQLite DB, network ölçümleri, dashboard.                      |
| Linux Wi-Fi probe | Wi-Fi probe                         | Wi-Fi               | Wi-Fi ağına bağlanır, Wi-Fi metriklerini toplar ve Pi backend'e gönderir.    |
| macOS host                      | Opsiyonel probe / geliştirme cihazı | Wi-Fi veya ethernet | İkinci probe, dashboard client veya geliştirme makinesi olarak kullanılabilir. |

**Ağ topolojisi**

Ana Modem / Gateway: YOUR_GATEWAY_IP

|

| Ethernet

v

your access point: YOUR_AP_IP

SSID: YOUR_SSID, DHCP: Kapalı

|

| Wi-Fi

v

Linux Wi-Fi probe Wi-Fi Probe

|

| HTTP POST /api/v1/metrics

v

Raspberry Pi HomeNetIQ Backend

FastAPI + SQLite + Quality Engine + Dashboard

## Neden Raspberry Pi var?

Tek bir laptop ile de ölçüm yapılabilir. Ancak Raspberry Pi projeyi "tek cihazda çalışan script" olmaktan çıkarıp gerçek bir telemetry backend mimarisine yaklaştırır.

| **Sebep**      | **Açıklama**                                                                          |
| -------------- | ------------------------------------------------------------------------------------- |
| Ayrım          | Wi-Fi probe ölçüm yapar; Pi backend/veritabanı olarak ayrı kalır.                     |
| Süreklilik     | Pi düşük enerjiyle 7/24 açık kalabilir.                                               |
| Referans ölçüm | Pi ethernet ile bağlı olduğu için Wi-Fi'dan etkilenmeyen kablolu referans noktasıdır. |
| Gerçek mimari  | Collector -> HTTP API -> backend -> database -> dashboard akışı oluşur.               |

# 3\. Modüller ve Hangi Kod Nerede Çalışacak

| **Modül**            | **Çalışacağı Yer**          | **Dil/Teknoloji**   | **Görev**                                                                               |
| -------------------- | --------------------------- | ------------------- | --------------------------------------------------------------------------------------- |
| Backend API          | Raspberry Pi                | Python + FastAPI    | Metrik kabul eder, cihazları kaydeder, DB'ye yazar, summary/anomaly endpointleri sunar. |
| SQLite DB            | Raspberry Pi                | SQLite              | Cihaz ve metrik kayıtlarını tutar.                                                      |
| Quality Engine       | Raspberry Pi backend içinde | Python              | Payload'a göre quality, issues ve root_cause üretir.                                    |
| Kali Wi-Fi Collector | Linux Wi-Fi probe            | Python + iw + ping  | Wi-Fi metrikleri, latency ve packet loss toplar; backend'e gönderir.                    |
| Pi Network Probe     | Raspberry Pi                | Python + ping + dig | Gateway/AP/internet/DNS ölçümleri yapar ve backend'e gönderir.                          |
| Dashboard            | Raspberry Pi veya macOS host  | Streamlit           | Son metrikleri, cihazları, trendleri ve anomalileri gösterir.                           |
| systemd servisleri   | Raspberry Pi ve Kali        | Linux systemd       | Backend ve collector'ların otomatik başlamasını sağlar.                                 |

# 4\. Dosya Yapısı

**Önerilen repo yapısı**

homenetiq/

├── README.md

├── .env.example

├── config/

│ ├── backend.env

│ ├── kali-agent.yaml

│ └── pi-probe.yaml

├── backend/

│ ├── requirements.txt

│ └── app/

│ ├── \__init_\_.py

│ ├── main.py

│ ├── models.py

│ ├── storage.py

│ ├── quality.py

│ └── settings.py

├── collectors/

│ ├── kali_wifi_collector.py

│ └── pi_network_probe.py

├── dashboard/

│ ├── requirements.txt

│ └── streamlit_app.py

├── database/

│ └── schema.sql

├── systemd/

│ ├── homenetiq-backend.service

│ ├── homenetiq-kali-agent.service

│ └── homenetiq-pi-probe.service

├── scripts/

│ ├── test_post_metric.sh

│ └── run_local_backend.sh

└── docs/

├── architecture.md

├── api.md

└── test-plan.md

# 5\. Raspberry Pi Backend Kurulumu ve Kodları

## 5.1. Raspberry Pi üzerinde kurulum

**Raspberry Pi kurulum komutları**

\# Raspberry Pi üzerinde çalıştırılacak

sudo apt update

sudo apt install -y python3 python3-venv python3-pip sqlite3 git

mkdir -p ~/homenetiq/backend/app

cd ~/homenetiq/backend

python3 -m venv .venv

source .venv/bin/activate

pip install fastapi uvicorn pydantic pydantic-settings python-dotenv

## 5.2. backend/requirements.txt

fastapi==0.115.6

uvicorn\[standard\]==0.34.0

pydantic==2.10.4

pydantic-settings==2.7.0

python-dotenv==1.0.1

## 5.3. backend/app/settings.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):

\# Backend'in dinleyeceği host/port

app_host: str = "0.0.0.0"

app_port: int = 8080

\# SQLite DB dosyası

database_path: str = "./homenetiq.db"

\# Basit API güvenliği için token.

\# İlk geliştirmede boş bırakılabilir ama servis haline getirirken doldurulmalı.

api_token: str = "dev-token-change-me"

\# Cihaz durum eşikleri

stale_after_seconds: int = 120

offline_after_seconds: int = 600

class Config:

env_file = ".env"

settings = Settings()

## 5.4. backend/app/models.py

from datetime import datetime, timezone

from typing import Any, Optional

from pydantic import BaseModel, Field

class MetricIn(BaseModel):

"""Her cihazdan gelen generic metric payload modeli.

Bu modeli generic tuttuk çünkü Kali, macOS, Raspberry Pi veya ileride

OpenWrt farklı payload gönderebilir. Ortak alanlar device_id, metric_type

ve payload'dur.

"""

device_id: str = Field(..., examples=\["linux-wifi-1"\])

device_name: Optional\[str\] = Field(None, examples=\["Linux Wi-Fi probe"\])

device_type: str = Field(..., examples=\["wifi_probe"\])

os: Optional\[str\] = Field(None, examples=\["kali-linux"\])

metric_type: str = Field(..., examples=\["wifi", "network", "dns"\])

collected_at: Optional\[datetime\] = None

payload: dict\[str, Any\]

class MetricStored(BaseModel):

id: int

device_id: str

metric_type: str

collected_at: datetime

payload: dict\[str, Any\]

quality: str

issues: list\[str\]

root_cause: str

class DeviceOut(BaseModel):

device_id: str

device_name: Optional\[str\]

device_type: str

os: Optional\[str\]

first_seen: datetime

last_seen: datetime

status: str

## 5.5. backend/app/quality.py

from typing import Any

def classify_quality(metric_type: str, payload: dict\[str, Any\]) -> tuple\[str, list\[str\], str\]:

"""Metrikten kalite, issue listesi ve kök neden üretir.

İlk sürümde ML kullanmıyoruz. Açıklanabilir rule-based yaklaşım kullanıyoruz.

Bu daha doğru çünkü kullanıcıya "neden kötü" sorusunun cevabını verebiliriz.

"""

issues: list\[str\] = \[\]

\# Ortak ağ metrikleri

packet_loss = \_to_float(payload.get("packet_loss_percent") or payload.get("packet_loss"))

internet_latency = \_to_float(payload.get("internet_latency_ms"))

gateway_latency = \_to_float(payload.get("gateway_latency_ms"))

ap_latency = \_to_float(payload.get("ap_latency_ms"))

dns_latency = \_to_float(payload.get("dns_latency_ms"))

jitter = \_to_float(payload.get("jitter_ms"))

if packet_loss is not None:

if packet_loss >= 5:

issues.append("packet_loss_critical")

elif packet_loss >= 2:

issues.append("packet_loss_warning")

if internet_latency is not None and internet_latency > 100:

issues.append("high_internet_latency")

if gateway_latency is not None and gateway_latency > 30:

issues.append("high_gateway_latency")

if ap_latency is not None and ap_latency > 30:

issues.append("high_ap_latency")

if dns_latency is not None and dns_latency > 150:

issues.append("slow_dns")

if jitter is not None and jitter > 30:

issues.append("high_jitter")

\# Wi-Fi özel metrikler

rssi = \_to_float(payload.get("rssi"))

snr = \_to_float(payload.get("snr"))

tx_rate = \_to_float(payload.get("tx_rate_mbps"))

band = str(payload.get("band") or "").lower()

if rssi is not None:

if rssi <= -80:

issues.append("very_weak_signal")

elif rssi <= -75:

issues.append("weak_signal")

if snr is not None:

if snr < 10:

issues.append("very_low_snr")

elif snr < 15:

issues.append("low_snr")

if tx_rate is not None and tx_rate < 50:

issues.append("low_tx_rate")

if band in {"2ghz", "2g", "2.4ghz"}:

\# Bu tek başına problem değildir; sadece bilgi amaçlı düşük ağırlıklı issue.

issues.append("using_2ghz_band")

root_cause = classify_root_cause(payload, issues)

serious = \[i for i in issues if i not in {"using_2ghz_band"}\]

if not serious:

quality = "good"

elif len(serious) <= 2:

quality = "warning"

else:

quality = "poor"

return quality, issues, root_cause

def classify_root_cause(payload: dict\[str, Any\], issues: list\[str\]) -> str:

"""Basit kök neden sınıflandırması."""

if "slow_dns" in issues:

return "dns_issue"

if "high_ap_latency" in issues or "high_gateway_latency" in issues:

return "local_network_or_ap_issue"

if "packet_loss_critical" in issues or "packet_loss_warning" in issues:

gw = \_to_float(payload.get("gateway_latency_ms"))

inet = \_to_float(payload.get("internet_latency_ms"))

if gw is not None and inet is not None and gw &lt; 30 and inet &gt; 100:

return "wan_or_isp_issue"

return "packet_loss_issue"

wifi_issues = {"very_weak_signal", "weak_signal", "very_low_snr", "low_snr", "low_tx_rate"}

if any(i in wifi_issues for i in issues):

if "low_snr" in issues or "very_low_snr" in issues:

return "wifi_noise_or_interference_issue"

return "wifi_signal_issue"

if "high_internet_latency" in issues:

return "wan_or_isp_issue"

return "healthy_or_unknown"

def \_to_float(value: Any) -> float | None:

if value is None:

return None

try:

return float(value)

except (TypeError, ValueError):

return None

## 5.6. backend/app/storage.py

import json

import sqlite3

from datetime import datetime, timezone

from pathlib import Path

from typing import Any

from .settings import settings

def get_conn() -> sqlite3.Connection:

conn = sqlite3.connect(settings.database_path)

conn.row_factory = sqlite3.Row

return conn

def init_db() -> None:

Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)

conn = get_conn()

cur = conn.cursor()

cur.execute(

"""

CREATE TABLE IF NOT EXISTS devices (

device_id TEXT PRIMARY KEY,

device_name TEXT,

device_type TEXT NOT NULL,

os TEXT,

first_seen TEXT NOT NULL,

last_seen TEXT NOT NULL

)

"""

)

cur.execute(

"""

CREATE TABLE IF NOT EXISTS metrics (

id INTEGER PRIMARY KEY AUTOINCREMENT,

device_id TEXT NOT NULL,

metric_type TEXT NOT NULL,

collected_at TEXT NOT NULL,

payload_json TEXT NOT NULL,

quality TEXT NOT NULL,

issues_json TEXT NOT NULL,

root_cause TEXT NOT NULL,

created_at TEXT NOT NULL,

FOREIGN KEY(device_id) REFERENCES devices(device_id)

)

"""

)

cur.execute("CREATE INDEX IF NOT EXISTS idx_metrics_device_time ON metrics(device_id, collected_at DESC)")

cur.execute("CREATE INDEX IF NOT EXISTS idx_metrics_type_time ON metrics(metric_type, collected_at DESC)")

cur.execute("CREATE INDEX IF NOT EXISTS idx_metrics_quality_time ON metrics(quality, collected_at DESC)")

conn.commit()

conn.close()

def upsert_device(device_id: str, device_name: str | None, device_type: str, os: str | None) -> None:

now = datetime.now(timezone.utc).isoformat()

conn = get_conn()

cur = conn.cursor()

cur.execute("SELECT device_id FROM devices WHERE device_id = ?", (device_id,))

exists = cur.fetchone()

if exists:

cur.execute(

"""

UPDATE devices

SET device_name = COALESCE(?, device_name),

device_type = ?,

os = COALESCE(?, os),

last_seen = ?

WHERE device_id = ?

""",

(device_name, device_type, os, now, device_id),

)

else:

cur.execute(

"""

INSERT INTO devices (device_id, device_name, device_type, os, first_seen, last_seen)

VALUES (?, ?, ?, ?, ?, ?)

""",

(device_id, device_name, device_type, os, now, now),

)

conn.commit()

conn.close()

def insert_metric(

device_id: str,

metric_type: str,

collected_at: datetime,

payload: dict\[str, Any\],

quality: str,

issues: list\[str\],

root_cause: str,

) -> int:

now = datetime.now(timezone.utc).isoformat()

conn = get_conn()

cur = conn.cursor()

cur.execute(

"""

INSERT INTO metrics (

device_id, metric_type, collected_at, payload_json,

quality, issues_json, root_cause, created_at

)

VALUES (?, ?, ?, ?, ?, ?, ?, ?)

""",

(

device_id,

metric_type,

collected_at.isoformat(),

json.dumps(payload, ensure_ascii=False),

quality,

json.dumps(issues, ensure_ascii=False),

root_cause,

now,

),

)

metric_id = int(cur.lastrowid)

conn.commit()

conn.close()

return metric_id

def list_devices() -> list\[dict\[str, Any\]\]:

conn = get_conn()

rows = conn.execute("SELECT \* FROM devices ORDER BY last_seen DESC").fetchall()

conn.close()

return \[dict(r) for r in rows\]

def latest_metrics(limit: int = 50) -> list\[dict\[str, Any\]\]:

conn = get_conn()

rows = conn.execute(

"""

SELECT \* FROM metrics

ORDER BY collected_at DESC

LIMIT ?

""",

(limit,),

).fetchall()

conn.close()

return \[\_metric_row_to_dict(r) for r in rows\]

def latest_metric_for_device(device_id: str) -> dict\[str, Any\] | None:

conn = get_conn()

row = conn.execute(

"""

SELECT \* FROM metrics

WHERE device_id = ?

ORDER BY collected_at DESC

LIMIT 1

""",

(device_id,),

).fetchone()

conn.close()

return \_metric_row_to_dict(row) if row else None

def anomaly_metrics(limit: int = 50) -> list\[dict\[str, Any\]\]:

conn = get_conn()

rows = conn.execute(

"""

SELECT \* FROM metrics

WHERE quality IN ('warning', 'poor')

ORDER BY collected_at DESC

LIMIT ?

""",

(limit,),

).fetchall()

conn.close()

return \[\_metric_row_to_dict(r) for r in rows\]

def \_metric_row_to_dict(row: sqlite3.Row) -> dict\[str, Any\]:

d = dict(row)

d\["payload"\] = json.loads(d.pop("payload_json"))

d\["issues"\] = json.loads(d.pop("issues_json"))

return d

## 5.7. backend/app/main.py

from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException

from .models import MetricIn

from .quality import classify_quality

from .settings import settings

from .storage import (

init_db,

upsert_device,

insert_metric,

list_devices,

latest_metrics,

latest_metric_for_device,

anomaly_metrics,

)

app = FastAPI(title="HomeNetIQ Backend", version="0.1.0")

@app.on_event("startup")

def on_startup() -> None:

init_db()

def check_token(authorization: str | None) -> None:

"""Basit token kontrolü.

Geliştirme sırasında dev-token kullanılabilir.

Production veya ev ağı dışı kullanımda token mutlaka değiştirilmelidir.

"""

if not settings.api_token:

return

expected = f"Bearer {settings.api_token}"

if authorization != expected:

raise HTTPException(status_code=401, detail="Invalid or missing API token")

@app.get("/health")

def health() -> dict:

return {"status": "ok", "service": "homenetiq-backend"}

@app.post("/api/v1/metrics")

def ingest_metric(metric: MetricIn, authorization: str | None = Header(default=None)) -> dict:

check_token(authorization)

collected_at = metric.collected_at or datetime.now(timezone.utc)

quality, issues, root_cause = classify_quality(metric.metric_type, metric.payload)

upsert_device(

device_id=metric.device_id,

device_name=metric.device_name,

device_type=metric.device_type,

os=metric.os,

)

metric_id = insert_metric(

device_id=metric.device_id,

metric_type=metric.metric_type,

collected_at=collected_at,

payload=metric.payload,

quality=quality,

issues=issues,

root_cause=root_cause,

)

return {

"status": "stored",

"metric_id": metric_id,

"device_id": metric.device_id,

"quality": quality,

"issues": issues,

"root_cause": root_cause,

}

@app.get("/api/v1/devices")

def get_devices() -> dict:

return {"devices": list_devices()}

@app.get("/api/v1/devices/{device_id}/latest")

def get_device_latest(device_id: str) -> dict:

metric = latest_metric_for_device(device_id)

if not metric:

raise HTTPException(status_code=404, detail="Device metric not found")

return {"metric": metric}

@app.get("/api/v1/metrics/latest")

def get_latest_metrics(limit: int = 50) -> dict:

limit = min(max(limit, 1), 500)

return {"metrics": latest_metrics(limit)}

@app.get("/api/v1/anomalies")

def get_anomalies(limit: int = 50) -> dict:

limit = min(max(limit, 1), 500)

return {"anomalies": anomaly_metrics(limit)}

## 5.8. Backend çalıştırma

\# Raspberry Pi üzerinde

cd ~/homenetiq/backend

source .venv/bin/activate

\# .env dosyası oluştur

cat > .env <<'EOF'

APP_HOST=0.0.0.0

APP_PORT=8080

DATABASE_PATH=/home/YOUR_USER/homenetiq/backend/homenetiq.db

API_TOKEN=dev-token-change-me

EOF

uvicorn app.main:app --host 0.0.0.0 --port 8080

**Backend test komutu**

\# Başka cihazdan test

curl http://RASPBERRY_PI_IP:8080/health

# 6\. Kali Linux Wi-Fi Probe/Collector Kodları

## 6.1. Kali üzerinde gerekli paketler

\# Linux Wi-Fi probe üzerinde

sudo apt update

sudo apt install -y python3 python3-venv python3-pip wireless-tools iw iproute2 iputils-ping dnsutils

mkdir -p ~/homenetiq/collectors

cd ~/homenetiq

python3 -m venv .venv

source .venv/bin/activate

pip install requests pyyaml

## 6.2. Wi-Fi interface adını bulma

\# Kali üzerinde çalıştır

ip link

iw dev

\# Örnek interface isimleri:

\# wlan0

\# wlp2s0

\# wlp3s0

## 6.3. config/kali-agent.yaml

device:

id: "linux-wifi-1"

name: "Linux Wi-Fi probe"

type: "wifi_probe"

os: "kali-linux"

backend:

url: "http://RASPBERRY_PI_IP:8080/api/v1/metrics"

token: "dev-token-change-me"

collector:

interface: "wlan0"

interval_seconds: 30

targets:

gateway_ip: "YOUR_GATEWAY_IP"

ap_ip: "YOUR_AP_IP"

internet_ip: "1.1.1.1"

## 6.4. collectors/kali_wifi_collector.py

import re

import subprocess

import time

from datetime import datetime, timezone

from pathlib import Path

from typing import Any

import requests

import yaml

CONFIG_PATH = Path.home() / "homenetiq" / "config" / "kali-agent.yaml"

def run_cmd(command: list\[str\], timeout: int = 10) -> str:

result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)

if result.returncode != 0:

return result.stdout + result.stderr

return result.stdout

def load_config() -> dict\[str, Any\]:

with open(CONFIG_PATH, "r", encoding="utf-8") as f:

return yaml.safe_load(f)

def parse_iw_link(output: str) -> dict\[str, Any\]:

"""iw dev &lt;iface&gt; link çıktısını parse eder.

Beklenen örnek:

Connected to aa:bb:cc:dd:ee:ff (on wlan0)

SSID: YOUR_SSID

freq: 2437

signal: -61 dBm

tx bitrate: 144.4 MBit/s

rx bitrate: 72.2 MBit/s

"""

payload: dict\[str, Any\] = {}

if "Not connected" in output:

payload\["connected"\] = False

return payload

payload\["connected"\] = True

m = re.search(r"Connected to\\s+(\[0-9a-fA-F:\]+)", output)

if m:

payload\["bssid"\] = m.group(1).lower()

m = re.search(r"SSID:\\s\*(.+)", output)

if m:

payload\["ssid"\] = m.group(1).strip()

m = re.search(r"freq:\\s\*(\\d+)", output)

if m:

freq = int(m.group(1))

payload\["frequency_mhz"\] = freq

payload\["band"\] = frequency_to_band(freq)

payload\["channel"\] = frequency_to_channel(freq)

m = re.search(r"signal:\\s\*(-?\\d+)\\s\*dBm", output)

if m:

payload\["rssi"\] = int(m.group(1))

m = re.search(r"tx bitrate:\\s\*(\[0-9.\]+)\\s\*MBit/s", output)

if m:

payload\["tx_rate_mbps"\] = float(m.group(1))

m = re.search(r"rx bitrate:\\s\*(\[0-9.\]+)\\s\*MBit/s", output)

if m:

payload\["rx_rate_mbps"\] = float(m.group(1))

return payload

def frequency_to_band(freq_mhz: int) -> str:

if 2400 <= freq_mhz < 2500:

return "2GHz"

if 5000 <= freq_mhz < 5900:

return "5GHz"

if 5900 <= freq_mhz < 7200:

return "6GHz"

return "unknown"

def frequency_to_channel(freq_mhz: int) -> int | None:

\# 2.4 GHz approximate mapping

if 2412 <= freq_mhz <= 2472:

return int((freq_mhz - 2407) / 5)

if freq_mhz == 2484:

return 14

\# 5 GHz approximate mapping

if 5000 <= freq_mhz <= 5900:

return int((freq_mhz - 5000) / 5)

return None

def ping_stats(target: str, count: int = 5) -> dict\[str, float | None\]:

output = run_cmd(\["ping", "-c", str(count), target\], timeout=15)

loss = None

avg = None

min_v = None

max_v = None

jitter = None

m = re.search(r"(\\d+(?:\\.\\d+)?)% packet loss", output)

if m:

loss = float(m.group(1))

m = re.search(r"min/avg/max/(?:mdev|stddev) = (\[0-9.\]+)/(\[0-9.\]+)/(\[0-9.\]+)/(\[0-9.\]+)", output)

if m:

min_v = float(m.group(1))

avg = float(m.group(2))

max_v = float(m.group(3))

jitter = float(m.group(4))

return {

"latency_min_ms": min_v,

"latency_avg_ms": avg,

"latency_max_ms": max_v,

"jitter_ms": jitter,

"packet_loss_percent": loss,

}

def build_metric(config: dict\[str, Any\]) -> dict\[str, Any\]:

iface = config\["collector"\]\["interface"\]

targets = config\["targets"\]

iw_output = run_cmd(\["iw", "dev", iface, "link"\])

wifi = parse_iw_link(iw_output)

gateway = ping_stats(targets\["gateway_ip"\])

ap = ping_stats(targets\["ap_ip"\])

internet = ping_stats(targets\["internet_ip"\])

payload = {

\*\*wifi,

"gateway_ip": targets\["gateway_ip"\],

"ap_ip": targets\["ap_ip"\],

"internet_ip": targets\["internet_ip"\],

"gateway_latency_ms": gateway\["latency_avg_ms"\],

"gateway_packet_loss_percent": gateway\["packet_loss_percent"\],

"ap_latency_ms": ap\["latency_avg_ms"\],

"ap_packet_loss_percent": ap\["packet_loss_percent"\],

"internet_latency_ms": internet\["latency_avg_ms"\],

"internet_packet_loss_percent": internet\["packet_loss_percent"\],

"packet_loss_percent": internet\["packet_loss_percent"\],

"jitter_ms": internet\["jitter_ms"\],

}

return {

"device_id": config\["device"\]\["id"\],

"device_name": config\["device"\]\["name"\],

"device_type": config\["device"\]\["type"\],

"os": config\["device"\]\["os"\],

"metric_type": "wifi",

"collected_at": datetime.now(timezone.utc).isoformat(),

"payload": payload,

}

def post_metric(config: dict\[str, Any\], metric: dict\[str, Any\]) -> None:

headers = {

"Authorization": f"Bearer {config\['backend'\]\['token'\]}",

"Content-Type": "application/json",

}

response = requests.post(config\["backend"\]\["url"\], json=metric, headers=headers, timeout=10)

response.raise_for_status()

print(response.json())

def main() -> None:

config = load_config()

interval = int(config\["collector"\].get("interval_seconds", 30))

while True:

try:

metric = build_metric(config)

post_metric(config, metric)

except Exception as exc:

print(f"collector_error: {exc}")

time.sleep(interval)

if \_\_name\_\_ == "\__main_\_":

main()

## 6.5. Kali collector tek seferlik test

\# Kali üzerinde

mkdir -p ~/homenetiq/config ~/homenetiq/collectors

\# config/kali-agent.yaml dosyasını oluşturduktan sonra:

cd ~/homenetiq

source .venv/bin/activate

python collectors/kali_wifi_collector.py

# 7\. Raspberry Pi Network Probe Kodları

Bu probe kablolu referans ölçüm noktasıdır: gateway, AP, internet ve DNS.

## 7.1. config/pi-probe.yaml

device:

id: "raspberry-pi"

name: "Raspberry Pi Backend Probe"

type: "network_probe"

os: "raspberry-pi-os"

backend:

url: "<http://127.0.0.1:8080/api/v1/metrics>"

token: "dev-token-change-me"

collector:

interval_seconds: 30

targets:

gateway_ip: "YOUR_GATEWAY_IP"

ap_ip: "YOUR_AP_IP"

internet_ip: "1.1.1.1"

dns_domain: "google.com"

## 7.2. collectors/pi_network_probe.py

import re

import subprocess

import time

from datetime import datetime, timezone

from pathlib import Path

from typing import Any

import requests

import yaml

CONFIG_PATH = Path.home() / "homenetiq" / "config" / "pi-probe.yaml"

def run_cmd(command: list\[str\], timeout: int = 10) -> str:

result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)

return result.stdout + result.stderr

def load_config() -> dict\[str, Any\]:

with open(CONFIG_PATH, "r", encoding="utf-8") as f:

return yaml.safe_load(f)

def ping_stats(target: str, count: int = 5) -> dict\[str, float | None\]:

output = run_cmd(\["ping", "-c", str(count), target\], timeout=15)

loss = None

avg = None

min_v = None

max_v = None

jitter = None

m = re.search(r"(\\d+(?:\\.\\d+)?)% packet loss", output)

if m:

loss = float(m.group(1))

m = re.search(r"min/avg/max/(?:mdev|stddev) = (\[0-9.\]+)/(\[0-9.\]+)/(\[0-9.\]+)/(\[0-9.\]+)", output)

if m:

min_v = float(m.group(1))

avg = float(m.group(2))

max_v = float(m.group(3))

jitter = float(m.group(4))

return {

"min_ms": min_v,

"avg_ms": avg,

"max_ms": max_v,

"jitter_ms": jitter,

"packet_loss_percent": loss,

}

def dns_latency(domain: str) -> float | None:

output = run_cmd(\["dig", domain\], timeout=10)

m = re.search(r"Query time:\\s\*(\\d+)\\s\*msec", output)

if m:

return float(m.group(1))

return None

def build_metric(config: dict\[str, Any\]) -> dict\[str, Any\]:

targets = config\["targets"\]

gateway = ping_stats(targets\["gateway_ip"\])

ap = ping_stats(targets\["ap_ip"\])

internet = ping_stats(targets\["internet_ip"\])

dns_ms = dns_latency(targets\["dns_domain"\])

payload = {

"gateway_ip": targets\["gateway_ip"\],

"ap_ip": targets\["ap_ip"\],

"internet_ip": targets\["internet_ip"\],

"dns_domain": targets\["dns_domain"\],

"gateway_latency_ms": gateway\["avg_ms"\],

"gateway_packet_loss_percent": gateway\["packet_loss_percent"\],

"ap_latency_ms": ap\["avg_ms"\],

"ap_packet_loss_percent": ap\["packet_loss_percent"\],

"internet_latency_ms": internet\["avg_ms"\],

"internet_packet_loss_percent": internet\["packet_loss_percent"\],

"packet_loss_percent": internet\["packet_loss_percent"\],

"jitter_ms": internet\["jitter_ms"\],

"dns_latency_ms": dns_ms,

}

return {

"device_id": config\["device"\]\["id"\],

"device_name": config\["device"\]\["name"\],

"device_type": config\["device"\]\["type"\],

"os": config\["device"\]\["os"\],

"metric_type": "network",

"collected_at": datetime.now(timezone.utc).isoformat(),

"payload": payload,

}

def post_metric(config: dict\[str, Any\], metric: dict\[str, Any\]) -> None:

headers = {

"Authorization": f"Bearer {config\['backend'\]\['token'\]}",

"Content-Type": "application/json",

}

response = requests.post(config\["backend"\]\["url"\], json=metric, headers=headers, timeout=10)

response.raise_for_status()

print(response.json())

def main() -> None:

config = load_config()

interval = int(config\["collector"\].get("interval_seconds", 30))

while True:

try:

metric = build_metric(config)

post_metric(config, metric)

except Exception as exc:

print(f"pi_probe_error: {exc}")

time.sleep(interval)

if \_\_name\_\_ == "\__main_\_":

main()

# 8\. Kalite Skoru ve Root Cause Engine Mantığı

| **Kural**                 | **Issue**             | **Yorum**                                               |
| ------------------------- | --------------------- | ------------------------------------------------------- |
| RSSI <= -75               | weak_signal           | Wi-Fi sinyali zayıflıyor. Mesafe/duvar etkisi olabilir. |
| SNR < 15                  | low_snr               | Gürültü/parazit yüksek veya sinyal-gürültü farkı düşük. |
| Tx rate < 50 Mbps         | low_tx_rate           | Kablosuz link hızı düşük.                               |
| Packet loss >= 2%         | packet_loss_warning   | Kullanıcı deneyimini bozabilecek paket kaybı var.       |
| Internet latency > 100 ms | high_internet_latency | WAN/ISP veya upstream problem olabilir.                 |
| DNS latency > 150 ms      | slow_dns              | Web siteleri geç açılıyor hissi verebilir.              |
| AP latency > 30 ms        | high_ap_latency       | AP tarafında local problem olabilir.                    |

**Neden rule-based?:** İlk sürümde ML kullanmak gereksiz karmaşıklık yaratır. Rule-based yaklaşım açıklanabilir, test edilebilir ve ürünün teşhis mantığını net gösterir.

# 9\. Streamlit Dashboard Kodları

## 9.1. dashboard/requirements.txt

streamlit==1.41.1

requests==2.32.3

pandas==2.2.3

## 9.2. dashboard/streamlit_app.py

import os

import requests

import pandas as pd

import streamlit as st

BACKEND_BASE_URL = os.getenv("HOMENETIQ_BACKEND", "<http://127.0.0.1:8080>")

st.set_page_config(page_title="HomeNetIQ", layout="wide")

st.title("HomeNetIQ - Ev Ağı Sağlık Paneli")

st.caption("Wi-Fi + broadband telemetry, quality scoring ve root cause classification")

def get_json(path: str) -> dict:

url = f"{BACKEND_BASE_URL}{path}"

response = requests.get(url, timeout=10)

response.raise_for_status()

return response.json()

try:

health = get_json("/health")

st.success(f"Backend aktif: {health\['status'\]}")

except Exception as exc:

st.error(f"Backend'e ulaşılamıyor: {exc}")

st.stop()

col1, col2 = st.columns(2)

with col1:

st.subheader("Cihazlar")

devices = get_json("/api/v1/devices")\["devices"\]

st.dataframe(pd.DataFrame(devices), use_container_width=True)

with col2:

st.subheader("Son Anomaliler")

anomalies = get_json("/api/v1/anomalies?limit=20")\["anomalies"\]

if anomalies:

anomaly_rows = \[\]

for m in anomalies:

anomaly_rows.append({

"time": m\["collected_at"\],

"device": m\["device_id"\],

"quality": m\["quality"\],

"root_cause": m\["root_cause"\],

"issues": ", ".join(m\["issues"\]),

})

st.dataframe(pd.DataFrame(anomaly_rows), use_container_width=True)

else:

st.info("Anomali yok.")

st.subheader("Son Metrikler")

metrics = get_json("/api/v1/metrics/latest?limit=200")\["metrics"\]

rows = \[\]

for m in metrics:

p = m\["payload"\]

rows.append({

"time": m\["collected_at"\],

"device": m\["device_id"\],

"type": m\["metric_type"\],

"quality": m\["quality"\],

"root_cause": m\["root_cause"\],

"rssi": p.get("rssi"),

"band": p.get("band"),

"tx_rate": p.get("tx_rate_mbps"),

"gateway_ms": p.get("gateway_latency_ms"),

"internet_ms": p.get("internet_latency_ms"),

"packet_loss": p.get("packet_loss_percent"),

"dns_ms": p.get("dns_latency_ms"),

"issues": ", ".join(m\["issues"\]),

})

df = pd.DataFrame(rows)

st.dataframe(df, use_container_width=True)

if not df.empty:

st.subheader("Trendler")

df\["time"\] = pd.to_datetime(df\["time"\], errors="coerce")

df = df.sort_values("time")

metric_options = \["rssi", "tx_rate", "gateway_ms", "internet_ms", "packet_loss", "dns_ms"\]

selected = st.selectbox("Grafik metriği", metric_options)

chart_df = df\[\["time", "device", selected\]\].dropna()

if not chart_df.empty:

pivot = chart_df.pivot_table(index="time", columns="device", values=selected, aggfunc="mean")

st.line_chart(pivot)

else:

st.info("Bu metrik için yeterli veri yok.")

## 9.3. Dashboard çalıştırma

\# Raspberry Pi veya macOS host üzerinde

cd ~/homenetiq/dashboard

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

export HOMENETIQ_BACKEND=http://RASPBERRY_PI_IP:8080

streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501

# 10\. Servis Olarak Çalıştırma

## 10.1. systemd/homenetiq-backend.service

\[Unit\]

Description=HomeNetIQ FastAPI Backend

After=network-online.target

Wants=network-online.target

\[Service\]

User=pi

WorkingDirectory=/home/YOUR_USER/homenetiq/backend

Environment="PATH=/home/YOUR_USER/homenetiq/backend/.venv/bin"

ExecStart=/home/YOUR_USER/homenetiq/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080

Restart=always

RestartSec=5

\[Install\]

WantedBy=multi-user.target

## 10.2. systemd/homenetiq-pi-probe.service

\[Unit\]

Description=HomeNetIQ Raspberry Pi Network Probe

After=homenetiq-backend.service

Wants=homenetiq-backend.service

\[Service\]

User=pi

WorkingDirectory=/home/YOUR_USER/homenetiq

Environment="PATH=/home/YOUR_USER/homenetiq/.venv/bin"

ExecStart=/home/YOUR_USER/homenetiq/.venv/bin/python /home/YOUR_USER/homenetiq/collectors/pi_network_probe.py

Restart=always

RestartSec=5

\[Install\]

WantedBy=multi-user.target

## 10.3. systemd/homenetiq-kali-agent.service

\[Unit\]

Description=HomeNetIQ Kali Wi-Fi Collector

After=network-online.target

Wants=network-online.target

\[Service\]

User=YOUR_USER

WorkingDirectory=/home/YOUR_USER/homenetiq

Environment="PATH=/home/YOUR_USER/homenetiq/.venv/bin"

ExecStart=/home/YOUR_USER/homenetiq/.venv/bin/python /home/YOUR_USER/homenetiq/collectors/kali_wifi_collector.py

Restart=always

RestartSec=5

\[Install\]

WantedBy=multi-user.target

## 10.4. Servisleri aktif etme

\# Raspberry Pi backend servisi

sudo cp systemd/homenetiq-backend.service /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable homenetiq-backend

sudo systemctl start homenetiq-backend

sudo systemctl status homenetiq-backend

\# Raspberry Pi probe servisi

sudo cp systemd/homenetiq-pi-probe.service /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable homenetiq-pi-probe

sudo systemctl start homenetiq-pi-probe

sudo systemctl status homenetiq-pi-probe

\# Kali üzerinde agent servisi

sudo cp systemd/homenetiq-kali-agent.service /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable homenetiq-kali-agent

sudo systemctl start homenetiq-kali-agent

sudo systemctl status homenetiq-kali-agent

# 11\. Test Planı, QA ve Hata Ayıklama

| **Test**              | **Komut / Aksiyon**           | **Beklenen Sonuç**                          |
| --------------------- | ----------------------------- | ------------------------------------------- |
| Backend health        | curl http://PI_IP:8080/health | status ok dönmeli.                          |
| Manuel metric POST    | scripts/test_post_metric.sh   | metric stored dönmeli.                      |
| Cihaz listesi         | GET /api/v1/devices           | linux-wifi-1 ve raspberry-pi görünmeli. |
| Son metrikler         | GET /api/v1/metrics/latest    | Payload ve quality alanları gelmeli.        |
| Kali Wi-Fi bağlantısı | iw dev wlan0 link             | Connected, SSID, signal, bitrate görünmeli. |
| AP ping               | ping YOUR_AP_IP            | 0% packet loss beklenir.                    |
| Gateway ping          | ping YOUR_GATEWAY_IP              | Düşük latency beklenir.                     |
| Internet ping         | ping 1.1.1.1                  | Internet erişimi doğrulanır.                |

## 11.1. scripts/test_post_metric.sh

# !/usr/bin/env bash

set -euo pipefail

BACKEND="\${BACKEND:-http://RASPBERRY_PI_IP:8080}"

TOKEN="\${TOKEN:-dev-token-change-me}"

curl -X POST "\$BACKEND/api/v1/metrics" -H "Authorization: Bearer \$TOKEN" -H "Content-Type: application/json" -d '{

"device_id": "manual-test-device",

"device_name": "Manual Test Device",

"device_type": "test_probe",

"os": "manual",

"metric_type": "wifi",

"payload": {

"ssid": "YOUR_SSID",

"band": "2GHz",

"rssi": -76,

"snr": 12,

"tx_rate_mbps": 39,

"internet_latency_ms": 28,

"packet_loss_percent": 0

}

}'

echo

## 11.2. Yaygın hatalar ve çözümler

| **Problem**            | **Muhtemel Sebep**                          | **Çözüm**                                        |
| ---------------------- | ------------------------------------------- | ------------------------------------------------ |
| 401 Invalid token      | Collector token ile backend .env farklı.    | API_TOKEN ve YAML token değerlerini eşitle.      |
| Kali Not connected     | Wi-Fi bağlantısı yok veya interface yanlış. | iw dev ile interface adını bul, YAML'da düzelt.  |
| Backend'e ulaşılamıyor | Pi IP yanlış, firewall, backend çalışmıyor. | curl /health, systemctl status, IP kontrolü yap. |
| DB dosyası oluşmuyor   | Path izni yok.                              | DATABASE_PATH yazılabilir bir dizine alın.       |
| Dashboard boş          | Metrik gelmiyor veya backend URL yanlış.    | GET /api/v1/metrics/latest ile kontrol et.       |

# 12\. Veritabanı, DBA Notları ve Büyütme Planı

MVP için SQLite yeterlidir. Çok cihaz ve uzun süreli veri toplanmaya başlanırsa PostgreSQL veya ClickHouse düşünülmelidir.

| **Aşama** | **DB**     | **Neden**                                                          |
| --------- | ---------- | ------------------------------------------------------------------ |
| MVP       | SQLite     | Kurulumu kolay, Raspberry Pi için hafif, tek dosya.                |
| v0.3+     | PostgreSQL | Daha güçlü sorgular, eşzamanlı erişim, dashboard için daha stabil. |
| v0.6+     | ClickHouse | Yüksek hacimli time-series/analytics sorguları için uygun.         |

## 12.1. database/schema.sql

CREATE TABLE IF NOT EXISTS devices (

device_id TEXT PRIMARY KEY,

device_name TEXT,

device_type TEXT NOT NULL,

os TEXT,

first_seen TEXT NOT NULL,

last_seen TEXT NOT NULL

);

CREATE TABLE IF NOT EXISTS metrics (

id INTEGER PRIMARY KEY AUTOINCREMENT,

device_id TEXT NOT NULL,

metric_type TEXT NOT NULL,

collected_at TEXT NOT NULL,

payload_json TEXT NOT NULL,

quality TEXT NOT NULL,

issues_json TEXT NOT NULL,

root_cause TEXT NOT NULL,

created_at TEXT NOT NULL,

FOREIGN KEY(device_id) REFERENCES devices(device_id)

);

CREATE INDEX IF NOT EXISTS idx_metrics_device_time

ON metrics(device_id, collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_type_time

ON metrics(metric_type, collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_quality_time

ON metrics(quality, collected_at DESC);

## 12.2. ClickHouse ileri aşama şeması

CREATE TABLE wifi_metrics

(

collected_at DateTime,

device_id String,

device_type String,

ssid String,

bssid String,

band String,

channel UInt16,

frequency_mhz UInt16,

rssi Int16,

snr Int16,

tx_rate_mbps Float32,

rx_rate_mbps Float32,

gateway_latency_ms Float32,

internet_latency_ms Float32,

packet_loss_percent Float32,

quality String,

root_cause String

)

ENGINE = MergeTree

PARTITION BY toYYYYMM(collected_at)

ORDER BY (device_id, collected_at);

# 13\. Roadmap ve Sonraki Sürümler

| **Versiyon** | **Kapsam**                                                             |
| ------------ | ---------------------------------------------------------------------- |
| v0.1         | Kali Wi-Fi collector + Pi backend + SQLite + quality score.            |
| v0.2         | Streamlit dashboard, latest metrics, device list, anomaly list.        |
| v0.3         | Pi network probe, DNS latency, jitter, AP/gateway/internet ayrımı.     |
| v0.4         | Channel scan, komşu Wi-Fi ağları, channel recommendation.              |
| v0.5         | Root cause engine geliştirme, scenario test runner, markdown report.   |
| v0.6         | PostgreSQL/ClickHouse opsiyonları, retention policy, export.           |
| v0.7         | macOS collector, browser/phone probe, multi-device scoring.            |
| v1.0         | Installer, systemd servisleri, ekran görüntüleri, açık kaynak release. |

# 14\. Çalıştırma Sırası - Kafa Karıştırmayan Özet

| **Sıra** | **Nerede?**      | **Ne Yapılacak?**                                                      |
| -------- | ---------------- | ---------------------------------------------------------------------- |
| 1        | Access point     | SSID YOUR_SSID, DHCP kapalı, IP YOUR_AP_IP, kanal 6/20MHz.      |
| 2        | Raspberry Pi     | Backend kurulacak ve uvicorn ile 8080 portunda başlatılacak.           |
| 3        | Raspberry Pi     | Pi network probe çalıştırılacak.                                       |
| 4        | Linux Wi-Fi probe | YOUR_SSID ağına bağlanacak, iw dev ile interface bulunacak.        |
| 5        | Linux Wi-Fi probe | kali-agent.yaml ayarlanacak ve collector başlatılacak.                 |
| 6        | Herhangi cihaz   | http://PI_IP:8080/api/v1/metrics/latest ile veri geldiği doğrulanacak. |
| 7        | Dashboard        | Streamlit dashboard açılacak ve trendler izlenecek.                    |

**En önemli karar:** Başta her şeyi mükemmel yapmaya çalışma. Önce tek endpoint, tek DB ve iki agent ile çalışan v0.1 çıkar. Sonra dashboard ve root cause engine'i büyüt.

# 15\. Projenin Mantığı Tek Paragrafta

HomeNetIQ'de Raspberry Pi merkezi backend ve kablolu referans probe olarak çalışır. Linux Wi-Fi probe, your access point tarafından yayınlanan YOUR_SSID Wi-Fi ağına bağlanır ve iw/ping gibi Linux komutlarıyla Wi-Fi ve network metriklerini toplar. Toplanan veriler HTTP POST ile Raspberry Pi üzerindeki FastAPI backend'e gönderilir. Backend cihazları device_id ile ayırır, metrikleri SQLite veritabanına time-series event olarak kaydeder, rule-based kalite skoru üretir ve root cause sınıflandırması yapar. Streamlit dashboard ise cihazları, son metrikleri, anomalileri ve trendleri gösterir. Böylece sistem yalnızca sinyal gücü ölçmez; Wi-Fi, local network, DNS ve WAN/ISP sorunlarını ayırmaya çalışan küçük bir ev ağı intelligence platformuna dönüşür.
