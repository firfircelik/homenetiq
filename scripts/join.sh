#!/usr/bin/env bash
# meshlink ağına TEK KOMUTLA katıl (client / ikinci cihaz)
#
#   HOMENETIQ_API_TOKEN=... MESHLINK_PREAUTH=... ./scripts/join.sh <HOST_IP> [İSIM]
#
# Örnek:
#   ./scripts/join.sh YOUR_COORDINATOR_HOST linux
#
# Ne yapar:
#   1. Host'un HomeNetIQ backend'inden coordinator public key'i çeker
#      (GET /api/v1/mesh/pubkey — pinlenen kimlik; üyelik vermez)
#   2. meshlink agent binary'sini bulur (yerel repo, PATH, veya GitHub release)
#   3. Agent'ı --preauth ile kaydeder (coordinator -preauth zorunlu üretimde)
#
# Ortam değişkenleri:
#   DATA_PORT              veri soketi portu (varsayılan 19502)
#   HOMENETIQ_API_TOKEN    backend Bearer (zorunlu; GET auth)
#   HOMENETIQ_ENROLL_TOKEN pubkey için ayrı token (opsiyonel, API token yerine)
#   MESHLINK_PREAUTH       coordinator enrollment token veya token dosyası (zorunlu)
set -euo pipefail

HOST_IP="${1:-}"
[ -n "$HOST_IP" ] || { echo "Kullanım: HOMENETIQ_API_TOKEN=... MESHLINK_PREAUTH=... $0 <HOST_IP> [İSİM]"; exit 1; }
NAME="${2:-$(hostname -s | tr -d ' ')}"
DATA_PORT="${DATA_PORT:-19502}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log()  { printf '\033[1;32m[join]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[hata]\033[0m %s\n' "$*"; exit 1; }

TOKEN="${HOMENETIQ_ENROLL_TOKEN:-${HOMENETIQ_API_TOKEN:-}}"
[ -n "$TOKEN" ] || die "HOMENETIQ_API_TOKEN (veya HOMENETIQ_ENROLL_TOKEN) zorunlu"
PREAUTH="${MESHLINK_PREAUTH:-}"
[ -n "$PREAUTH" ] || die "MESHLINK_PREAUTH zorunlu (coordinator -preauth token veya dosya yolu)"
if [ -f "$PREAUTH" ]; then
  PREAUTH="$(tr -d '\r\n' < "$PREAUTH")"
fi

# ------------------------------------------------ 1) Pubkey'i host'tan al
PUB="$(curl -sf --max-time 8 -H "Authorization: Bearer $TOKEN" \
  "http://$HOST_IP:8080/api/v1/mesh/pubkey" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["coord_pubkey"])')" \
  || die "pubkey alınamadı (401 = token eksik). Host: curl -H \"Authorization: Bearer \$TOKEN\" http://$HOST_IP:8080/health"
log "coordinator pubkey alındı: ${PUB:0:16}… (pin; üyelik preauth ile)"

# ------------------------------------------------ 2) meshlink binary
MESHLINK_REPO="${MESHLINK_REPO:-$ROOT/../network-project}"
AGENT=""
for cand in \
  "${MESHLINK_AGENT:-}" \
  "$MESHLINK_REPO/bin/agent" \
  "$(command -v meshlink-agent 2>/dev/null || true)" \
  "$ROOT/data/meshlink-agent"
do
  if [ -n "$cand" ] && [ -x "$cand" ]; then AGENT="$cand"; break; fi
done

if [ -z "$AGENT" ] && [ -d "$MESHLINK_REPO" ] && command -v go >/dev/null 2>&1; then
  log "meshlink derleniyor ($MESHLINK_REPO) ..."
  (cd "$MESHLINK_REPO" && make build >/dev/null) || die "derleme başarısız"
  AGENT="$MESHLINK_REPO/bin/agent"
fi

if [ -z "$AGENT" ]; then
  log "yerel binary yok — GitHub release deneniyor ..."
  if bash "$ROOT/scripts/fetch-meshlink.sh" "$ROOT/data"; then
    AGENT="$ROOT/data/meshlink-agent"
    [ -x "$AGENT" ] || AGENT="$ROOT/data/agent"
  fi
fi

[ -n "$AGENT" ] && [ -x "$AGENT" ] || die "meshlink agent bulunamadı. Şunlardan biri olsun:
  - MESHLINK_VERSION=v0.2.0 ./scripts/fetch-meshlink.sh
  - scripts/install.sh
  - MESHLINK_REPO=<meshlink-repo-yolu> $0 $HOST_IP"

# ------------------------------------------------ 3) Katıl
mkdir -p data
log "'$NAME' olarak ağa katılılıyor ($HOST_IP) ..."
exec "$AGENT" up \
  --name "$NAME" \
  --keyfile "data/$NAME.key" \
  --data "0.0.0.0:$DATA_PORT" \
  --coordinator "$HOST_IP:19200" \
  --coord-pubkey "$PUB" \
  --stun "$HOST_IP:19201" \
  --relay "$HOST_IP:19205" \
  --preauth "$PREAUTH"
