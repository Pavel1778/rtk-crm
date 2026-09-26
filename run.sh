#!/usr/bin/env bash
# ============================================================
#  RTK CRM — Universal Launcher (Docker Compose)
#  Работает из любой директории
# ============================================================

set -uo pipefail

# --- Цвета ---
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; B='\033[0;34m'
C='\033[0;36m'; M='\033[0;35m'; NC='\033[0m'

# --- Корень проекта (там, где лежит скрипт) ---
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
ROOT="$(cd -P "$(dirname "$SOURCE")" && pwd)"
cd "$ROOT"

# --- Docker Compose команда ---
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  echo -e "${R}✗ Docker Compose не найден${NC}"
  exit 1
fi

# --- Helper ---
banner() {
  echo ""
  echo -e "${B}╔══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${B}║${NC}      ${M}RTK CRM — Local Launcher (Docker Compose)${NC}            ${B}║${NC}"
  echo -e "${B}║${NC}      ${C}$ROOT${NC}"
  echo -e "${B}╚══════════════════════════════════════════════════════════╝${NC}"
  echo ""
}

ok()    { echo -e "${G}✓${NC} $1"; }
warn()  { echo -e "${Y}⚠${NC} $1"; }
err()   { echo -e "${R}✗${NC} $1"; }
info()  { echo -e "${C}ℹ${NC} $1"; }

# --- Проверки окружения ---
check_docker() {
  if ! docker info >/dev/null 2>&1; then
    err "Docker daemon не запущен"
    echo "  → Windows: запусти Docker Desktop"
    echo "  → Linux:   sudo systemctl start docker"
    exit 1
  fi
  ok "Docker работает"
}

check_compose() {
  if [ ! -f "$ROOT/docker-compose.yml" ]; then
    err "docker-compose.yml не найден в $ROOT"
    exit 1
  fi
  if ! $DC config >/dev/null 2>&1; then
    err "YAML в docker-compose.yml невалиден"
    echo "  → Запусти: $DC config"
    exit 1
  fi
  ok "docker-compose.yml валиден"
}

check_env() {
  # backend/.env
  if [ ! -f "$ROOT/backend/.env" ] && [ -f "$ROOT/backend/.env.example" ]; then
    cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"
    warn "Создан backend/.env из .env.example"
  fi

  # frontend/.env
  if [ ! -f "$ROOT/frontend/.env" ] && [ -f "$ROOT/frontend/.env.example" ]; then
    cp "$ROOT/frontend/.env.example" "$ROOT/frontend/.env"
    warn "Создан frontend/.env из .env.example"
  fi
  ok ".env файлы на месте"
}

check_db_creds() {
  local url
  url=$(grep -oE 'DATABASE_URL:\s*"[^"]+' "$ROOT/docker-compose.yml" 2>/dev/null | head -1 | sed 's/.*"//')
  if [ -z "$url" ]; then
    url=$(grep -oE '^DATABASE_URL=.*' "$ROOT/backend/.env" 2>/dev/null | head -1 | sed 's/^DATABASE_URL=//')
  fi

  if [ -z "$url" ]; then
    err "DATABASE_URL не найден ни в docker-compose.yml, ни в backend/.env"
    exit 1
  fi

  if echo "$url" | grep -q "НОВЫЙ_ПАРОЛЬ\|YOUR_PASSWORD\|\[YOUR-PASSWORD\]\|PASSWORD_HERE"; then
    err "DATABASE_URL содержит placeholder вместо реального пароля"
    echo "  → Укажите строку подключения PostgreSQL (managed-кластер или контейнер)"
    echo "  → Замени пароль в $ROOT/docker-compose.yml"
    exit 1
  fi

  ok "DATABASE_URL настроен"
}

