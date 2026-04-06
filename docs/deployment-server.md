# Server Deployment Guide

Deploys AI-Namer to a single Debian server with Nginx as reverse proxy.
Frontend and backend share one domain (`ai.bookpass.de`). Nginx routes `/api/*` to the backend, everything else to the frontend.

## Prerequisites

- Debian server (tested on Debian 12)
- SSH access as root
- DNS A records pointing to the server IP (see Step 0)
- GitHub repository secrets configured (see Step 5)

---

## Step 0: DNS Configuration (all-inkl.com)

Set these A records before running Certbot:

| Hostname | Type | Value |
|----------|------|-------|
| `ai.bookpass.de` | A | `<server-ip>` |
| `mybookhub.de` | A | `<server-ip>` |
| `www.mybookhub.de` | A | `<server-ip>` |

DNS propagation takes up to 24h, but usually under 10 minutes.

---

## Step 1: Remove OpenClaw

```bash
# Check what's running
systemctl list-units | grep -i claw
which openclaw

# Stop and remove
systemctl stop openclaw 2>/dev/null || true
systemctl disable openclaw 2>/dev/null || true
npm uninstall -g openclaw 2>/dev/null || true

# Remove Node.js if not needed for anything else
apt remove --purge -y nodejs npm
rm -rf /root/.npm /root/.openclaw ~/.local/share/openclaw

# Remove any lingering service file
rm -f /etc/systemd/system/openclaw.service
systemctl daemon-reload

# Verify
systemctl list-units | grep -i claw  # should be empty
```

---

## Step 2: Server Base Setup

Run the provisioning script (installs Docker, Nginx, Certbot, UFW, creates deploy user):

```bash
curl -fsSL https://raw.githubusercontent.com/BiTy1024/ai-file-renamer/main/scripts/server-setup.sh | bash
```

Or clone the repo first and run locally:

```bash
bash /opt/ai-namer/scripts/server-setup.sh
```

What it does:
- `apt upgrade` + installs Docker CE + Compose plugin
- Installs Nginx + Certbot
- UFW: opens ports 80 and 443
- Creates `deploy` user in docker group with same SSH key as root

---

## Step 3: Nginx Configuration

### AI-Namer (ai.bookpass.de)

```bash
cp /opt/ai-namer/scripts/nginx/ai.bookpass.de.conf /etc/nginx/sites-available/ai.bookpass.de
ln -s /etc/nginx/sites-available/ai.bookpass.de /etc/nginx/sites-enabled/ai.bookpass.de
nginx -t && systemctl reload nginx
```

### mybookhub.de (placeholder — managed by another team)

```bash
mkdir -p /var/www/mybookhub.de
cp /opt/ai-namer/scripts/nginx/mybookhub.de.conf /etc/nginx/sites-available/mybookhub.de
ln -s /etc/nginx/sites-available/mybookhub.de /etc/nginx/sites-enabled/mybookhub.de
nginx -t && systemctl reload nginx
```

### Remove default Nginx site

```bash
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

---

## Step 4: SSL Certificates

DNS must be propagated before running Certbot.

```bash
certbot --nginx -d ai.bookpass.de
certbot --nginx -d mybookhub.de -d www.mybookhub.de
```

Certbot auto-configures HTTPS redirect and HTTP/2. Renewal is automatic via systemd timer (`certbot.timer`).

Verify renewal works:

```bash
certbot renew --dry-run
```

---

## Step 5: First Deploy (Manual)

### 5a. Clone the repository

```bash
# As deploy user
su - deploy
git clone https://github.com/BiTy1024/ai-file-renamer.git /opt/ai-namer
cd /opt/ai-namer
```

### 5b. Create .env

```bash
cp .env.example .env
```

Edit `.env` with production values:

```env
DOMAIN=ai.bookpass.de
FRONTEND_HOST=https://ai.bookpass.de
ENVIRONMENT=production
PROJECT_NAME=AI-Namer
STACK_NAME=ai-namer

BACKEND_CORS_ORIGINS=https://ai.bookpass.de
SECRET_KEY=<generate: python3 -c "import secrets; print(secrets.token_hex(32))">
FIRST_SUPERUSER=admin@yourdomain.com
FIRST_SUPERUSER_PASSWORD=<strong-password>

