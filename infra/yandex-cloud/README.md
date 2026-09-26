# Миграция RTK CRM в Yandex Cloud

Инструкция рассчитана примерно на час работы. Текущий прод
(Render + Supabase + Vercel) при этом продолжает работать — переключение
выполняется только сменой DNS в самом конце.

## 0. Что получится

```text
Интернет ──► Nginx (443, Let's Encrypt) ──┬──► frontend (React, nginx:80)
                                          └──► backend  (FastAPI, :8000) ──► PostgreSQL 16 (volume)
```

Все компоненты — контейнеры на одной ВМ, описаны в
`infra/yandex-cloud/docker-compose.prod.yml`.

## 1. Создание ВМ

Консоль Yandex Cloud → Compute Cloud → «Создать ВМ»:

| Параметр | Значение |
|---|---|
| Образ | Ubuntu 22.04 или 24.04 LTS |
| Платформа | Intel Ice Lake, прерываемая — нет |
| vCPU / доля | 2 vCPU, 20 % (для демо достаточно) или 100 % для прода |
| RAM | 4 ГБ |
| Диск | 20–30 ГБ |
| Публичный IP | **статический** (нужен для A-записи и сертификата) |
| Доступ | логин `ubuntu`, ваш SSH-ключ |

Публичный IP обязателен статический: при динамическом адрес сменится после
перезапуска ВМ, и вместе с ним отвалятся DNS-запись и сертификат.

## 2. Первичная настройка

Репозиторий приватный, поэтому для клонирования нужен токен или deploy key:

```bash
# вариант 1: токен GitHub (fine-grained, доступ только к этому репо)
ssh ubuntu@<публичный-IP>
curl -fsSL https://raw.githubusercontent.com/Pavel1778/rtk-crm/dev/infra/yandex-cloud/setup-vm.sh -o setup-vm.sh
GITHUB_TOKEN=ghp_... sudo -E bash setup-vm.sh

# вариант 2: deploy key
DEPLOY_KEY=/home/ubuntu/.ssh/rtk_deploy sudo -E bash setup-vm.sh
```

Скрипт ставит Docker + Compose, certbot, настраивает ufw, создаёт swap
(нужен для сборки фронтенда на 4 ГБ RAM), клонирует репозиторий в
`/opt/rtk-crm` и вешает ежедневный бэкап в `/etc/cron.daily/rtk-backup`.

## 3. Настройка `.env`

```bash
cd /opt/rtk-crm
cp infra/yandex-cloud/.env.prod.example .env
nano .env   # SECRET_KEY, POSTGRES_PASSWORD, DOMAIN, TLS_ENABLED, CORS_ORIGINS
```

Ключевые переменные:

| Переменная | Значение |
|---|---|
| `DOMAIN` | домен, на который отвечает nginx |
| `TLS_ENABLED` | `false` — только HTTP (отладка по IP); `true` — HTTPS с сертификатом |
| `SECRET_KEY` | минимум 32 символа (`openssl rand -hex 32`) |
| `SEED_DEMO_DATA` | `true`, иначе база пустая и войти некуда |

`.env` в `.gitignore` — в репозиторий он не попадает.

## 4. Запуск стека

Режим HTTP (по IP, без домена и сертификата):

```bash
cd /opt/rtk-crm
docker compose -f infra/yandex-cloud/docker-compose.prod.yml --env-file .env up -d --build
docker compose -f infra/yandex-cloud/docker-compose.prod.yml ps
curl -fsS http://localhost/api/health
```

Режим TLS (домен + Let's Encrypt) — сертификат выпускается **до** старта
nginx, потому что `certbot --standalone` занимает порт 80:

1. В реестре домена создайте A-записи `DOMAIN` и `www.DOMAIN` на IP ВМ.
2. Дождитесь распространения DNS (`dig +short <DOMAIN>`).
3. Выпустите сертификат:
   ```bash
   sudo certbot certonly --standalone -d <DOMAIN> -d www.<DOMAIN>
   ```
4. Поставьте `TLS_ENABLED=true` в `.env` и поднимите стек (команда выше).
5. Проверьте: `curl -fsS https://<DOMAIN>/api/health`.

Обновление сертификата — системным таймером certbot; nginx монтирует
`/etc/letsencrypt` только на чтение.

## 5. Перенос данных из Supabase

```bash
# на локальной машине (или на ВМ)
pg_dump "postgresql://<supabase-user>:<pass>@<host>:5432/postgres" \
  --no-owner --no-privileges -Fc -f rtk-crm.dump

scp rtk-crm.dump ubuntu@<IP>:/tmp/
ssh ubuntu@<IP>
docker cp /tmp/rtk-crm.dump rtk_postgres:/tmp/
docker exec -i rtk_postgres pg_restore -U rtk_user -d rtk_crm --no-owner /tmp/rtk-crm.dump
```

Схема создаётся приложением при старте, поэтому при конфликте таблиц
используйте `--clean --if-exists`.

## 6. Бэкапы

`infra/yandex-cloud/backup.sh` делает `pg_dump` в `/backups/rtk-crm-YYYYMMDD.sql.gz`
и удаляет копии старше 7 дней. Проверка вручную:

```bash
sudo BACKUP_DIR=/backups bash /opt/rtk-crm/infra/yandex-cloud/backup.sh
ls -lh /backups
```

## 7. Бюджет

| Ресурс | Цена в месяц |
|---|---|
| Вычислительные ресурсы (Intel Ice Lake, 20 % vCPU, 2 vCPU) | 748,80 ₽ |
| RAM 4 ГБ | 950,40 ₽ |
| Стандартный диск 30 ГБ | 103,68 ₽ |
| Публичный динамический IP | 189,73 ₽ |
| **Итого** | **1 992,61 ₽** |

Грант 5 000 ₽ покрывает около 2,5 месяцев непрерывной работы, 5 месяцев при
выключении на ночь (~8 часов работы в день) и 7–8 месяцев при выключении по
выходным. В разделе Billing → «Бюджеты» создайте уведомление на 50 % и 80 %
гранта.

Замечания по конфигурации:

- **IP нужен статический.** Динамический дешевле, но адрес сменится после
  перезапуска ВМ, и вместе с ним отвалятся DNS-запись и сертификат.
- **Стандартный диск (HDD) медленный.** Сборка фронтенда на нём занимает
  10–20 минут; если это критично, собирайте образы в CI и на ВМ делайте
  только `docker compose pull`.
- **Swap обязателен.** На 4 ГБ RAM сборка `vite build` может упереться в
  память; `setup-vm.sh` создаёт 2 ГБ swap автоматически.

## 8. Откат

Текущий прод не выключается до переключения DNS. Если что-то пошло не так —
верните A-запись на Vercel/Render, контейнеры на ВМ остановите:

```bash
docker compose -f infra/yandex-cloud/docker-compose.prod.yml down
```
