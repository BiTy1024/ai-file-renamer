#!/usr/bin/env bash
# Server provisioning script for Debian
# Run as root on a fresh Debian server.
# Usage: bash scripts/server-setup.sh

set -euo pipefail

DEPLOY_USER="deploy"

echo "=== 1. System update ==="
apt-get update -y
apt-get upgrade -y

echo "=== 2. Install Docker ==="
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

echo "=== 3. Install Nginx + Certbot ==="
apt-get install -y nginx certbot python3-certbot-nginx
systemctl enable nginx
systemctl start nginx

echo "=== 4. Configure UFW ==="
ufw allow 80/tcp
ufw allow 443/tcp
# SSH must already be allowed before running this script
ufw --force enable
ufw status

echo "=== 5. Create deploy user ==="
if ! id "$DEPLOY_USER" &>/dev/null; then
  adduser --disabled-password --gecos "" "$DEPLOY_USER"
fi
usermod -aG docker "$DEPLOY_USER"

# Copy SSH authorized_keys from root so deploy user can log in with same key
mkdir -p "/home/$DEPLOY_USER/.ssh"
cp /root/.ssh/authorized_keys "/home/$DEPLOY_USER/.ssh/authorized_keys"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
chmod 700 "/home/$DEPLOY_USER/.ssh"
chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"

echo "=== 6. Create backup directory ==="
mkdir -p /opt/backups/db
chown "$DEPLOY_USER:$DEPLOY_USER" /opt/backups/db

echo "=== 7. Create app directory ==="
mkdir -p /opt/ai-namer
chown "$DEPLOY_USER:$DEPLOY_USER" /opt/ai-namer

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Set DNS A records for ai.bookpass.de → $(curl -s ifconfig.me)"
echo "  2. Place Nginx vhosts in /etc/nginx/sites-available/ and enable them"
echo "  3. Run: certbot --nginx -d ai.bookpass.de"
echo "  4. Clone repo to /opt/ai-namer and configure .env"
echo "  5. docker compose -f compose.yml -f compose.prod.yml up -d"
