#!/usr/bin/env bash
# First-run: generate a local token and starter files. Does not invent a LAN.
#
#   ./scripts/homenetiq-init.sh
#
# Writes:
#   backend/.env          (gitignore) with a random HOMENETIQ_API_TOKEN
#   config/*.yaml         from *.example if missing (empty gateway_ip / ap_ip)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

die() { printf '\033[1;31m[hata]\033[0m %s\n' "$*"; exit 1; }
log() { printf '\033[1;32m[init]\033[0m %s\n' "$*"; }

if command -v openssl >/dev/null 2>&1; then
  TOKEN="$(openssl rand -hex 32)"
else
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
fi

ENV_FILE="$ROOT/backend/.env"
if [ -f "$ENV_FILE" ]; then
  log "backend/.env already exists — not overwriting token"
else
  mkdir -p "$ROOT/backend" "$ROOT/data"
  cat > "$ENV_FILE" <<EOF
HOMENETIQ_DB_PATH=$ROOT/data/homenetiq.sqlite3
HOMENETIQ_API_TOKEN=$TOKEN
HOMENETIQ_REQUIRE_AUTH=true
HOMENETIQ_REQUIRE_GET_AUTH=true
HOMENETIQ_STALE_AFTER_SECONDS=120
HOMENETIQ_OFFLINE_AFTER_SECONDS=600
# Bind the API to localhost; put Caddy/nginx in front for LAN TLS (contrib/Caddyfile).
# HOMENETIQ_MESH_PUBKEY=
# HOMENETIQ_ENROLL_TOKEN=
# HOMENETIQ_NOTIFY_URL=
EOF
  chmod 600 "$ENV_FILE"
  log "wrote backend/.env (token length ${#TOKEN})"
fi

copied=0
for example in "$ROOT"/config/*.yaml.example; do
  [ -f "$example" ] || continue
  dest="${example%.example}"
  if [ -f "$dest" ]; then
    continue
  fi
  cp "$example" "$dest"
  copied=$((copied + 1))
done
log "starter YAML copies: $copied new file(s) (existing files left untouched)"

# Do not invent a home gateway. Empty targets.gateway_ip must stay empty
# until the operator fills it — collectors should fail loudly.
if grep -R --include='*.yaml' -n '192.168.1.1' config >/dev/null 2>&1; then
  die "config YAML still contains 192.168.1.1 — fill YOUR gateway, do not ship a guess"
fi

cat <<EOF

Next:
  1. Edit config/*.yaml — set backend.url, token (same as backend/.env),
     and targets.gateway_ip / ap_ip for YOUR network. Leave them empty
     and the probe will error instead of probing a guessed router.
  2. Source the env:  set -a && source backend/.env && set +a
  3. Start API on localhost:  make run-backend
  4. Optional mesh: fill config/meshlink_agent.yaml and MESHLINK_PREAUTH.

Dashboard needs HOMENETIQ_API_TOKEN in its environment too (GET auth is on).
EOF
