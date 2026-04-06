#!/usr/bin/env bash
# Daily database backup — run via cron as deploy user.
# Cron entry: 0 2 * * * /opt/ai-namer/scripts/backup-db.sh >> /opt/backups/db/backup.log 2>&1

set -euo pipefail

APP_DIR="/opt/ai-namer"
BACKUP_DIR="/opt/backups/db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ai-namer-$TIMESTAMP.sql.gz"
RETENTION_DAYS=30

cd "$APP_DIR"

echo "[$TIMESTAMP] Starting backup..."

docker compose -f compose.yml -f compose.prod.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_FILE"

echo "[$TIMESTAMP] Backup written to $BACKUP_FILE ($(du -sh "$BACKUP_FILE" | cut -f1))"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "ai-namer-*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
echo "[$TIMESTAMP] Cleaned up backups older than $RETENTION_DAYS days"
