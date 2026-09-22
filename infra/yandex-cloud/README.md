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
| Образ | Ubuntu 22.04 LTS |
| Платформа | Intel Ice Lake, прерываемая — нет |
| vCPU / доля | 2 vCPU, 20 % (для демо достаточно) или 100 % для прода |
| RAM | 4 ГБ |
| Диск | 20 ГБ SSD |
| Публичный IP | статический (нужен для A-записи) |
| Доступ | логин `ubuntu`, ваш SSH-ключ |

## 2. Первичная настройка

```bash
ssh ubuntu@<публичный-IP>
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Pavel1778/rtk-crm/dev/infra/yandex-cloud/setup-vm.sh)"
```

Скрипт ставит Docker + Compose, certbot, настраивает ufw, клонирует репозиторий
в `/opt/rtk-crm` и вешает ежедневный бэкап в `/etc/cron.daily/rtk-backup`.

Тот же скрипт можно указать при создании ВМ как `user-data` (cloud-init).

## 3. Настройка `.env`

```bash
cd /opt/rtk-crm
cp infra/yandex-cloud/.env.prod.example .env
nano .env   # SECRET_KEY, POSTGRES_PASSWORD, CORS_ORIGINS, VITE_API_URL
```

`.env` в `.gitignore` — в репозиторий он не попадает.

## 4. Домен и сертификат

1. В реестре домена создайте A-запись `rtk-crm.ru → <публичный-IP>`
   (и `www` — тоже A-запись на тот же IP).
2. Дождитесь распространения DNS (`dig +short rtk-crm.ru`).
3. Выпустите сертификат:

```bash
sudo certbot certonly --standalone -d rtk-crm.ru -d www.rtk-crm.ru
```

Обновление сертификата — системным таймером certbot; nginx монтирует
`/etc/letsencrypt` только на чтение.

## 5. Запуск стека

```bash
cd /opt/rtk-crm
docker compose -f infra/yandex-cloud/docker-compose.prod.yml --env-file .env up -d --build
docker compose -f infra/yandex-cloud/docker-compose.prod.yml ps
curl -fsS https://rtk-crm.ru/api/health
```

## 6. Перенос данных из Supabase

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

## 7. Бэкапы

`infra/yandex-cloud/backup.sh` делает `pg_dump` в `/backups/rtk-crm-YYYYMMDD.sql.gz`
и удаляет копии старше 7 дней. Проверка вручную:

```bash
sudo BACKUP_DIR=/backups bash /opt/rtk-crm/infra/yandex-cloud/backup.sh
ls -lh /backups
```

## 8. Бюджет

| Ресурс | Цена в месяц (оценка) |
|---|---|
| ВМ 2 vCPU (20 %), 4 ГБ RAM | ~800 ₽ |
| SSD 20 ГБ | ~200 ₽ |
| Статический публичный IP | ~150 ₽ |
| Исходящий трафик (демо-нагрузка) | ~50 ₽ |
| **Итого** | **~1 200 ₽** |

Стартовый грант 4 000 ₽ покрывает более трёх месяцев. В разделе
Billing → «Бюджеты» создайте уведомление на 50 % и 80 % гранта.

## 9. Откат

Текущий прод не выключается до переключения DNS. Если что-то пошло не так —
верните A-запись на Vercel/Render, контейнеры на ВМ остановите:

```bash
docker compose -f infra/yandex-cloud/docker-compose.prod.yml down
```
