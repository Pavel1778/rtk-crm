# Система контроля взаимодействия ИТ Школы Ростелекома с вузами

CRM для кейса «ИТ Школа» хакатона «Лидеры цифровой трансформации 2026».
Визуализирует многоэтапный процесс взаимодействия с вузами-партнёрами,
ведёт учёт договоров, задач и комментариев по каждому взаимодействию.

## Что реализовано

- **Kanban-доска** взаимодействий с перемещением карточек между этапами
  (`@dnd-kit`), поиском по вузу и фильтром по продукту.
- **Карточка взаимодействия**: сведения, договор, задачи со сроками,
  комментарии, смена этапа.
- **Справочники**: вузы, ИТ-продукты, ИТ-направления.
- **Настройка воркфлоу**: добавление этапов, переименование, цвет колонки,
  порядок, включение/выключение.
- **Отчёт**: ключевые показатели и распределение взаимодействий по этапам.
- **Роли**: менеджер и администратор (доступ к справочникам и настройкам —
  только у администратора).
- **Адаптив**: на мобильной доска показывается одна колонка с выбором этапа.

## Ограничение бизнес-модели

У одного вуза может быть **не более 2 активных** взаимодействий —
проверяется на backend при создании.

## Стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2 (async), JWT + bcrypt |
| Frontend | React 18, TypeScript, Vite, Ant Design 5, Zustand, @dnd-kit |
| БД | PostgreSQL (Supabase) или SQLite для локальной разработки |
| Деплой | Render (backend), Vercel (frontend), Supabase (БД) |

## Бизнес-модель

```text
University  ──┐
              ├──► Interaction ──► WorkflowStage
ITProduct  ───┘         │
ITDirection ── ITProduct       ├── Action (задача со сроком)
                               └── Comment
```

`University`, `ITProduct`, `ITDirection` — справочники.
`Interaction` — главная сущность, связка «вуз + продукт», перемещается по этапам.

## Структура репозитория

```text
backend/          FastAPI-приложение (пакет backend)
  core/config.py    настройки из окружения
  db/               база и сессия
  models/           модели и перечисления
  schemas/          Pydantic-схемы
  api/              роутеры: auth, universities, directories,
                    stages, interactions, reports
  seed.py           справочники + демо-данные
  start.sh          старт на Render
frontend/         React-приложение (Vite)
  src/api/          axios-клиент и описание эндпоинтов
  src/pages/        BoardPage, ReportPage, DirectoryPage,
                    SettingsPage, LoginPage
  src/components/   MainLayout, kanban, interaction
docs/             DEPLOYMENT.md, ARCHITECTURE.md, USER_GUIDE.md
```

## Локальный запуск

### Backend

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
# в backend\.env: DATABASE_URL=sqlite+aiosqlite:///./dev.db
uvicorn backend.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

http://127.0.0.1:5173 — dev-сервер проксирует `/api` на `localhost:8000`,
поэтому `VITE_API_URL` в разработке не нужен.

### Демо-доступ

| Роль | Email | Пароль |
|---|---|---|
| Администратор | `admin@rtk.ru` | `admin123` |
| Менеджер | `manager@rtk.ru` | `manager123` |

## Деплой

Пошаговая инструкция для Render + Supabase + Vercel:
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Документация

- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — развёртывание
- [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) — архитектура
- [USER_GUIDE.md](docs/USER_GUIDE.md) — руководство пользователя