# --- Действия ---
do_start() {
  banner
  check_docker
  check_compose
  check_env
  check_db_creds

  echo ""
  info "Запускаю контейнеры (down + up)..."
  $DC down --remove-orphans >/dev/null 2>&1 || true
  $DC up -d --build

  echo ""
  info "Жду готовности backend (до 90 сек)..."
  local i=0
  while [ $i -lt 45 ]; do
    if docker logs rtk_backend 2>&1 | grep -q "Application startup complete"; then
      ok "Backend готов"
      break
    fi
    sleep 2
    i=$((i+1))
    printf "."
  done
  echo ""

  if [ $i -ge 45 ]; then
    warn "Backend не ответил за 90 сек — проверь логи: $DC logs backend"
    return 1
  fi

  echo ""
  info "Проверяю подключение к базе данных..."
  if ! docker exec rtk_backend python -c "
import asyncio, os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
url = os.environ.get('DATABASE_URL','')
engine = create_async_engine(url)
async def c():
    async with engine.connect() as conn:
        await conn.execute(text('SELECT 1'))
asyncio.run(c())
" >/dev/null 2>&1; then
    err "Backend не может подключиться к базе данных"
    return 1
  fi
  ok "База данных доступна"

  echo ""
  info "Проверяю таблицы..."
  local tables
  tables=$(docker exec rtk_backend python -c "
import asyncio
from app.db.session import engine
from sqlalchemy import text
async def c():
    async with engine.connect() as conn:
        r = await conn.execute(text(\"SELECT count(*) FROM pg_tables WHERE schemaname='public'\"))
        print(r.scalar())
asyncio.run(c())
" 2>/dev/null | tail -1)

  if [ "${tables:-0}" -lt 5 ] 2>/dev/null; then
    warn "Таблиц мало или нет ($tables). Запускаю миграции..."
    docker exec rtk_backend alembic upgrade head 2>/dev/null || \
      docker exec rtk_backend python -c "
import asyncio
from app.db.session import engine, Base
import app.models.entities
async def c():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(c())
"
    ok "Таблицы созданы"
  else
    ok "Таблиц: $tables"
  fi

  echo ""
  info "Проверяю пользователей..."
  local users
  users=$(docker exec rtk_backend python -c "
import asyncio
from app.db.session import engine
from sqlalchemy import text
async def c():
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT count(*) FROM users'))
        print(r.scalar())
asyncio.run(c())
" 2>/dev/null | tail -1)

  if [ "${users:-0}" -lt 1 ] 2>/dev/null; then
    warn "Пользователей нет. Запускаю seed..."
    docker exec rtk_backend python -m app.seed 2>&1 | tail -5
    ok "Seed выполнен"
  else
    ok "Пользователей: $users"
  fi

  echo ""
  info "Список учётных записей:"
  docker exec rtk_backend python -c "
import asyncio
from app.db.session import engine
from sqlalchemy import text
async def c():
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT email, role FROM users ORDER BY id'))
        for row in r: print(f'  • {row[0]:<25} [{row[1]}]')
asyncio.run(c())
" 2>/dev/null

  echo ""
  echo -e "${G}╔══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${G}║${NC}            ${G}✓ RTK CRM ЗАПУЩЕН${NC}                             ${G}║${NC}"
  echo -e "${G}╚══════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${C}Frontend:${NC}   http://localhost:3000"
  echo -e "  ${C}Backend:${NC}    http://localhost:8000/docs"
  echo -e "  ${C}Keycloak:${NC}   http://localhost:8080  (admin/admin)"
  echo -e "  ${C}Nginx:${NC}      http://localhost"
  echo ""
}

do_reset_password() {
  local email="${1:-admin@rtk.ru}"
  local newpass="${2:-admin123}"

  info "Сброс пароля для $email..."

  cat > /tmp/reset_admin.py << EOF
import asyncio, sys
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import User

# Пробуем разные пути к функции хэширования
try:
    from app.auth.security import get_password_hash
except ImportError:
    try:
        from app.core.security import get_password_hash
    except ImportError:
        from app.services.auth import get_password_hash

async def main():
    async with SessionLocal() as db:
        r = await db.execute(select(User).where(User.email == "$email"))
        user = r.scalar_one_or_none()
        if not user:
            print(f"Пользователь $email не найден")
            return
        user.hashed_password = get_password_hash("$newpass")
        user.is_active = True
        await db.commit()
        print(f"OK: {user.email} → пароль '$newpass'")

asyncio.run(main())
EOF

  docker cp /tmp/reset_admin.py rtk_backend:/tmp/reset_admin.py
  docker exec rtk_backend python /tmp/reset_admin.py
}

do_seed() {
  info "Запускаю seed..."
  docker exec rtk_backend python -m app.seed 2>&1 | tail -20
  do_users
}

do_migrations() {
  info "Применяю миграции..."
  docker exec rtk_backend alembic upgrade head 2>&1 | tail -10
}

do_users() {
  echo ""
  info "Пользователи в базе:"
  docker exec rtk_backend python -c "
import asyncio
from app.db.session import engine
from sqlalchemy import text
async def c():
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT email, role, is_active FROM users ORDER BY id'))
        for row in r: print(f'  {row[0]:<25} [{row[1]:<8}] active={row[2]}')
asyncio.run(c())
" 2>/dev/null
}

do_status() {
  banner
  echo -e "${C}=== Контейнеры ===${NC}"
  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "rtk_|NAMES" || echo "  нет запущенных rtk-* контейнеров"
  echo ""
  echo -e "${C}=== Health backend ===${NC}"
  curl -sS -m 5 http://localhost:8000/health 2>/dev/null || echo "  (нет ответа)"
  echo ""
  echo ""
  echo -e "${C}=== Пользователи ===${NC}"
  do_users
}

do_logs() {
  echo "Выбери контейнер:"
  echo "  1. backend"
  echo "  2. frontend"
  echo "  3. keycloak"
  echo "  4. nginx"
  echo "  5. все"
  read -rp "Твой выбор [1-5]: " c
  case "$c" in
    1) docker logs rtk_backend -f --tail 50 ;;
    2) docker logs rtk_frontend -f --tail 50 ;;
    3) docker logs rtk_keycloak -f --tail 50 ;;
    4) docker logs rtk_nginx -f --tail 50 ;;
    5) $DC logs -f --tail 30 ;;
  esac
}

