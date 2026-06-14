#!/usr/bin/env bash
# Kali Linux Wi-Fi agent'ı bir tick çalıştırır.
# Repo kök dizininde çalıştırılmalıdır.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CONFIG="${CONFIG:-config/kali_agent.yaml}"

if [ ! -f "$CONFIG" ]; then
    echo "Hata: $CONFIG bulunamadı." >&2
    echo "       Önce:  cp config/kali_agent.yaml.example $CONFIG" >&2
    echo "       Sonra: targets/backend kısmını düzenle." >&2
    exit 1
fi

echo "[kali-once] config: $CONFIG"
exec python3 collectors/kali_wifi_agent.py --config "$CONFIG" --once
