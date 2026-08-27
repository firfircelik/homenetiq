#!/usr/bin/env bash
# Download meshlink agent (and optionally other binaries) from GitHub Releases.
# Local checkout ../network-project is optional.
#
#   ./scripts/fetch-meshlink.sh [DEST_DIR]
#
# Env:
#   MESHLINK_VERSION  tag (default v0.2.0)
#   MESHLINK_REPO_SLUG  owner/name (default firfircelik/network-project)
set -euo pipefail

DEST="${1:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -n "$DEST" ] || DEST="$ROOT/data"
mkdir -p "$DEST"

VER="${MESHLINK_VERSION:-v0.2.0}"
VER_NUM="${VER#v}"
SLUG="${MESHLINK_REPO_SLUG:-firfircelik/network-project}"
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
esac

# GoReleaser archive name: meshlink_<version>_<os>_<arch>.tar.gz
URL="https://github.com/${SLUG}/releases/download/${VER}/meshlink_${VER_NUM}_${OS}_${ARCH}.tar.gz"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "[fetch-meshlink] $URL"
if ! command -v curl >/dev/null 2>&1; then
  echo "curl required" >&2
  exit 1
fi
if ! curl -fsSL --max-time 60 "$URL" -o "$TMP/meshlink.tgz"; then
  echo "download failed (tag $VER may not exist yet). Clone network-project and make build instead." >&2
  exit 1
fi
tar -xzf "$TMP/meshlink.tgz" -C "$TMP"
# Archives may nest the binary at top level as "agent".
FOUND=""
for cand in "$TMP/agent" "$TMP/meshlink-agent" "$DEST/agent"; do
  if [ -f "$cand" ]; then FOUND="$cand"; break; fi
done
# goreleaser sometimes uses a folder
if [ -z "$FOUND" ]; then
  FOUND="$(find "$TMP" -maxdepth 3 -type f -name agent | head -1 || true)"
fi
[ -n "$FOUND" ] || { echo "agent binary missing from archive"; exit 1; }
cp "$FOUND" "$DEST/meshlink-agent"
chmod +x "$DEST/meshlink-agent"
# Also copy coordinator/relay if present (operator host).
for b in coordinator relay natbox; do
  f="$(find "$TMP" -maxdepth 3 -type f -name "$b" | head -1 || true)"
  if [ -n "$f" ]; then
    cp "$f" "$DEST/meshlink-$b"
    chmod +x "$DEST/meshlink-$b"
  fi
done
echo "[fetch-meshlink] installed $DEST/meshlink-agent"
