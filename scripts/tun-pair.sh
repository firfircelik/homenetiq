#!/usr/bin/env bash
# meshlink — İKİ CİHAZ TUN kurulumu (gerçek VPN trafiği)
#
# Overlay ağ: 10.42.0.0/24
#   HOST  (server) : 10.42.0.1  — coordinator+relay de burada çalışır
#   CLIENT         : 10.42.0.2
#
# Kullanım:
#   HOST makinede   : sudo ./scripts/tun-pair.sh server
#   CLIENT makinede : sudo ./scripts/tun-pair.sh client <HOST_LAN_IP>
#
# Sonrasında gerçek trafik:  ping 10.42.0.1   /   ssh user@10.42.0.1
# Not: root gerekir (TUN cihazı açmak için). macOS'ta utun, Linux'ta tun0.
set -euo pipefail

ROLE="${1:-}"
HOST_LAN="${2:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$BIN:-$ROOT/../network-project/bin"
BIN="${BIN#/BIN:}"

log() { printf '\033[1;35m[tun-pair]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[hata]\033[0m %s\n' "$*"; exit 1; }

[ "$(id -u)" -eq 0 ] || die "root gerekli — sudo ile çalıştırın."
[ -x "$BIN/agent" ] || BIN="$ROOT/data"   # install.sh kopyaladıysa
[ -x "$BIN/coordinator" ] || die "meshlink binary'leri yok ($BIN). Önce scripts/install.sh."

TMP="$(mktemp -d)"
PIDS=()
cleanup(){ for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null||true; done; wait 2>/dev/null||true; rm -rf "$TMP";
  case "$(uname -s)" in
    Darwin) [ -n "${IFACE:-}" ] && ifconfig "$IFACE" destroy 2>/dev/null||true ;;
    Linux)  [ -n "${IFACE:-}" ] && ip link del "$IFACE" 2>/dev/null||true ;;
  esac; }
trap cleanup EXIT INT TERM

if [ "$ROLE" = "server" ]; then
  log "coordinator + relay başlatılıyor ..."
  "$BIN/coordinator" -ctrl 0.0.0.0:19200 -stun 0.0.0.0:19201 -keyfile "$TMP/c.key" >"$TMP/c.log" 2>&1 &
  PIDS+=($!)
  "$BIN/relay" -addr 0.0.0.0:19205 >/dev/null 2>&1 &
  PIDS+=($!)
  sleep 0.6
  PUB="$(grep -oE '[0-9a-f]{64}' "$TMP/c.log" | head -1)"
  LAN_IP="$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}' || hostname -I | awk '{print $1}')"
  log "HOST LAN IP: $LAN_IP   PUB: ${PUB:0:16}…"
  log "CLIENT komutu: sudo ./scripts/tun-pair.sh client $LAN_IP"
  log "agent a (TUN=10.42.0.1) başlatılıyor ..."
  IFACE="utun9"; UNAME="$(uname -s)"
  [ "$UNAME" = "Linux" ] && IFACE="tun0"
  exec "$BIN/agent" up --name a --keyfile "$TMP/a.key" --data 0.0.0.0:19501 \
    --coordinator "127.0.0.1:19200" --coord-pubkey "$PUB" \
    --stun "127.0.0.1:19201" --relay "127.0.0.1:19205" \
    --tun "$IFACE" --tun-ip 10.42.0.1 --tun-peer client=10.42.0.2
fi

if [ "$ROLE" = "client" ]; then
  [ -n "$HOST_LAN" ] || die "kullanım: $0 client <HOST_LAN_IP>"
  TMPKEY="$(mktemp -d)"
  log "host'tan pubkey alınıyor ..."
  PUB=""
  for p in 8080 8081; do
    PUB="$(curl -sf --max-time 5 "http://$HOST_LAN:$p/api/v1/mesh/pubkey" | python3 -c 'import json,sys;print(json.load(sys.stdin)["coord_pubkey"])' 2>/dev/null || true)"
    [ -n "$PUB" ] && break
  done
  if [ -z "$PUB" ]; then
    # TOFU yedeği: coordinator'a çıplak TCP ile bağlanıp Noise sonrası anahtarı
    # öğrenemeyiz; kullanıcıya elle ver diyoruz (güvenlik pinlemesi şart).
    die "pubkey alınamadı. Host'taki coordinator public key'ini elle girin:
         read -r PUB; sudo -E ./scripts/tun-pair.sh client $HOST_LAN"
  fi
  IFACE="utun9"; UNAME="$(uname -s)"
  [ "$UNAME" = "Linux" ] && IFACE="tun0"
  log "client agent (TUN=10.42.0.2 → host 10.42.0.1) başlatılıyor ..."
  exec "$BIN/agent" up --name client --keyfile "$TMP/cl.key" --data 0.0.0.0:19502 \
    --coordinator "$HOST_LAN:19200" --coord-pubkey "$PUB" \
    --stun "$HOST_LAN:19201" --relay "$HOST_LAN:19205" \
    --tun "$IFACE" --tun-ip 10.42.0.2 --tun-peer a=10.42.0.1
fi

die "rol eksik: 'server' ya da 'client <HOST_IP>'"
