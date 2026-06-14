#!/usr/bin/env bash
# HomeNetIQ Streamlit dashboard'u başlatır.
# Repo kök dizininde çalıştırılmalıdır.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -z "${HOMENETIQ_BACKEND_URL:-}" ]; then
    echo "[dashboard] HOMENETIQ_BACKEND_URL ayarlı değil; varsayılan http://127.0.0.1:8080 kullanılacak."
    echo "[dashboard] Başka bir backend'e bağlanmak için: export HOMENETIQ_BACKEND_URL=http://..."
fi

echo "[dashboard] Backend: ${HOMENETIQ_BACKEND_URL:-http://127.0.0.1:8080}"
echo "[dashboard] http://localhost:8501  (Ctrl+C ile durdur)"

exec python3 -m streamlit run dashboard/streamlit_app.py
