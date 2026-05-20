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

echo "→ Target : ${USER}@${HOST}"
echo "→ Source : ${URL}"
echo

# Hint about SSH key auth — without it, you'll get prompted for the SSH
# password on every step.
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "${USER}@${HOST}" true 2>/dev/null; then
  cat >&2 <<MSG
⚠ SSH key auth is not set up for ${USER}@${HOST}.
  You will be prompted for the SSH password below.
  To skip this in the future, run once:
      ssh-copy-id ${USER}@${HOST}

MSG
fi

# Build the remote-side script. Everything happens in one shot so that
# the TTY allocated by `ssh -t` is held end-to-end — both the SSH
# password prompt (if any) and the sudo password prompt for the
# plugin_loader restart read from the same controlling terminal.
REMOTE_SCRIPT=$(cat <<EOF
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
echo "  · restarting plugin_loader.service (sudo)…"
sudo systemctl restart plugin_loader.service
echo "  · done"
EOF
)

# Base64-encode the script so we don't have to fight shell quoting when
# embedding it into the ssh command line. The remote bash decodes it and
# evaluates — sudo inside reads its password from /dev/tty (allocated by -t).
ENCODED=$(printf '%s' "$REMOTE_SCRIPT" | base64 | tr -d '\n')

ssh -t -o ConnectTimeout=10 "${USER}@${HOST}" \
  "echo $ENCODED | base64 -d | bash"

echo
echo "✓ Plugin installed on ${HOST}"
echo
echo "Drop your .conf into ~/.config/amneziawg/ on the deck, e.g.:"
echo "  scp ./amnezia.conf ${USER}@${HOST}:~/.config/amneziawg/"