do_shell_backend() {
  MSYS_NO_PATHCONV=1 docker exec -it rtk_backend bash 2>/dev/null || \
  MSYS_NO_PATHCONV=1 docker exec -it rtk_backend sh
}

do_shell_db() {
  docker exec -it rtk_backend python -c "
import asyncio
from app.db.session import engine
from sqlalchemy import text
async def c():
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT current_database(), current_user, version()'))
        print(r.first())
asyncio.run(c())
"
}

do_open() {
  info "Открываю браузер..."
  if command -v start >/dev/null 2>&1; then
    start http://localhost:3000
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open http://localhost:3000
  elif command -v open >/dev/null 2>&1; then
    open http://localhost:3000
  else
    echo "  Открой вручную: http://localhost:3000"
  fi
}

do_reset_all() {
  warn "Это удалит все контейнеры и БД (данные во внешней БД НЕ удаляются)"
  read -rp "Продолжить? (yes/no): " c
  if [ "$c" = "yes" ]; then
    $DC down -v --remove-orphans
    ok "Всё удалено. Запусти 'start' для пересборки."
  fi
}

# --- Меню ---
menu() {
  while true; do
    echo ""
    echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${C}Меню:${NC}"
    echo -e "  ${G}1${NC}.  Запустить всё (start)"
    echo -e "  ${G}2${NC}.  Статус (status)"
    echo -e "  ${G}3${NC}.  Логи (logs)"
    echo -e "  ${G}4${NC}.  Перезапустить backend"
    echo -e "  ${G}5${NC}.  Перезапустить frontend"
    echo -e "  ${G}6${NC}.  Применить миграции"
    echo -e "  ${G}7${NC}.  Запустить seed"
    echo -e "  ${G}8${NC}.  Показать пользователей"
    echo -e "  ${G}9${NC}.  Сбросить пароль admin → admin123"
    echo -e "  ${G}10${NC}. Shell внутрь backend"
    echo -e "  ${G}11${NC}. Проверить подключение к БД"
    echo -e "  ${G}12${NC}. Открыть браузер"
    echo -e "  ${G}13${NC}. Полный сброс (down -v)"
    echo -e "  ${G}0${NC}.  Выход"
    echo -e "${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    read -rp "Твой выбор: " choice

    case "$choice" in
      1)  do_start ;;
      2)  do_status ;;
      3)  do_logs ;;
      4)  $DC restart backend && ok "backend перезапущен" ;;
      5)  $DC restart frontend && ok "frontend перезапущен" ;;
      6)  do_migrations ;;
      7)  do_seed ;;
      8)  do_users ;;
      9)  do_reset_password ;;
      10) do_shell_backend ;;
      11) do_shell_db ;;
      12) do_open ;;
      13) do_reset_all ;;
      0)  echo "Пока!"; exit 0 ;;
      *)  err "Неверный выбор" ;;
    esac
  done
}

# --- CLI режим ---
if [ $# -gt 0 ]; then
  case "$1" in
    start)      do_start ;;
    stop)       $DC down ;;
    restart)    $DC restart ;;
    status)     do_status ;;
    logs)       do_logs ;;
    seed)       do_seed ;;
    migrate)    do_migrations ;;
    users)      do_users ;;
    reset-pass) do_reset_password "${2:-admin@rtk.ru}" "${3:-admin123}" ;;
    reset-all)  do_reset_all ;;
    open)       do_open ;;
    *)          echo "Использование: $0 [start|stop|restart|status|logs|seed|migrate|users|reset-pass|reset-all|open]" ;;
  esac
else
  banner
  menu
fi