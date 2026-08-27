#!/usr/bin/env bash
# HomeNetIQ + meshlink — TEK KOMUTLA tam yığın (Docker'sız)
#
#   ./scripts/run-all.sh
#
# Ne yapar:
#   1. .venv yoksa kurar, bağımlılıkları yükler
#   2. meshlink binary'lerini bulur / kaynaklardan derler
#   3. config/meshlink_agent.yaml yoksa GERÇEK değerlerle üretir
#      (kalıcı data/coordinator.key'den pubkey otomatik yakalanır)
#   4. Sırayla kaldırır: coordinator → relay → agent a → backend →
#      mesh collector (döngü) → dashboard
#   5. Sağlık kontrolleri yapar, adresleri ekrana basar
#
# Durdurmak: Ctrl+C (tüm servisler temiz kapanır)
#
# Ortam değişkenleri:
#   MESHLINK_REPO   meshlink checkout yolu   (varsayılan: ../network-project; yoksa GitHub release)
#   BIND            dinleme adresi           (varsayılan: 127.0.0.1)
#   HOMENETIQ_API_TOKEN             backend token (yoksa üretilir)
#   MESH=0          meshlink yığınını atla (yalnız HomeNetIQ pano)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MESHLINK_REPO="${MESHLINK_REPO:-$ROOT/../network-project}"
BIND="${BIND:-127.0.0.1}"
# Dinleme ile hedef adresi AYRI tut: 0.0.0.0 "tüm arayüzlerde dinle" demektir
# ama agent'ın STUN/coordinator PAKETİ için hedef olarak geçersizdir.
AGENT_HOST="${AGENT_HOST:-$BIND}"
[ "$AGENT_HOST" = "0.0.0.0" ] && AGENT_HOST="127.0.0.1"
URL_HOST="$BIND"; [ "$URL_HOST" = "0.0.0.0" ] && URL_HOST="127.0.0.1"
TOKEN="${HOMENETIQ_API_TOKEN:-}"
if [ -z "$TOKEN" ] || [ "$TOKEN" = "change-me-local-token" ]; then
  if command -v openssl >/dev/null 2>&1; then
    TOKEN="$(openssl rand -hex 16)"
  else
    TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
  fi
  warn "üretilmiş oturum token'ı kullanılıyor (kalıcı için HOMENETIQ_API_TOKEN set edin)"
fi
MESH="${MESH:-1}"
DATA="$ROOT/data"
LOGS="$DATA/logs"
mkdir -p "$DATA" "$LOGS"

log()  { printf '\033[1;36m[run-all]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[uyarı]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[hata]\033[0m %s\n' "$*"; exit 1; }

PIDS=()
cleanup() {
  log "kapatılıyor ..."
  for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done
  wait 2>/dev/null || true
  log "görüşürüz 👋"
}
trap cleanup EXIT INT TERM

launch(){ local name=$1; shift; "$@" >"$LOGS/$name.log" 2>&1 & PIDS+=($!); }

wait_for(){ # wait_for <açıklama> <max_deneme> <komut...>
  local desc="$1" tries="$2"; shift 2
  for _ in $(seq 1 "$tries"); do
    if "$@" >/dev/null 2>&1; then log "$desc ✅"; return 0; fi
    sleep 0.5
  done
  die "$desc — başarısız (loglar: $LOGS)"
}

# ---------------------------------------------------- 0) Port ön kontrolü
ports="8080 8501"
[ "$MESH" = "1" ] && ports="$ports 19200"
for port in $ports; do
  if nc -z "$BIND" "$port" 2>/dev/null; then
    die "port $port meşgul görünüyor. Önce eski süreci kapatın: lsof -i :$port"
  fi
done

# ---------------------------------------------------- 1) Python venv
PY_BIN=""
for cand in python3.12 python3.11 python3.13 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    v="$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    case "$v" in 3.11|3.12|3.13) PY_BIN="$(command -v "$cand")"; break ;; esac
  fi
done
[ -n "$PY_BIN" ] || die "Python 3.11-3.13 bulunamadı."
if [ ! -x ".venv/bin/python" ]; then
  log "venv oluşturuluyor ($("$PY_BIN" --version)) ..."
  "$PY_BIN" -m venv .venv
