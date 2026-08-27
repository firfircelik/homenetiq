#!/usr/bin/env bash
# HomeNetIQ backend'i geliştirme modunda başlatır.
# Repo kök dizininde çalıştırılmalıdır.
#
# Loads backend/.env when present (from `make init`). Does NOT default
# HOMENETIQ_ALLOW_INSECURE — set it explicitly for a throwaway demo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f "$ROOT/backend/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/backend/.env"
  set +a
fi

export HOMENETIQ_DB_PATH="${HOMENETIQ_DB_PATH:-$ROOT/data/homenetiq.sqlite3}"
export HOMENETIQ_REQUIRE_AUTH="${HOMENETIQ_REQUIRE_AUTH:-true}"
export HOMENETIQ_REQUIRE_GET_AUTH="${HOMENETIQ_REQUIRE_GET_AUTH:-true}"
HOST="${HOMENETIQ_BIND:-127.0.0.1}"

if [ -z "${HOMENETIQ_API_TOKEN:-}" ]; then
  echo "[backend] HOMENETIQ_API_TOKEN unset. Run: make init" >&2
  echo "[backend] (local demo only: HOMENETIQ_ALLOW_INSECURE=1 with a placeholder token)" >&2
  exit 1
fi

echo "[backend] HOMENETIQ_DB_PATH=$HOMENETIQ_DB_PATH"
echo "[backend] HOMENETIQ_API_TOKEN=*** (${#HOMENETIQ_API_TOKEN} chars)"
echo "[backend] GET auth=$HOMENETIQ_REQUIRE_GET_AUTH ALLOW_INSECURE=${HOMENETIQ_ALLOW_INSECURE:-}"
echo "[backend] http://$HOST:8080  (Ctrl+C ile durdur)"

exec python3 -m uvicorn backend.app.main:app \
    --host "$HOST" --port 8080 --reload
