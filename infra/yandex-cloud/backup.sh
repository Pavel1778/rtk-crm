#!/bin/bash
# Бэкап PostgreSQL из docker-контейнера rtk_postgres.
# Установка в cron: ln -s /opt/rtk-crm/infra/yandex-cloud/backup.sh /etc/cron.daily/rtk-backup
set -euo pipefail

CONTAINER="${CONTAINER:-rtk_postgres}"
DB_USER="${POSTGRES_USER:-rtk_user}"
DB_NAME="${POSTGRES_DB:-rtk_crm}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

mkdir -p "$BACKUP_DIR"
DUMP_FILE="$BACKUP_DIR/rtk-crm-$(date +%Y%m%d).sql"

echo "==> Дамп базы $DB_NAME -> $DUMP_FILE"
docker exec "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$DUMP_FILE"
gzip -f "$DUMP_FILE"

echo "==> Удаление бэкапов старше $RETENTION_DAYS дней"
find "$BACKUP_DIR" -name 'rtk-crm-*.sql.gz' -mtime "+$RETENTION_DAYS" -delete

echo "==> Готово: ${DUMP_FILE}.gz"
