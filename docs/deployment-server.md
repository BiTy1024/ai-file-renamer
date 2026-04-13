# Server Deployment Guide

Deploys AI-Namer to a single Debian server.  
Frontend runs on port 80, backend API on port 8000. No reverse proxy.

**Single file to configure:** `scripts/deploy.conf`

---

## Quick Start

```
1. Edit scripts/deploy.conf
2. SSH into server as root, run: bash scripts/server-setup.sh
3. Set GitHub Secrets + Variables (output by setup script)
4. Clone repo, configure .env, start Docker stack
```

---

## Step 0: Configure deploy.conf

Edit `scripts/deploy.conf` before running anything:

```bash
DEPLOY_USER=deploy             # Non-root user to create
APP_DIR=/opt/ai-namer          # Where the app lives on the server
GHCR_OWNER=your-github-username
BACKUP_RETENTION_DAYS=30
BACKUP_DIR=/opt/backups/db
```

---

## Step 1: Remove existing software (if any)

If your server has other software running on port 80 or 8000, stop it first.

---

## Step 2: Run the setup script

SSH into the server as root, then:

```bash
bash scripts/server-setup.sh
```

This installs Docker CE, configures UFW (opens port 80 + 8000), creates the deploy user, and generates a deploy SSH key.

The script prints the private SSH key and server IP at the end — you need both for GitHub Secrets.

---

## Step 3: Set GitHub Secrets and Variables

### Secrets (GitHub → Settings → Secrets → Actions)

| Secret | Value |
|--------|-------|
| `SERVER_HOST` | Server IP (printed by setup script) |
| `SERVER_USER` | `deploy` (or value from deploy.conf) |
| `SERVER_SSH_KEY` | Private key (printed by setup script) |

### Variables (GitHub → Settings → Variables → Actions)

| Variable | Value |
|----------|-------|
| `APP_DOMAIN` | Server IP or domain (e.g. `123.45.67.89` or `ai.example.com`) |
| `APP_DIR` | App directory on server (e.g. `/opt/ai-namer`) |

---

## Step 4: First Deploy (Manual)

### Clone the repository

```bash
su - deploy
git clone https://github.com/<your-org>/ai-file-renamer.git /opt/ai-namer
cd /opt/ai-namer
```

### Configure .env

```bash
cp .env.example .env
nano .env
```

Minimum required values:

```env
DOMAIN=<server-ip-or-domain>
FRONTEND_HOST=http://<server-ip-or-domain>
ENVIRONMENT=production
BACKEND_CORS_ORIGINS=http://<server-ip-or-domain>

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
curl http://<server-ip>:8000/api/v1/utils/health-check/
```

The frontend is then accessible at `http://<server-ip>/`.

---

## Step 5: GitHub Actions CI/CD

On every push to `main` (after lint + tests pass):

1. Builds backend and frontend Docker images
2. Pushes to GHCR tagged with git SHA + `latest`
3. SSHs into server, pulls new images, restarts stack
4. Migrations run automatically via the `prestart` container
5. Health checks `http://<APP_DOMAIN>:8000/api/v1/utils/health-check/`

---

## Step 6: Automated Backups

```bash
chmod +x /opt/ai-namer/scripts/backup-db.sh

# Install cron job (as deploy user)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/ai-namer/scripts/backup-db.sh >> /opt/backups/db/backup.log 2>&1") | crontab -
```

Backups are stored in `BACKUP_DIR` (from deploy.conf) and kept for `BACKUP_RETENTION_DAYS` days.

### Restore from backup

```bash
gunzip -c /opt/backups/db/ai-namer-<TIMESTAMP>.sql.gz | \
  docker compose -f compose.yml -f compose.prod.yml exec -T db \
  psql -U $POSTGRES_USER $POSTGRES_DB
```

---

## Rollback

```bash
cd /opt/ai-namer
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

# Firewall status
ufw status
```
