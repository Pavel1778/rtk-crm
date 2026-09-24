# Деплой RTK CRM: Render + Supabase + Vercel

## Архитектура

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

## 1. Supabase (база данных)

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

## 2. Render (backend)

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
| `CORS_ORIGINS` | `https://rtk-crm-nx4r.vercel.app,http://localhost:5173` |
| `CORS_ORIGIN_REGEX` | регулярное выражение для хостов предпросмотра (необязательно), напр. `https://[a-z0-9-]+\.preview\.example\.com`; пусто = выключено |
| `SEED_DEMO_DATA` | `true` |
| `MOCK_MODE` | `true` |

### Как это работает при старте

1. `Dockerfile` ставит зависимости из `backend/requirements.txt` и запускает
   `uvicorn app.main:app --host 0.0.0.0 --port 8000` (код лежит в `/app`,
   `PYTHONPATH=/`).
2. При старте приложение (`app.main:lifespan`) создаёт схему БД
   (`create_tables()`) и загружает справочники (`seed_reference()`: 14 этапов,
   пользователи, направления, продукты) — идемпотентно.
3. Если `SEED_DEMO_DATA=true`, приложение при старте дополнительно
   заполняет демо-вузы/взаимодействия (только для пустой базы).

`backend/start.sh` — вспомогательный скрипт для Render-деплоя без Docker
(задаётся вручную как Start Command); в образ он не встроен.

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
GET https://rtk-crm-backend.onrender.com/health      -> {"status":"ok"}
GET https://rtk-crm-backend.onrender.com/api/health  -> {"status":"ok","app":"RTK CRM","database":"ok"}
GET https://rtk-crm-backend.onrender.com/docs        -> Swagger UI
```

### Демо-доступ

| Роль | Email | Пароль |
|---|---|---|
| Администратор | `admin@rtk.ru` | `admin123` |
| Менеджер | `manager@rtk.ru` | `manager123` |
| КАМ | `user@rtk.ru` | `user123` |

---

## 3. Vercel (frontend)

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

## 3.1. Локальный запуск

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

## 4. Типичные ошибки

| Симптом | Причина | Решение |
|---|---|---|
| Build: `backend/ $` / ошибка pre-deploy | В Render заполнено `Pre-Deploy Command` мусором | Очистить поле полностью |
| `relation "users" does not exist` | Схема не создана | Проверить, что старт шёл через `start.sh`/CMD |
| `connection timeout` к Supabase | Порт `6543` (transaction pooler) с asyncpg | Использовать `5432` (session pooler) |
| CORS error в браузере | `CORS_ORIGINS` со пробелами/без домена Vercel | Строка через запятую без пробелов |
| `Invalid (interleaved) UTF-8` в логах Render | Нет `PYTHONIOENCODING` | Уже задано в Dockerfile |
| Медленные ответы | Render в US, Supabase в EU | Region Render: Frankfurt |

---

## 5. Безопасность

- Пароли БД и `SECRET_KEY` — только в переменных окружения.
- `backend/.env` в `.gitignore`, в репозитории лишь `.env.example`.
- JWT-доступ ко всем эндпоинтам, кроме `/health` и логина.
- После публичного показа: сменить пароль Supabase
  (Settings → Database → Reset password) и отозвать использованные токены GitHub.
