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

1. Проект создан, регион **eu-west-1 (Ирландия)**.
2. Connection string берётся в **Connect → Session pooler** (порт `5432`, НЕ `6543`).
3. Формат для backend (asyncpg):

```
DATABASE_URL=postgresql+asyncpg://<user>:<password>@aws-1-eu-west-1.pooler.supabase.com:5432/postgres
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
| `DATABASE_URL` | строка из раздела 1 (без пробелов) |
| `SECRET_KEY` | случайная строка 32+ символов |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` |
| `CORS_ORIGINS` | `https://rtk-crm-nx4r.vercel.app,http://localhost:5173` (без пробелов) |
| `SEED_DEMO_DATA` | `true` (демо-карточки) или `false` (только справочники) |

### Как это работает при старте

1. `Dockerfile` ставит зависимости из `backend/requirements.txt`.
2. `start.sh` (CMD в образе):
   - создаёт схему БД (`create_tables()`);
   - загружает справочники (`seed_reference()`: 13 этапов, пользователи,
     направления, продукты) — идемпотентно;
   - запускает `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
3. Если `SEED_DEMO_DATA=true`, приложение при старте дополнительно
   заполняет демо-вузы/взаимодействия (только для пустой базы).

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
# в backend/.env: DATABASE_URL=sqlite+aiosqlite:///./dev.db
uvicorn backend.main:app --reload

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
