#!/usr/bin/env bash
# =============================================================================
# server-setup.sh — Provision a fresh Debian server for AI-Namer
# =============================================================================
# Run as root on a clean Debian server.
#
# What this script does:
#   1. Reads configuration from scripts/deploy.conf
#   2. Updates system packages
#   3. Installs Docker CE + Compose plugin
#   4. Opens UFW ports 80 (frontend) and 8000 (backend API)
#   5. Creates a non-root deploy user with Docker access
#   6. Creates required directories
#
# Usage:
#   bash scripts/server-setup.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="$SCRIPT_DIR/deploy.conf"

if [[ ! -f "$CONF" ]]; then
  echo "ERROR: $CONF not found. Copy scripts/deploy.conf and fill in your values."
  exit 1
fi

# shellcheck source=deploy.conf
source "$CONF"

echo "==================================================================="
echo " AI-Namer Server Setup"
echo " Deploy user: $DEPLOY_USER"
echo " App dir:     $APP_DIR"
echo "==================================================================="
echo ""

# --- 1. System update --------------------------------------------------------
echo ">>> [1/6] Updating system packages..."
apt-get update -y
apt-get upgrade -y

# --- 2. Docker ---------------------------------------------------------------
echo ">>> [2/6] Installing Docker CE..."
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg \
  | gpg --batch --yes --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Docker CE only officially supports up to Debian 12 (bookworm).
# Map newer codenames (trixie, forky, ...) to bookworm as fallback.
DOCKER_CODENAME=$(. /etc/os-release && case "$VERSION_CODENAME" in
  trixie|forky) echo "bookworm" ;;
  *) echo "$VERSION_CODENAME" ;;
esac)

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian $DOCKER_CODENAME stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
echo "    Docker $(docker --version) installed."

# --- 3. UFW ------------------------------------------------------------------
echo ">>> [3/6] Configuring UFW..."
# SSH must already be allowed — we only add the app ports
ufw allow 80/tcp    # frontend
ufw allow 8000/tcp  # backend API
ufw --force enable
echo "    UFW status:"
ufw status

# --- 4. Deploy user ----------------------------------------------------------
echo ">>> [4/6] Creating deploy user '$DEPLOY_USER'..."
if ! id "$DEPLOY_USER" &>/dev/null; then
  adduser --disabled-password --gecos "" "$DEPLOY_USER"
fi
usermod -aG docker "$DEPLOY_USER"

mkdir -p "/home/$DEPLOY_USER/.ssh"
if [[ -f /root/.ssh/authorized_keys ]]; then
  cp /root/.ssh/authorized_keys "/home/$DEPLOY_USER/.ssh/authorized_keys"
  chown -R "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
  chmod 700 "/home/$DEPLOY_USER/.ssh"
  chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
fi

# --- 5. Directories ----------------------------------------------------------
echo ">>> [5/6] Creating directories..."
mkdir -p "$BACKUP_DIR"
chown "$DEPLOY_USER:$DEPLOY_USER" "$BACKUP_DIR"
mkdir -p "$APP_DIR"
chown "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"

# --- 6. Deploy SSH key -------------------------------------------------------
echo ">>> [6/6] Generating deploy SSH key..."
su - "$DEPLOY_USER" -c "
  if [[ ! -f ~/.ssh/id_ed25519 ]]; then
    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ''
    cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
    echo '    SSH key generated.'
  else
    echo '    SSH key already exists, skipping.'
  fi
"

# --- Done --------------------------------------------------------------------
echo ""
echo "==================================================================="
echo " Setup complete!"
echo ""
echo " Next steps:"
echo "   1. Copy the private key below into GitHub Secret SERVER_SSH_KEY"
echo ""
cat "/home/$DEPLOY_USER/.ssh/id_ed25519"
echo ""
echo "   2. Set GitHub Secrets:"
echo "      SERVER_HOST = $(curl -s ifconfig.me 2>/dev/null || echo '<server-ip>')"
echo "      SERVER_USER = $DEPLOY_USER"
echo "      SERVER_SSH_KEY = <key printed above>"
echo ""
echo "   3. Set GitHub Variable:"
echo "      APP_DOMAIN = <your-domain-or-ip>"
echo ""
echo "   4. Clone repo and configure .env on server:"
echo "      su - $DEPLOY_USER"
echo "      git clone <repo-url> $APP_DIR"
echo "      cp $APP_DIR/.env.example $APP_DIR/.env && nano $APP_DIR/.env"
echo ""
echo "   5. Start app:"
echo "      docker compose -f compose.yml -f compose.prod.yml up -d"
echo ""
echo " Full guide: docs/deployment-server.md"
echo "==================================================================="