# Email (optional — alerts won't send without this)
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
EMAILS_FROM_EMAIL=
SMTP_TLS=True
SMTP_SSL=False
SMTP_PORT=587

POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<generate: python3 -c "import secrets; print(secrets.token_hex(16))">

# Docker images (updated automatically by CI/CD after first deploy)
DOCKER_IMAGE_BACKEND=ghcr.io/bity1024/ai-namer-backend
DOCKER_IMAGE_FRONTEND=ghcr.io/bity1024/ai-namer-frontend
TAG=latest
```

### 5c. Log in to GHCR and start the stack

```bash
# Log in to GitHub Container Registry
echo $GITHUB_PAT | docker login ghcr.io -u BiTy1024 --password-stdin

# Start stack
docker compose -f compose.yml -f compose.prod.yml up -d

# Check status
docker compose -f compose.yml -f compose.prod.yml ps
docker compose -f compose.yml -f compose.prod.yml logs -f
```

### 5d. Verify

```bash
curl https://ai.bookpass.de/api/v1/utils/health-check/
# → {"status":"ok"}
```

---

## Step 6: GitHub Actions CI/CD

### Required Secrets (GitHub → Settings → Secrets → Actions)

| Secret | Value |
|--------|-------|
| `SERVER_HOST` | Server IP address |
| `SERVER_USER` | `deploy` |
| `SERVER_SSH_KEY` | Private key of the deploy user (content of `~/.ssh/id_ed25519`) |
| `GOOGLE_SA_CREDENTIALS_JSON` | Google service account JSON (for integration tests) |
| `GOOGLE_TEST_FOLDER_ID` | Google Drive folder ID for tests |

### How it works

On every push to `main` (after lint + tests pass):

1. Builds backend and frontend Docker images
2. Pushes to `ghcr.io/bity1024/ai-namer-backend` and `ghcr.io/bity1024/ai-namer-frontend` tagged with git SHA + `latest`
3. SSHs into server as `deploy`
4. Pulls new images, restarts stack with `--remove-orphans`
5. Runs `alembic upgrade head` for migrations
6. Health checks `https://ai.bookpass.de/api/v1/utils/health-check/`

### Generate deploy SSH key

```bash
# On the server as deploy user
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys

# Copy private key to GitHub secret
cat ~/.ssh/id_ed25519
```

---

## Step 7: Automated Backups

Install the backup cron job (runs daily at 02:00):

```bash
# As deploy user
crontab -e
# Add:
0 2 * * * /opt/ai-namer/scripts/backup-db.sh >> /opt/backups/db/backup.log 2>&1
```

Make the script executable:

```bash
chmod +x /opt/ai-namer/scripts/backup-db.sh
```

Backups are stored in `/opt/backups/db/` and retained for 30 days.

### Restore from backup

```bash
gunzip -c /opt/backups/db/ai-namer-<TIMESTAMP>.sql.gz | \
  docker compose -f compose.yml -f compose.prod.yml exec -T db \
  psql -U $POSTGRES_USER $POSTGRES_DB
```

---

## Rollback

Each deploy tags images with the git SHA. To roll back to a previous version:

```bash
cd /opt/ai-namer

# Find the previous SHA from git log or GHCR
PREVIOUS_SHA=<git-sha>

# Update .env
sed -i "s|TAG=.*|TAG=$PREVIOUS_SHA|" .env

# Restart with old images
docker compose -f compose.yml -f compose.prod.yml pull
docker compose -f compose.yml -f compose.prod.yml up -d
```

---

## Useful Commands

```bash
# View running containers
docker compose -f compose.yml -f compose.prod.yml ps

# Tail logs
docker compose -f compose.yml -f compose.prod.yml logs -f backend
docker compose -f compose.yml -f compose.prod.yml logs -f frontend

# Run migrations manually
docker compose -f compose.yml -f compose.prod.yml exec backend alembic upgrade head

# Open adminer (debug profile — only when needed)
docker compose -f compose.yml -f compose.prod.yml --profile debug up -d adminer
# Then SSH tunnel: ssh -L 8080:127.0.0.1:8080 deploy@<server>

# Check SSL cert expiry
certbot certificates

# Check UFW status
ufw status
```
