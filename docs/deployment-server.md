# Server Deployment Guide

Deploys AI-Namer to a single Debian server with Nginx as reverse proxy.  
Frontend and backend share one domain. Nginx routes `/api/*` to the backend, everything else to the frontend.

**Single file to configure:** `scripts/deploy.conf`

---

## Quick Start

```
1. Edit scripts/deploy.conf
2. Run: bash scripts/server-setup.sh
3. Set DNS A record → server IP
4. Run: certbot --nginx -d <your-domain>
5. Clone repo, configure .env, start Docker stack
6. Set GitHub Actions variables and secrets
```

---

## Step 0: Configure deploy.conf

Edit `scripts/deploy.conf` before running anything:

```bash
APP_DOMAIN=ai.example.com      # Your domain
DEPLOY_USER=deploy             # Non-root user to create
APP_DIR=/opt/ai-namer          # Where the app lives on the server
FRONTEND_PORT=3000             # Must match compose.prod.yml
BACKEND_PORT=8000              # Must match compose.prod.yml
GHCR_OWNER=your-github-username
BACKUP_RETENTION_DAYS=30
BACKUP_DIR=/opt/backups/db
```

---

## Step 1: Set DNS (your DNS provider)

Add an A record before running Certbot:

| Hostname | Type | Value |
|----------|------|-------|
| `<APP_DOMAIN>` | A | `<server-ip>` |

DNS propagation typically takes a few minutes, up to 24h.

---

## Step 2: Remove existing software (if any)

If your server has other software running, stop and remove it before proceeding.  
Example for OpenClaw (Node.js daemon):

```bash
systemctl stop openclaw && systemctl disable openclaw
npm uninstall -g openclaw
apt remove --purge -y nodejs npm
systemctl daemon-reload
```

---

## Step 3: Run the setup script

SSH into the server as root, then:

```bash
bash scripts/server-setup.sh
```

This installs Docker CE, Nginx, Certbot, configures UFW (opens 80 + 443), creates the deploy user, and generates the Nginx vhost from the template.

---

## Step 4: SSL Certificate

Wait for DNS to propagate (`dig <APP_DOMAIN>` should return your server IP), then:

```bash
certbot --nginx -d <APP_DOMAIN>
certbot renew --dry-run   # Verify auto-renewal works
```

Certbot auto-configures HTTPS redirect and HTTP/2.

---

## Step 5: First Deploy (Manual)

### Clone the repository

```bash
su - deploy
git clone https://github.com/<your-org>/ai-file-renamer.git <APP_DIR>
cd <APP_DIR>
```

### Configure .env

```bash
cp .env.example .env
```

Edit `.env` — minimum required values:

```env
DOMAIN=<APP_DOMAIN>                  # Must match deploy.conf APP_DOMAIN
FRONTEND_HOST=https://<APP_DOMAIN>
ENVIRONMENT=production
BACKEND_CORS_ORIGINS=https://<APP_DOMAIN>

SECRET_KEY=<generate: python3 -c "import secrets; print(secrets.token_hex(32))">
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=<strong-password>

POSTGRES_SERVER=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<generate: python3 -c "import secrets; print(secrets.token_hex(16))">
POSTGRES_DB=app

DOCKER_IMAGE_BACKEND=ghcr.io/<GHCR_OWNER>/ai-namer-backend
DOCKER_IMAGE_FRONTEND=ghcr.io/<GHCR_OWNER>/ai-namer-frontend
TAG=latest
```

### Start the stack

```bash
# Log in to GitHub Container Registry
echo <GITHUB_PAT> | docker login ghcr.io -u <GHCR_OWNER> --password-stdin

docker compose -f compose.yml -f compose.prod.yml up -d

# Verify
docker compose -f compose.yml -f compose.prod.yml ps
curl https://<APP_DOMAIN>/api/v1/utils/health-check/
```

---

## Step 6: GitHub Actions CI/CD

### Required Secrets (GitHub → Settings → Secrets → Actions)

| Secret | Value |
|--------|-------|
| `SERVER_HOST` | Server IP |
| `SERVER_USER` | `deploy` (or value from deploy.conf) |
| `SERVER_SSH_KEY` | Private SSH key of the deploy user |

### Required Variables (GitHub → Settings → Variables → Actions)

| Variable | Value |
|----------|-------|
| `APP_DOMAIN` | Your domain (e.g. `ai.example.com`) |
| `APP_DIR` | App directory on server (e.g. `/opt/ai-namer`) |

### Generate a deploy SSH key

```bash
# On the server, as deploy user
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys

# Copy the private key into GitHub Secret SERVER_SSH_KEY
cat ~/.ssh/id_ed25519
```

### How CI/CD works

On every push to `main` (after lint + tests pass):

1. Builds backend and frontend Docker images
2. Pushes to GHCR tagged with git SHA + `latest`
3. SSHs into server, pulls new images, restarts stack
4. Migrations run automatically via the `prestart` container
5. Health checks `https://<APP_DOMAIN>/api/v1/utils/health-check/`

---

## Step 7: Automated Backups

```bash
chmod +x <APP_DIR>/scripts/backup-db.sh

# Install cron job (as deploy user)
(crontab -l 2>/dev/null; echo "0 2 * * * <APP_DIR>/scripts/backup-db.sh >> <BACKUP_DIR>/backup.log 2>&1") | crontab -
```

Backups are stored in `BACKUP_DIR` (from deploy.conf) and kept for `BACKUP_RETENTION_DAYS` days.

### Restore from backup

```bash
gunzip -c <BACKUP_DIR>/ai-namer-<TIMESTAMP>.sql.gz | \
  docker compose -f compose.yml -f compose.prod.yml exec -T db \
  psql -U $POSTGRES_USER $POSTGRES_DB
```

---

## Adding additional sites to Nginx

To host other domains on the same server (e.g. a static site):

```bash
# Create the vhost manually
cat > /etc/nginx/sites-available/example.com << 'EOF'
server {
    listen 80;
    server_name example.com www.example.com;
    root /var/www/example.com;
    index index.html;
    location / { try_files $uri $uri/ =404; }
}
EOF

mkdir -p /var/www/example.com
ln -s /etc/nginx/sites-available/example.com /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d example.com -d www.example.com
```

---

## Rollback

```bash
cd <APP_DIR>
PREVIOUS_SHA=<git-sha>
sed -i "s|^TAG=.*|TAG=$PREVIOUS_SHA|" .env
docker compose -f compose.yml -f compose.prod.yml pull
docker compose -f compose.yml -f compose.prod.yml up -d
```

---

## Useful Commands

```bash
# Container status
docker compose -f compose.yml -f compose.prod.yml ps

# Logs
docker compose -f compose.yml -f compose.prod.yml logs -f backend

# Manual migration
docker compose -f compose.yml -f compose.prod.yml exec backend alembic upgrade head

# Adminer (DB admin, debug only)
docker compose -f compose.yml -f compose.prod.yml --profile debug up -d adminer
# Then: ssh -L 8080:127.0.0.1:8080 deploy@<server>

# SSL cert status
certbot certificates

# Firewall status
ufw status
```
