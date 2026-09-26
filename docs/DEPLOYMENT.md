# Деплой RTK CRM

Актуальный способ развёртывания — Yandex Cloud, одна ВМ со всеми
компонентами в Docker. Описание ниже (Render + Supabase + Vercel) оставлено
как предыдущий вариант: он использовался до переезда.

- [1. Yandex Cloud (актуально)](#1-yandex-cloud-актуально)
- [2. Render + Supabase + Vercel (предыдущий вариант)](#2-render--supabase--vercel-предыдущий-вариант)

---

## 1. Yandex Cloud (актуально)

Всё разворачивается на одной ВМ: PostgreSQL, backend (FastAPI), frontend
(React/Vite) и nginx. Подробная пошаговая инструкция — в
[`infra/yandex-cloud/README.md`](../infra/yandex-cloud/README.md), здесь —
схема и ключевые отличия от предыдущего варианта.

```
Пользователь
   │  https://<домен>  (или http://<IP> в режиме отладки)
   ▼
nginx  ── /            ──▶ frontend  (статика Vite)
       ── /api/        ──▶ backend   (uvicorn + FastAPI)
                              │
                              ▼
                          PostgreSQL 16 (контейнер на той же ВМ)
```

Все контейнеры в одной docker-сети, наружу смотрят только nginx (80/443).
Backend и база снаружи недоступны.

### Что изменилось относительно Render + Supabase + Vercel

| Было | Стало |
|---|---|
| Vercel (CDN) | nginx на ВМ, отдаёт статику |
| Render (US/EU) | тот же контейнер backend на ВМ |
| Supabase (внешний Postgres) | PostgreSQL 16 в контейнере |
| Два origin, CORS обязателен | Один origin, запросы same-origin |
| `VITE_API_URL` = абсолютный адрес backend | `VITE_API_URL` пустой, `/api/` проксирует nginx |

Переход на один origin убирает целый класс проблем: preflight-запросы,
расхождения в allowlist CORS, разные домены у cookie.

### Два режима nginx

Режим выбирается переменной `TLS_ENABLED` в `.env`:

| `TLS_ENABLED` | Что поднимается | Когда нужен |
|---|---|---|
| `false` | только 80, отвечает по IP | отладка, домена и сертификата ещё нет |
| `true` | 80 (редирект) + 443 с сертификатом | демонстрация жюри |

В режиме `true` сертификат нужно выпустить **до** старта nginx:
`certbot --standalone` занимает порт 80, поэтому одновременно с работающим
nginx он не отработает.

### Переменные окружения

Шаблон — `infra/yandex-cloud/.env.prod.example`. Важно: имена переменных
должны совпадать с теми, что читает `backend/core/config.py` (`SECRET_KEY`,
`SEED_DEMO_DATA`, `CORS_ORIGINS`, `S3_*`). `ENVIRONMENT=production` включает
проверку длины `SECRET_KEY` при старте — со слабым ключом приложение не
поднимется.

### Бэкапы

`infra/yandex-cloud/backup.sh` кладётся в `/etc/cron.daily/rtk-backup`
скриптом `setup-vm.sh` и делает `pg_dump` раз в сутки.

---

## 2. Render + Supabase + Vercel (предыдущий вариант)

### Архитектура

```
Vercel (frontend, статика Vite)
   │  https://rtk-crm-nx4r.vercel.app
   ▼
Render (backend, Docker: uvicorn + FastAPI)
   │  https://rtk-crm-backend.onrender.com
   ▼
Supabase PostgreSQL 15 (Session Pooler, порт 5432)
```

---

### 2.1. Supabase (база данных)

Проект: `azdovsiwdyjzoqmltvrv`
Region: **eu-west-1 (Ирландия)**

Connection string (Session Pooler, порт 5432):
```
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>.pooler.supabase.com:5432/postgres
```

Требования:
- префикс `postgresql+asyncpg://` (не `postgresql://`);
- порт `5432` (Session Pooler — держит постоянное соединение, нужно asyncpg);
- SSL включён по умолчанию, дополнительных параметров не требуется.

> Важно: пароли в репозиторий не коммитятся. Значения — только в
> Render → Environment и локальном `backend/.env`.

---

### 2.2. Render (backend)

Тип: **Web Service** (Docker).

| Параметр | Значение |
|---|---|
| Repository | `Pavel1778/rtk-crm` |
| Branch | `main` |
| Environment | **Docker** |
| Dockerfile Path | `backend/Dockerfile` |
| Docker Context Directory | `backend` |
| Region | **Frankfurt (EU Central)** — ближе к Supabase eu-west-1 |
| Instance Type | Free |

### Переменные окружения (Render → Environment)

| Ключ | Значение |
|---|---|
| `DATABASE_URL` | значение из Supabase, хранить только в Render Environment |
| `SECRET_KEY` | уникальная строка не менее 32 символов |
| `ENVIRONMENT` | `production`; включает HSTS (`Strict-Transport-Security`) и строгую проверку `SECRET_KEY` |
| `CORS_ORIGINS` | `https://rtk-crm-nx4r.vercel.app,http://localhost:5173` |
| `CORS_ORIGIN_REGEX` | регулярное выражение для хостов предпросмотра (необязательно), напр. `https://[a-z0-9-]+\.preview\.example\.com`; пусто = выключено |
| `SEED_DEMO_DATA` | `true` |
| `MOCK_MODE` | `true` |

> `ENVIRONMENT` должен быть ровно `production` (или `prod`). При другом
> значении HSTS не отдаётся, а проверка длины `SECRET_KEY` не применяется.
> Перед сменой значения убедитесь, что `SECRET_KEY` не короче 32 символов:
> иначе приложение не стартует (см. `Settings.validate_production_secret`).

### Как это работает при старте

1. `Dockerfile` ставит зависимости из `backend/requirements.txt` и запускает
   `uvicorn app.main:app --host 0.0.0.0 --port 8000` (код лежит в `/app`,
   `PYTHONPATH=/`).
2. При старте приложение (`app.main:lifespan`) создаёт схему БД
   (`create_tables()`) и **сверяет её с моделями**
   (`ensure_schema()`: добавляет недостающие колонки и индексы, заменяет
   устаревшие глобальные UNIQUE на составные по `scope`), затем загружает
   справочники (`seed_reference()`: 14 этапов B2B + 4 этапа B2C, пользователи,
   направления, продукты) — идемпотентно.
3. Если `SEED_DEMO_DATA=true`, приложение при старте дополнительно
   заполняет демо-вузы/взаимодействия (только для пустой базы).

> Сверка схемы нужна, потому что `create_all(checkfirst=True)` существующие
> таблицы не изменяет: база, созданная ранней версией приложения, молча
> оставалась без `scope`, и загрузка демо-данных падала с
> `column workflow_stages.scope does not exist`. `ensure_schema()` доводит
> такую схему до моделей, не удаляя данные, и отмечает головную ревизию
> Alembic, чтобы последующий `alembic upgrade head` не пытался создать уже
> существующие таблицы.

`backend/start.sh` — вспомогательный скрипт для Render-деплоя без Docker
(задаётся вручную как Start Command); в образ он не встроен. Он выполняет те
же шаги: `create_tables()` → `ensure_schema()` → `seed_reference()`.

### Режимы аутентификации

| Режим | `MOCK_MODE` | Что нужно | Использование |
|---|---:|---|---|
| JWT + БД | `true` | Только БД и `SECRET_KEY` | Текущий хакатонный и Render-контур |
| Keycloak | `false` | Keycloak, realm, клиент и адаптер токенов | Планируемый закрытый контур |

В текущей версии API реализует JWT-аутентификацию через
`POST /api/auth/login`. Значение `false` зарезервировано для будущей
интеграции Keycloak и не переключает backend автоматически.

### Проверка

```
GET https://rtk-crm-backend.onrender.com/           -> {"service":"RTK CRM",...}
GET https://rtk-crm-backend.onrender.com/health      -> {"status":"ok"}
GET https://rtk-crm-backend.onrender.com/api/health  -> {"status":"ok","app":"RTK CRM","database":"ok"}
GET https://rtk-crm-backend.onrender.com/healthz     -> {"status":"ok"}
GET https://rtk-crm-backend.onrender.com/readyz      -> {"status":"ok","checks":{...}}
GET https://rtk-crm-backend.onrender.com/metrics     -> метрики Prometheus
GET https://rtk-crm-backend.onrender.com/docs        -> Swagger UI
```

### Демо-доступ

| Роль | Email | Пароль |
|---|---|---|
| Администратор | `admin@rtk.ru` | `admin123` |
| Менеджер | `manager@rtk.ru` | `manager123` |
| КАМ | `kam@rtk.ru` | `kam123` |

---

### 2.3. Vercel (frontend)

| Параметр | Значение |
|---|---|
| Framework Preset | Vite |
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

Переменные окружения:

| Ключ | Значение |
|---|---|
| `VITE_API_URL` | `https://rtk-crm-backend.onrender.com` |

Frontend — SPA на React Router, поэтому нужен rewrite всех путей на
`index.html` (иначе 404 на `/reports`, `/directories`, `/settings`).
Файл `frontend/vercel.json` уже в репозитории:

```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
```

---

### 2.3.1. Локальный запуск

```bash
# Backend (без Supabase подойдёт SQLite)
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
# .env в корне репозитория: DATABASE_URL=sqlite+aiosqlite:///./dev.db
python scripts/run_dev.py

# Frontend
cd frontend
npm install
npm run dev
```

---

### 2.4. Типичные ошибки

| Симптом | Причина | Решение |
|---|---|---|
| Build: `backend/ $` / ошибка pre-deploy | В Render заполнено `Pre-Deploy Command` мусором | Очистить поле полностью |
| `relation "users" does not exist` | Схема не создана | Проверить, что старт шёл через `start.sh`/CMD |
| `connection timeout` к Supabase | Порт `6543` (transaction pooler) с asyncpg | Использовать `5432` (session pooler) |
| CORS error в браузере | `CORS_ORIGINS` со пробелами/без домена Vercel | Строка через запятую без пробелов |
| `Invalid (interleaved) UTF-8` в логах Render | Нет `PYTHONIOENCODING` | Уже задано в Dockerfile |
| Медленные ответы | Render в US, Supabase в EU | Region Render: Frankfurt |

---

### 2.5. Безопасность

- Пароли БД и `SECRET_KEY` — только в переменных окружения.
- `backend/.env` в `.gitignore`, в репозитории лишь `.env.example`.
- JWT-доступ ко всем эндпоинтам, кроме `/health` и логина.
- После публичного показа: сменить пароль Supabase
  (Settings → Database → Reset password) и отозвать использованные токены GitHub.
