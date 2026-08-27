# HomeNetIQ Makefile
# Tüm komutlar repo kök dizininden çalıştırılmalıdır.

PY     ?= python3
PIP    ?= $(PY) -m pip
VENV   ?= .venv

# Eğer .venv mevcutsa onu kullan; yoksa sistem python3'ünü.
ifeq ($(wildcard $(VENV)/bin/python),$(VENV)/bin/python)
PY := $(VENV)/bin/python
PIP := $(PY) -m pip
endif

# pip kurulumu tek yerde: backend/requirements.txt
REQ     = backend/requirements.txt
BACKEND = backend.app.main:app
DASH    = dashboard/streamlit_app.py
KALI    = collectors/kali_wifi_agent.py
MACOS   = collectors/macos_wifi_agent.py
PI      = probes/pi_network_probe.py
MESH    = collectors/meshlink_agent.py

CONFIG_KALI   ?= config/kali_agent.yaml
CONFIG_MACOS  ?= config/macos_agent.yaml
CONFIG_PI     ?= config/pi_probe.yaml
CONFIG_MESH   ?= config/meshlink_agent.yaml

HOST ?= 127.0.0.1
PORT ?= 8080
DB   ?= data/homenetiq.sqlite3

.PHONY: help install init test test-fast run-backend run-dashboard \
        kali-once macos-once pi-probe-once mesh-once backup clean lint

.PHONY: help install test test-fast run-backend run-dashboard \
        kali-once macos-once pi-probe-once mesh-once clean lint

help:
	@echo "HomeNetIQ v1 — Makefile"
	@echo ""
	@echo "  make init            Token + starter YAML (gateway boş kalır)"
	@echo "  make install         Sanal ortam kur + requirements kur"
	@echo "  make test            Tüm testleri çalıştır (pytest tests/ -v)"
	@echo "  make test-fast       Testleri verbose'siz çalıştır"
	@echo "  make run-backend     Backend (127.0.0.1:8080, GET auth açık)"
	@echo "  make run-dashboard   Streamlit dashboard'u başlat"
	@echo "  make backup          SQLite kopyası (data/backups/); retention sizin"
	@echo "  make kali-once       Kali Wi-Fi agent'ı bir tick çalıştır"
	@echo "  make macos-once      macOS Wi-Fi agent'ı bir tick çalıştır"
	@echo "  make pi-probe-once   Pi network probe'u bir tick çalıştır"
	@echo "  make mesh-once       meshlink VPN sağlık agent'ını bir tick çalıştır"
	@echo "  make clean           __pycache__ + .pytest_cache + .venv sil"
	@echo ""
	@echo "Config dosyaları CONFIG_KALI / CONFIG_MACOS / CONFIG_PI / CONFIG_MESH ile override edilebilir."

install:
	test -d $(VENV) || $(PY) -m venv $(VENV)
	. $(VENV)/bin/activate && $(PIP) install -q -r $(REQ)

init:
	bash scripts/homenetiq-init.sh

backup:
	mkdir -p data/backups
	@test -f $(DB) || { echo "Veritabanı yok: $(DB) — önce backend'i çalıştırın."; exit 1; }
	cp $(DB) data/backups/homenetiq-$$(date +%Y%m%dT%H%M%S).sqlite3
	@if command -v sqlite3 >/dev/null 2>&1; then \
	  sqlite3 $(DB) ".backup data/backups/homenetiq-latest.sqlite3"; \
	fi
	@echo "Kopyalandı. Metrik tablosu büyür; eski yedekleri siz silin."

lint:
	$(PY) -m ruff check backend collectors dashboard probes agents tests

test:
	$(PY) -m pytest tests/ -v

test-fast:
	$(PY) -m pytest tests/

run-backend:
	bash scripts/run_backend_dev.sh

run-dashboard:
	@if [ ! -f $(CONFIG_KALI) ] && [ ! -f $(CONFIG_MACOS) ] && [ ! -f $(CONFIG_PI) ]; then \
		echo "Hata: Hiçbir agent config bulunamadı. Önce 'cp config/*agent.yaml.example config/*.yaml' çalıştırın."; \
		exit 1; \
	fi
	@if [ -z "$$HOMENETIQ_BACKEND_URL" ]; then \
		echo "HOMENETIQ_BACKEND_URL ayarlı değil; varsayılan http://127.0.0.1:8080 kullanılacak."; \
	fi
	$(PY) -m streamlit run $(DASH)

kali-once:
	@test -f $(CONFIG_KALI) || { echo "Config yok: $(CONFIG_KALI) — 'cp config/kali_agent.yaml.example $(CONFIG_KALI)'"; exit 1; }
	$(PY) $(KALI) --config $(CONFIG_KALI) --once

macos-once:
	@test -f $(CONFIG_MACOS) || { echo "Config yok: $(CONFIG_MACOS) — 'cp config/macos_agent.yaml.example $(CONFIG_MACOS)'"; exit 1; }
	$(PY) $(MACOS) --config $(CONFIG_MACOS) --once

pi-probe-once:
	@test -f $(CONFIG_PI) || { echo "Config yok: $(CONFIG_PI) — 'cp config/pi_probe.yaml.example $(CONFIG_PI)'"; exit 1; }
	$(PY) $(PI) --config $(CONFIG_PI) --once

mesh-once:
	@test -f $(CONFIG_MESH) || { echo "Config yok: $(CONFIG_MESH) — 'cp config/meshlink_agent.yaml.example $(CONFIG_MESH)' veya './scripts/install.sh'"; exit 1; }
	$(PY) $(MESH) --config $(CONFIG_MESH) --once

clean:
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	@echo "Temizlendi. (.venv korundu; silmek için: rm -rf .venv)"
