#!/usr/bin/env bash
# Install (or update) the AmneziaWG Decky plugin on a remote Steam Deck.
#
# Usage:
#   ./scripts/install-remote.sh <deck-host-or-ip> [version-tag]
#
# Examples:
#   ./scripts/install-remote.sh 192.168.1.42
#   ./scripts/install-remote.sh deck-hostname.local v2.0.0
#
# Env overrides:
#   SSH_USER  — SSH login user on the deck (default: deck)
#   REPO      — owner/repo for releases (default: GordinRoman/decky-amnezia)
#   ASSET     — release asset file name (default: AmneziaWG.zip)

set -euo pipefail

HOST="${1:-}"
if [[ -z "$HOST" ]]; then
  echo "Usage: $0 <deck-host-or-ip> [version-tag]" >&2
  exit 2
fi
VERSION="${2:-latest}"
USER="${SSH_USER:-deck}"
REPO="${REPO:-GordinRoman/decky-amnezia}"
ASSET="${ASSET:-AmneziaWG.zip}"
PLUGIN_NAME="${ASSET%.zip}"

if [[ "$VERSION" == "latest" ]]; then
  URL="https://github.com/${REPO}/releases/latest/download/${ASSET}"
else
  URL="https://github.com/${REPO}/releases/download/${VERSION}/${ASSET}"
fi

echo "→ Target  : ${USER}@${HOST}"
echo "→ Source  : ${URL}"
echo

# 1) Download + extract + chmod (no sudo needed — everything in ~/homebrew)
ssh -o ConnectTimeout=10 "${USER}@${HOST}" bash -s <<EOF
set -euo pipefail
echo "  · downloading ${ASSET}…"
curl -fL --progress-bar -o "/tmp/${ASSET}" "${URL}"
echo "  · removing old install (if any)…"
rm -rf "\$HOME/homebrew/plugins/${PLUGIN_NAME}"
mkdir -p "\$HOME/homebrew/plugins"
echo "  · extracting to ~/homebrew/plugins/${PLUGIN_NAME}…"
unzip -q "/tmp/${ASSET}" -d "\$HOME/homebrew/plugins/"
chmod +x "\$HOME/homebrew/plugins/${PLUGIN_NAME}/bin/"*
rm "/tmp/${ASSET}"
mkdir -p "\$HOME/.config/amneziawg"
EOF

# 2) Restart decky-loader so it picks up the plugin (needs sudo, separate ssh -t for password prompt)
echo "  · restarting plugin_loader.service…"
ssh -t "${USER}@${HOST}" "sudo systemctl restart plugin_loader.service"

echo
echo "✓ Plugin installed on ${HOST}"
echo
echo "Drop your .conf into ~/.config/amneziawg/ on the deck, e.g.:"
echo "  scp ./amnezia.conf ${USER}@${HOST}:~/.config/amneziawg/"
