#!/usr/bin/env bash
# =============================================================================
# server-setup.sh — Provision a fresh Debian server for AI-Namer
# =============================================================================
# Run as root on a clean Debian 12 server.
#
# What this script does:
#   1. Reads configuration from scripts/deploy.conf
#   2. Updates system packages
#   3. Installs Docker CE + Compose plugin
#   4. Installs Nginx + Certbot
#   5. Opens UFW ports 80 and 443
#   6. Creates a non-root deploy user with Docker access
#   7. Creates required directories
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
echo " Domain:      $APP_DOMAIN"
echo " Deploy user: $DEPLOY_USER"
echo " App dir:     $APP_DIR"
echo "==================================================================="
echo ""

# --- 1. System update --------------------------------------------------------
echo ">>> [1/7] Updating system packages..."
apt-get update -y
apt-get upgrade -y

# --- 2. Docker ---------------------------------------------------------------
echo ">>> [2/7] Installing Docker CE..."
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

# --- 3. Nginx + Certbot ------------------------------------------------------
echo ">>> [3/7] Installing Nginx and Certbot..."
apt-get install -y nginx certbot python3-certbot-nginx
systemctl enable nginx
systemctl start nginx
echo "    Nginx $(nginx -v 2>&1 | grep -o '[0-9.]*') installed."

# --- 4. UFW ------------------------------------------------------------------
echo ">>> [4/7] Configuring UFW..."
# SSH must already be allowed — we only add 80 and 443
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
echo "    UFW status:"
ufw status

# --- 5. Deploy user ----------------------------------------------------------
echo ">>> [5/7] Creating deploy user '$DEPLOY_USER'..."
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

# --- 6. Directories ----------------------------------------------------------
echo ">>> [6/7] Creating directories..."
mkdir -p "$BACKUP_DIR"
chown "$DEPLOY_USER:$DEPLOY_USER" "$BACKUP_DIR"
mkdir -p "$APP_DIR"
chown "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"

# --- 7. Nginx vhost ----------------------------------------------------------
echo ">>> [7/7] Generating Nginx vhost for $APP_DOMAIN..."
export APP_DOMAIN FRONTEND_PORT BACKEND_PORT
envsubst '${APP_DOMAIN} ${FRONTEND_PORT} ${BACKEND_PORT}' \
  < "$SCRIPT_DIR/nginx/app.conf.template" \
  > "/etc/nginx/sites-available/$APP_DOMAIN"

rm -f /etc/nginx/sites-enabled/default
ln -sf "/etc/nginx/sites-available/$APP_DOMAIN" "/etc/nginx/sites-enabled/$APP_DOMAIN"
nginx -t && systemctl reload nginx
echo "    Nginx vhost configured for $APP_DOMAIN."

# --- Done --------------------------------------------------------------------
echo ""
echo "==================================================================="
echo " Setup complete!"
echo ""
echo " Next steps:"
echo "   1. Set DNS A record:  $APP_DOMAIN → $(curl -s ifconfig.me 2>/dev/null || echo '<server-ip>')"
echo "   2. Once DNS is live:  certbot --nginx -d $APP_DOMAIN"
echo "   3. Clone repo:        git clone <repo-url> $APP_DIR"
echo "   4. Configure .env:    cp $APP_DIR/.env.example $APP_DIR/.env && edit it"
echo "   5. Start app:         docker compose -f compose.yml -f compose.prod.yml up -d"
echo ""
echo " Full guide: docs/deployment-server.md"
echo "==================================================================="
