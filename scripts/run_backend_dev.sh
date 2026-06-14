#!/usr/bin/env bash
# HomeNetIQ backend'i geliştirme modunda başlatır.
# Repo kök dizininde çalıştırılmalıdır.
set -euo pipefail

# Repo köküne geç (scriptin nerede çağrıldığından bağımsız)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export HOMENETIQ_DB_PATH="${HOMENETIQ_DB_PATH:-./homenetiq.sqlite3}"
export HOMENETIQ_API_TOKEN="${HOMENETIQ_API_TOKEN:-change-me-local-token}"
export HOMENETIQ_REQUIRE_AUTH="${HOMENETIQ_REQUIRE_AUTH:-true}"

echo "[backend] HOMENETIQ_DB_PATH=$HOMENETIQ_DB_PATH"
echo "[backend] HOMENETIQ_API_TOKEN=*** (${#HOMENETIQ_API_TOKEN} chars)"
echo "[backend] http://0.0.0.0:8080  (Ctrl+C ile durdur)"

exec python3 -m uvicorn backend.app.main:app \
    --host 0.0.0.0 --port 8080 --reload
