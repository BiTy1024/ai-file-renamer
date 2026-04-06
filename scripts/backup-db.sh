#!/usr/bin/env bash
# =============================================================================
# backup-db.sh — Daily PostgreSQL backup
# =============================================================================
# Reads configuration from scripts/deploy.conf.
#
# Install via cron (as deploy user):
#   crontab -e
#   0 2 * * * /opt/ai-namer/scripts/backup-db.sh >> /opt/backups/db/backup.log 2>&1
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="$SCRIPT_DIR/deploy.conf"

if [[ ! -f "$CONF" ]]; then
  echo "ERROR: $CONF not found."
  exit 1
fi

source "$CONF"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ai-namer-$TIMESTAMP.sql.gz"

cd "$APP_DIR"

echo "[$TIMESTAMP] Starting backup..."

docker compose -f compose.yml -f compose.prod.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_FILE"

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[$TIMESTAMP] Backup written: $BACKUP_FILE ($SIZE)"

# Remove old backups beyond retention period
find "$BACKUP_DIR" -name "ai-namer-*.sql.gz" -mtime +"$BACKUP_RETENTION_DAYS" -delete
echo "[$TIMESTAMP] Cleaned up backups older than $BACKUP_RETENTION_DAYS days."
