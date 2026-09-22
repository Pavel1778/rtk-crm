#!/bin/bash
# Первичная настройка ВМ в Yandex Cloud (Ubuntu 22.04).
# Использование: sudo bash setup-vm.sh  (или как user-data при создании ВМ)
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Pavel1778/rtk-crm.git}"
REPO_BRANCH="${REPO_BRANCH:-dev}"
APP_DIR="${APP_DIR:-/opt/rtk-crm}"

echo "==> Обновление пакетов"
apt-get update -y
apt-get upgrade -y

echo "==> Базовые утилиты"
apt-get install -y ca-certificates curl git gnupg ufw

echo "==> Docker + Docker Compose plugin"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

echo "==> Certbot для Let's Encrypt"
apt-get install -y certbot

echo "==> Файрвол"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Клонирование репозитория в $APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone --branch "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi

if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/infra/yandex-cloud/.env.prod.example" "$APP_DIR/.env"
  echo "!! Заполните секреты в $APP_DIR/.env перед запуском"
fi

chmod +x "$APP_DIR/infra/yandex-cloud/backup.sh"
ln -sf "$APP_DIR/infra/yandex-cloud/backup.sh" /etc/cron.daily/rtk-backup

cat <<EOF

Готово. Дальнейшие шаги:
  1. Заполнить $APP_DIR/.env (SECRET_KEY, POSTGRES_PASSWORD, CORS_ORIGINS, VITE_API_URL)
  2. Выпустить сертификат:
     certbot certonly --standalone -d rtk-crm.ru -d www.rtk-crm.ru
  3. Запустить стек:
     cd $APP_DIR && docker compose -f infra/yandex-cloud/docker-compose.prod.yml --env-file .env up -d --build
EOF
