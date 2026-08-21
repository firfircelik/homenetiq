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
#   MESHLINK_REPO   meshlink checkout yolu   (varsayılan: ../network-project)
#   BIND            dinleme adresi           (varsayılan: 127.0.0.1)
#   HOMENETIQ_API_TOKEN             backend token (varsayılan: change-me-local-token)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MESHLINK_REPO="${MESHLINK_REPO:-$ROOT/../network-project}"
BIND="${BIND:-127.0.0.1}"
TOKEN="${HOMENETIQ_API_TOKEN:-change-me-local-token}"
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
for port in 8080 8501 19200; do
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

# ---------------------------------------------------- 2) meshlink binary
MESH_AGENT=""
MESH_COORD=""
if [ -x "$MESHLINK_REPO/bin/agent" ]; then
  MESH_AGENT="$MESHLINK_REPO/bin/agent"
  MESH_COORD="$MESHLINK_REPO/bin/coordinator"
elif command -v meshlink-agent >/dev/null 2>&1 && command -v meshlink-coordinator >/dev/null 2>&1; then
  MESH_AGENT="$(command -v meshlink-agent)"
  MESH_COORD="$(command -v meshlink-coordinator)"
elif [ -d "$MESHLINK_REPO" ] && command -v go >/dev/null 2>&1; then
  log "meshlink derleniyor ($MESHLINK_REPO) ..."
  (cd "$MESHLINK_REPO" && make build >/dev/null)
  MESH_AGENT="$MESHLINK_REPO/bin/agent"
  MESH_COORD="$MESHLINK_REPO/bin/coordinator"
else
  die "meshlink bulunamadı. MESHLINK_REPO=<yol> verin ya da network-project'i yanına klonlayın."
fi
log "meshlink agent: $MESH_AGENT"

# ---------------------------------------------------- 3) Config üretimi
CFG="config/meshlink_agent.yaml"
COORD_KEYFILE="$DATA/coordinator.key"
if [ ! -f "$CFG" ]; then
  log "config/meshlink_agent.yaml üretiliyor ..."
  # Kalıcı keyfile ile coordinator'ı bir anlığına başlat → pubkey'i yakala.
  "$MESH_COORD" -ctrl "$BIND:19200" -stun "$BIND:19201" -keyfile "$COORD_KEYFILE" >"$LOGS/keycap.log" 2>&1 &
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
  url: "http://$BIND:8080/api/v1/metrics"
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
  coordinator: "$BIND:19200"
  coord_pubkey: "$PUB"
  stun: "$BIND:19201"
  relay: "$BIND:19205"
  probe_peer: "a"
EOF
  log "config yazıldı (pubkey: ${PUB:0:16}…)"
else
  log "config zaten var — dokunulmadı."
fi

# ---------------------------------------------------- 4) Servisler
log "coordinator başlatılıyor ..."
launch coordinator "$MESH_COORD" -ctrl "$BIND:19200" -stun "$BIND:19201" -keyfile "$COORD_KEYFILE"
PUB=""
for _ in $(seq 1 40); do
  PUB="$(grep -oE '[0-9a-f]{64}' "$LOGS/coordinator.log" | head -1 || true)"
  [ -n "$PUB" ] && break
  sleep 0.25
done
[ -n "$PUB" ] || die "coordinator pubkey log'a düşmedi ($LOGS/coordinator.log)"
log "coordinator ayakta (pubkey ${PUB:0:16}…)"

log "relay başlatılıyor ..."
launch relay "$MESHLINK_REPO/bin/relay" -addr "$BIND:19205"
sleep 0.4

log "agent a başlatılıyor (kalıcı kimlik: $DATA/key.a) ..."
launch agenta "$MESH_AGENT" up --name a --keyfile "$DATA/key.a" --data 0.0.0.0:19501 \
  --coordinator "$BIND:19200" --coord-pubkey "$PUB" \
  --stun "$BIND:19201" --relay "$BIND:19205"
sleep 2

log "backend başlatılıyor ..."
export HOMENETIQ_API_TOKEN="$TOKEN"
launch backend ".venv/bin/python" -m uvicorn backend.app.main:app --host "$BIND" --port 8080
wait_for "backend sağlık kontrolü" 30 curl -sf "http://$BIND:8080/health"

log "mesh collector başlatılıyor (30 sn'de bir örnek) ..."
launch mesh-collector ".venv/bin/python" collectors/meshlink_agent.py --config "$CFG"

log "dashboard başlatılıyor ..."
export HOMENETIQ_BACKEND_URL="http://$BIND:8080"
launch dashboard ".venv/bin/python" -m streamlit run dashboard/streamlit_app.py \
  --server.address 0.0.0.0 --server.port 8501 --server.headless true
sleep 2

# ---------------------------------------------------- 5) Özet
cat <<EOF

────────────────────────────────────────────────────────────
 🟢 HomeNetIQ + meshlink yığını çalışıyor
────────────────────────────────────────────────────────────
  Dashboard      : http://localhost:8501        ("🔐 Mesh VPN" sayfası)
  Backend API    : http://$BIND:8080/health
  Mesh koordinat.: $BIND:19200  (pinli anahtar: ${PUB:0:16}…)
  Loglar         : $LOGS/
  Durdurmak      : Ctrl+C
────────────────────────────────────────────────────────────
EOF

wait
