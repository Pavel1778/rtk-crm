#!/bin/bash
# Первичная настройка ВМ в Yandex Cloud (Ubuntu 22.04/24.04).
# Использование: sudo bash setup-vm.sh  (или как user-data при создании ВМ)
#
# Репозиторий приватный, поэтому для клонирования нужен один из вариантов:
#   GITHUB_TOKEN=ghp_... sudo -E bash setup-vm.sh   # HTTPS + токен
#   DEPLOY_KEY=/path/to/key sudo -E bash setup-vm.sh # SSH + deploy key
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Pavel1778/rtk-crm.git}"
REPO_BRANCH="${REPO_BRANCH:-dev}"
APP_DIR="${APP_DIR:-/opt/rtk-crm}"
SWAP_SIZE="${SWAP_SIZE:-2G}"

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

echo "==> Swap $SWAP_SIZE (нужен для сборки фронтенда: node_modules + vite)"
if [ ! -f /swapfile ]; then
  fallocate -l "$SWAP_SIZE" /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "Swap $SWAP_SIZE создан"
else
  echo "Swap уже существует, пропускаем"
fi

echo "==> Файрвол"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Клонирование репозитория в $APP_DIR"
# Приватный репозиторий: обычный https-clone в неинтерактивном скрипте
# зависает на запросе логина. Токен подставляется в URL только на время
# клонирования и не сохраняется в .git/config.
CLONE_URL="$REPO_URL"
if [ -n "${GITHUB_TOKEN:-}" ]; then
  CLONE_URL="$(printf '%s' "$REPO_URL" | sed "s#https://#https://x-access-token:${GITHUB_TOKEN}@#")"
fi

if [ ! -d "$APP_DIR/.git" ]; then
  if [ -n "${DEPLOY_KEY:-}" ]; then
    export GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o StrictHostKeyChecking=accept-new"
    CLONE_URL="git@github.com:Pavel1778/rtk-crm.git"
  fi
  git clone --branch "$REPO_BRANCH" "$CLONE_URL" "$APP_DIR"
  # Убираем токен из remote, чтобы он не лежал в .git/config открытым текстом.
  git -C "$APP_DIR" remote set-url origin "$REPO_URL"
else
  git -C "$APP_DIR" pull --ff-only
fi

if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/infra/yandex-cloud/.env.prod.example" "$APP_DIR/.env"
  echo "!! Заполните секреты в $APP_DIR/.env перед запуском"
fi

chmod +x "$APP_DIR/infra/yandex-cloud/backup.sh"
chmod +x "$APP_DIR/infra/yandex-cloud/nginx-entrypoint.sh"
ln -sf "$APP_DIR/infra/yandex-cloud/backup.sh" /etc/cron.daily/rtk-backup

cat <<EOF

Готово. Дальнейшие шаги:
  1. Заполнить $APP_DIR/.env (SECRET_KEY, POSTGRES_PASSWORD, DOMAIN, TLS_ENABLED)
  2. Запустить стек:
     cd $APP_DIR && docker compose -f infra/yandex-cloud/docker-compose.prod.yml --env-file .env up -d --build
  3. Для TLS=true сначала выпустить сертификат (нужен свободный порт 80):
     certbot certonly --standalone -d <DOMAIN> -d www.<DOMAIN>
EOF