fi
if ! ".venv/bin/python" -c "import fastapi, yaml, requests" >/dev/null 2>&1; then
  log "Python bağımlılıkları yükleniyor ..."
  ".venv/bin/pip" install -q -r backend/requirements.txt
fi

# ---------------------------------------------------- 2) meshlink (opsiyonel)
MESH_AGENT=""
MESH_COORD=""
MESH_RELAY=""
PREAUTH_FILE="$DATA/preauth.tokens"
if [ "$MESH" = "1" ]; then
  if [ -x "$MESHLINK_REPO/bin/agent" ]; then
    MESH_AGENT="$MESHLINK_REPO/bin/agent"
    MESH_COORD="$MESHLINK_REPO/bin/coordinator"
    MESH_RELAY="$MESHLINK_REPO/bin/relay"
  elif command -v meshlink-agent >/dev/null 2>&1 && command -v meshlink-coordinator >/dev/null 2>&1; then
    MESH_AGENT="$(command -v meshlink-agent)"
    MESH_COORD="$(command -v meshlink-coordinator)"
    MESH_RELAY="$(command -v meshlink-relay || true)"
  elif [ -d "$MESHLINK_REPO" ] && command -v go >/dev/null 2>&1; then
    log "meshlink derleniyor ($MESHLINK_REPO) ..."
    (cd "$MESHLINK_REPO" && make build >/dev/null)
    MESH_AGENT="$MESHLINK_REPO/bin/agent"
    MESH_COORD="$MESHLINK_REPO/bin/coordinator"
    MESH_RELAY="$MESHLINK_REPO/bin/relay"
  elif bash "$ROOT/scripts/fetch-meshlink.sh" "$DATA"; then
    MESH_AGENT="$DATA/meshlink-agent"
    MESH_COORD="$DATA/meshlink-coordinator"
    MESH_RELAY="$DATA/meshlink-relay"
  else
    die "meshlink bulunamadı. MESH=0 ile yalnız pano çalışır, veya MESHLINK_REPO / fetch-meshlink.sh kullanın."
  fi
  [ -x "$MESH_COORD" ] || die "meshlink coordinator binary yok"
  [ -x "$MESH_RELAY" ] || die "meshlink relay binary yok"
  log "meshlink agent: $MESH_AGENT"
  if [ ! -f "$PREAUTH_FILE" ]; then
    if command -v openssl >/dev/null 2>&1; then
      openssl rand -hex 16 > "$PREAUTH_FILE"
    else
      python3 -c 'import secrets; print(secrets.token_hex(16))' > "$PREAUTH_FILE"
    fi
    chmod 600 "$PREAUTH_FILE"
  fi
  PREAUTH="$(head -1 "$PREAUTH_FILE" | tr -d '\r\n')"
fi

# ---------------------------------------------------- 3) Config üretimi
CFG="config/meshlink_agent.yaml"
COORD_KEYFILE="$DATA/coordinator.key"
if [ "$MESH" = "1" ] && [ ! -f "$CFG" ]; then
  log "config/meshlink_agent.yaml üretiliyor ..."
  "$MESH_COORD" -ctrl "$BIND:19200" -stun "$BIND:19201" -keyfile "$COORD_KEYFILE" -preauth "$PREAUTH_FILE" >"$LOGS/keycap.log" 2>&1 &
  KPID=$!
  PUB=""
  for _ in $(seq 1 40); do
    PUB="$(grep -oE '[0-9a-f]{64}' "$LOGS/keycap.log" | head -1 || true)"
    [ -n "$PUB" ] && break
    sleep 0.25
  done
  kill $KPID 2>/dev/null || true; wait $KPID 2>/dev/null || true
  [ -n "$PUB" ] || die "coordinator pubkey alınamadı ($LOGS/keycap.log)"

  OS_NAME="$(uname -s | tr '[:upper:]' '[:lower:]')"
  cat > "$CFG" <<EOF
device:
  id: "$(hostname -s 2>/dev/null || echo local)-mesh"
  name: "$(hostname -s 2>/dev/null || echo local) meshlink tunnel"
  type: "network_probe"
  os: "$OS_NAME"
  agent_version: "1.0.0"

backend:
  url: "http://$URL_HOST:8080/api/v1/metrics"
  token: "$TOKEN"

collector:
  interval_seconds: 30
  retry_delay_seconds: 10
  timeout_seconds: 25

