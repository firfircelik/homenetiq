#!/usr/bin/env bash
# meshlink ağına TEK KOMUTLA katıl (client / ikinci cihaz)
#
#   ./scripts/join.sh <HOST_IP> [İSIM]
#
# Örnek:
#   ./scripts/join.sh 192.168.1.113 linux
#
# Ne yapar:
#   1. Host'un HomeNetIQ backend'inden coordinator public key'i çeker
#      (GET /api/v1/mesh/pubkey — anahtar gizli değil, pinlenen kimliktir)
#   2. meshlink agent binary'sini bulur
#   3. Agent'ı kalıcı kimlikle (data/<isim>.key) ayağa kaldırır
#
# Ortam değişkenleri:
#   DATA_PORT   veri soketi portu (varsayılan 19502; aynı makinede çok
#               client test ediliyorsa çakışmayı önler)
set -euo pipefail

HOST_IP="${1:-}"
[ -n "$HOST_IP" ] || { echo "Kullanım: $0 <HOST_IP> [İSİM]   örn: $0 192.168.1.113 linux"; exit 1; }
NAME="${2:-$(hostname -s | tr -d ' ')}"
DATA_PORT="${DATA_PORT:-19502}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log()  { printf '\033[1;32m[join]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[hata]\033[0m %s\n' "$*"; exit 1; }

# ------------------------------------------------ 1) Pubkey'i host'tan al
PUB="$(curl -sf --max-time 8 "http://$HOST_IP:8080/api/v1/mesh/pubkey" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["coord_pubkey"])')" \
  || die "pubkey alınamadı. Host çalışıyor mu?  curl http://$HOST_IP:8080/health"
log "coordinator pubkey alındı: ${PUB:0:16}…"

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

# Otomatik derleme: repo var + go var ama binary yok → kendin derle
if [ -z "$AGENT" ] && [ -d "$MESHLINK_REPO" ] && command -v go >/dev/null 2>&1; then
  log "meshlink derleniyor ($MESHLINK_REPO) ..."
  (cd "$MESHLINK_REPO" && make build >/dev/null) || die "derleme başarısız"
  AGENT="$MESHLINK_REPO/bin/agent"
fi

[ -n "$AGENT" ] || die "meshlink agent bulunamadı. Şunlardan biri olsun:
  - scripts/install.sh çalıştır (PATH'e meshlink-agent koyar)
  - ya da: MESHLINK_REPO=<meshlink-repo-yolu> $0 $HOST_IP"

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
  --relay "$HOST_IP:19205"
