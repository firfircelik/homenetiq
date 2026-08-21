#!/usr/bin/env bash
# HomeNetIQ + meshlink — tek komut kurulum
#
# Ne yapar:
#   1. Python venv (.venv) kurar, backend bağımlılıklarını yükler
#   2. meshlink binary'sini bulur/derler ve PATH'e (INSTALL_BIN) kopyalar
#   3. config/meshlink_agent.yaml üretir (coordinator + pubkey sorar)
#   4. systemd servislerini gerçek yollarla yazar (Linux'ta)
#
# Kullanım:
#   ./scripts/install.sh
#
# Ortam değişkenleri:
#   MESHLINK_REPO   meshlink checkout yolu   (varsayılan: ../network-project)
#   INSTALL_BIN     binary hedefi            (varsayılan: /usr/local/bin)
#   COORDINATOR     coordinator adresi       (ör. 192.168.1.113:19200)
#   COORD_PUBKEY    coordinator public key   (64 hex)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

MESHLINK_REPO="${MESHLINK_REPO:-$REPO_ROOT/../network-project}"
INSTALL_BIN="${INSTALL_BIN:-/usr/local/bin}"
SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO="sudo"

log()  { printf '\033[1;36m[install]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[uyarı]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[hata]\033[0m %s\n' "$*"; exit 1; }

# ---------------------------------------------------------------- 1) Python
PY_BIN=""
for cand in python3.12 python3.11 python3.13 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    v="$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    case "$v" in
      3.11|3.12|3.13) PY_BIN="$(command -v "$cand")"; break ;;
    esac
  fi
done
[ -n "$PY_BIN" ] || die "Python 3.11-3.13 bulunamadı (3.14 desteklenmiyor)."

if [ ! -x ".venv/bin/python" ]; then
  log "venv oluşturuluyor ($("$PY_BIN" --version)) ..."
  "$PY_BIN" -m venv .venv
fi
log "Python bağımlılıkları yükleniyor ..."
".venv/bin/pip" install -q -r backend/requirements.txt

# ---------------------------------------------------------------- 2) meshlink
log "meshlink binary'leri kontrol ediliyor ..."
# meshlink dört binary üretir: agent, coordinator, relay, natbox.
# Müşteri ürünü için hepsini "meshlink-*" önekiyle kuruyoruz.
MESH_AGENT_BIN=""
MESH_COORD_BIN=""
declare -a FOUND=()
for b in agent coordinator relay natbox; do
  SRC=""
  if [ -x "$MESHLINK_REPO/bin/$b" ]; then
    SRC="$MESHLINK_REPO/bin/$b"
  fi
  if [ -n "$SRC" ]; then
    if [ -w "$INSTALL_BIN" ] || [ "$(id -u)" -eq 0 ]; then
      cp "$SRC" "$INSTALL_BIN/meshlink-$b"
    else
      $SUDO cp "$SRC" "$INSTALL_BIN/meshlink-$b"
    fi
    FOUND+=("meshlink-$b")
    [ "$b" = "agent" ] && MESH_AGENT_BIN="$INSTALL_BIN/meshlink-agent"
    [ "$b" = "coordinator" ] && MESH_COORD_BIN="$INSTALL_BIN/meshlink-coordinator"
  fi
done

if [ ! -d "$MESHLINK_REPO" ] && command -v go >/dev/null 2>&1 && [ -n "${MESHLINK_REPO:-}" ]; then
  : # repo yok ama go var: aşağıdaki uyarı yeterli
fi