privacy:
  mode: "redact"
  salt: ""

meshlink:
  bin: "$MESH_AGENT"
  name: "b"
  keyfile: "$DATA/key.b"
  data: "0.0.0.0:19502"
  coordinator: "$AGENT_HOST:19200"
  coord_pubkey: "$PUB"
  stun: "$AGENT_HOST:19201"
  relay: "$AGENT_HOST:19205"
  probe_peer: "a"
  preauth: "$PREAUTH"
EOF
  log "config yazıldı (pubkey: ${PUB:0:16}…)"
elif [ "$MESH" = "1" ]; then
  log "config zaten var — dokunulmadı."
fi

# ---------------------------------------------------- 4) Servisler
PUB=""
if [ "$MESH" = "1" ]; then
  log "coordinator başlatılıyor ..."
  launch coordinator "$MESH_COORD" -ctrl "$BIND:19200" -stun "$BIND:19201" -keyfile "$COORD_KEYFILE" -preauth "$PREAUTH_FILE"
  for _ in $(seq 1 40); do
    PUB="$(grep -oE '[0-9a-f]{64}' "$LOGS/coordinator.log" | head -1 || true)"
    [ -n "$PUB" ] && break
    sleep 0.25
  done
  [ -n "$PUB" ] || die "coordinator pubkey log'a düşmedi ($LOGS/coordinator.log)"
  log "coordinator ayakta (pubkey ${PUB:0:16}…)"

  log "relay başlatılıyor ..."
  launch relay "$MESH_RELAY" -addr "$BIND:19205"
  sleep 0.4

  log "agent a başlatılıyor (kalıcı kimlik: $DATA/key.a) ..."
  launch agenta "$MESH_AGENT" up --name a --keyfile "$DATA/key.a" --data 0.0.0.0:19501 \
    --coordinator "$AGENT_HOST:19200" --coord-pubkey "$PUB" \
    --stun "$AGENT_HOST:19201" --relay "$AGENT_HOST:19205" \
    --preauth "$PREAUTH"
  sleep 2
  wait_for "agent a kaydoldu" 20 ps -p "$(pgrep -f 'agent up --name a' | head -1)"
fi

log "backend başlatılıyor ..."
export HOMENETIQ_API_TOKEN="$TOKEN"
export HOMENETIQ_REQUIRE_GET_AUTH="${HOMENETIQ_REQUIRE_GET_AUTH:-true}"
if [ -n "$PUB" ]; then
  export HOMENETIQ_MESH_PUBKEY="$PUB"
fi
launch backend ".venv/bin/python" -m uvicorn backend.app.main:app --host "$BIND" --port 8080
wait_for "backend sağlık kontrolü" 30 curl -sf "http://$BIND:8080/health"

if [ "$MESH" = "1" ]; then
  log "mesh collector başlatılıyor (30 sn'de bir örnek) ..."
  launch mesh-collector ".venv/bin/python" collectors/meshlink_agent.py --config "$CFG"
fi

log "dashboard başlatılıyor ..."
export HOMENETIQ_BACKEND_URL="http://$BIND:8080"
export HOMENETIQ_API_TOKEN="$TOKEN"
launch dashboard ".venv/bin/python" -m streamlit run dashboard/streamlit_app.py \
  --server.address 127.0.0.1 --server.port 8501 --server.headless true
sleep 2

# ---------------------------------------------------- 5) Özet
cat <<EOF

────────────────────────────────────────────────────────────
 🟢 HomeNetIQ çalışıyor (mesh: $MESH)
────────────────────────────────────────────────────────────
  Dashboard      : http://127.0.0.1:8501
  Backend API    : http://$BIND:8080/health
  Token          : (HOMENETIQ_API_TOKEN, GET auth açık)
EOF
if [ "$MESH" = "1" ]; then
  cat <<EOF
  Mesh koordinat.: $BIND:19200  (pin: ${PUB:0:16}…; üyelik preauth)
  join.sh        : HOMENETIQ_API_TOKEN=… MESHLINK_PREAUTH=$PREAUTH_FILE ./scripts/join.sh $URL_HOST
EOF
fi
cat <<EOF
  Loglar         : $LOGS/
  Durdurmak      : Ctrl+C
────────────────────────────────────────────────────────────
EOF

wait
