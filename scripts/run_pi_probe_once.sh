#!/usr/bin/env bash
# Raspberry Pi network probe'u bir tick çalıştırır.
# Repo kök dizininde çalıştırılmalıdır.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CONFIG="${CONFIG:-config/pi_probe.yaml}"

if [ ! -f "$CONFIG" ]; then
    echo "Hata: $CONFIG bulunamadı." >&2
    echo "       Önce:  cp config/pi_probe.yaml.example $CONFIG" >&2
    echo "       Sonra: targets bölümünü düzenle." >&2
    exit 1
fi

echo "[pi-probe-once] config: $CONFIG"
exec python3 probes/pi_network_probe.py --config "$CONFIG" --once