if [ ${#FOUND[@]} -gt 0 ]; then
  log "kuruldu: ${FOUND[*]}"
elif [ -d "$MESHLINK_REPO" ] && command -v go >/dev/null 2>&1; then
  log "meshlink kaynaklardan derleniyor ($MESHLINK_REPO) ..."
  (cd "$MESHLINK_REPO" && make build >/dev/null)
  exec "$0"   # derleme sonrası kendini tekrar çalıştır
else
  warn "meshlink binary bulunamadı/derlenemedi."
  warn "  → git clone https://github.com/firfircelik/network-project && cd network-project && make build"
  warn "  → sonra tekrar çalıştırın: MESHLINK_REPO=<yol> $0"
fi

# ---------------------------------------------------------------- 3) Config
CFG="config/meshlink_agent.yaml"
if [ ! -f "$CFG" ]; then
  log "config/meshlink_agent.yaml üretiliyor ..."
  cp config/meshlink_agent.yaml.example "$CFG"

  COORDINATOR="${COORDINATOR:-}"
  COORD_PUBKEY="${COORD_PUBKEY:-}"
  INTERACTIVE=0
  [ -t 0 ] && INTERACTIVE=1
  if [ -z "$COORDINATOR" ]; then
    if [ "$INTERACTIVE" -eq 1 ]; then
      read -r -p "Coordinator adresi [192.168.1.50:19200]: " COORDINATOR
    fi
    COORDINATOR="${COORDINATOR:-192.168.1.50:19200}"
  fi
  # Public key'i yalnızca coordinator bu makinede çalışacaksa otomatik yakala.
  case "$COORDINATOR" in
    127.*|localhost:*|""|192.168.1.50:*) AUTO_KEY=1 ;;
    *) AUTO_KEY=0 ;;
  esac
  if [ -z "$COORD_PUBKEY" ] && [ "$AUTO_KEY" -eq 1 ] && [ -n "${MESH_COORD_BIN:-}" ]; then
    # ÖNEMLİ: Anahtarı KALICI bir keyfile'dan üret — systemd ile çalışacak
    # gerçek coordinator aynı dosyayı kullanır, böylece agent pinning eşleşir.
    COORD_KEYFILE="${COORD_KEYFILE:-$REPO_ROOT/data/coordinator.key}"
    mkdir -p "$(dirname "$COORD_KEYFILE")"
    log "Coordinator public key alınıyor (kalıcı keyfile: $COORD_KEYFILE) ..."
    TMPK="$(mktemp -d)"
    "$MESH_COORD_BIN" -ctrl 127.0.0.1:19200 -stun 127.0.0.1:19201 -keyfile "$COORD_KEYFILE" >"$TMPK/log" 2>&1 &
    CPID=$!
    PUB=""
    for _ in $(seq 1 30); do
      PUB="$(grep -oE '[0-9a-f]{64}' "$TMPK/log" | head -1 || true)"
      [ -n "$PUB" ] && break
      sleep 0.2
    done
    kill $CPID 2>/dev/null || true
    wait $CPID 2>/dev/null || true
    rm -rf "$TMPK"
    if [ -n "${PUB:-}" ]; then
      COORD_PUBKEY="$PUB"
      log "Public key alındı: ${COORD_PUBKEY:0:16}…"
      log "Coordinator'ı BU keyfile ile çalıştırın: $MESH_COORD_BIN -ctrl 0.0.0.0:19200 -stun 0.0.0.0:19201 -keyfile $COORD_KEYFILE"
    else
      warn "Public key otomatik alınamadı; elle girmeniz gerekecek."
    fi
  fi
  if [ -z "$COORD_PUBKEY" ]; then
    if [ "$INTERACTIVE" -eq 1 ]; then
      read -r -p "Coordinator control public key (64 hex): " COORD_PUBKEY
    else
      warn "COORD_PUBKEY verilmedi — $CFG içine elle girmeniz gerekecek."
    fi
  fi

  # Placeholder'ları gerçek değerlerle değiştir.
  .venv/bin/python - "$CFG" "$COORDINATOR" "$COORD_PUBKEY" <<'PYEOF'
import re, sys
path, coord, pub = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path).read()
text = text.replace("192.168.1.113:19200", coord)
text = text.replace("192.168.1.113:19201", coord.rsplit(":", 1)[0] + ":19201")
text = text.replace("192.168.1.113:19205", coord.rsplit(":", 1)[0] + ":19205")
text = text.replace("<coordinator-control-public-key-hex>", pub)
open(path, "w").write(text)
print(f"[install] {path} güncellendi")
PYEOF
else
  log "$CFG zaten var — dokunulmadı."
fi

# ---------------------------------------------------------------- 4) systemd
if [ -d /etc/systemd/system ]; then
  log "systemd birimleri yazılıyor ..."
  REAL_ROOT="$REPO_ROOT"
  RUN_USER="${SUDO_USER:-$(id -un)}"
  for unit in homenetiq-backend homenetiq-mesh-agent; do
    sed -e "s|User=.*|User=$RUN_USER|" \
        -e "s|WorkingDirectory=.*|WorkingDirectory=$REAL_ROOT|" \
        -e "s|ExecStart=\(.*\)/\.venv/|ExecStart=$REAL_ROOT/.venv/|" \
        "systemd/$unit.service" | $SUDO tee "/etc/systemd/system/$unit.service" >/dev/null
  done
  $SUDO systemctl daemon-reload
  log "Servisleri başlatmak için:"
  log "  sudo systemctl enable --now homenetiq-backend homenetiq-mesh-agent"
else
  warn "systemd bulunamadı (macOS?) — manuel çalıştırma:"
  warn "  .venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8080"
  warn "  .venv/bin/streamlit run dashboard/streamlit_app.py"
  warn "  .venv/bin/python collectors/meshlink_agent.py --config config/meshlink_agent.yaml --once"
fi

log "Kurulum tamamlandı 🎉"
log "Dashboard: streamlit run dashboard/streamlit_app.py  → '🔐 Mesh VPN' sayfası"
