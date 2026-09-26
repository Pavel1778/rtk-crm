# Технологический стек

Документ фиксирует версии и назначение компонентов RTK CRM (кейс №6, ЛЦТ 2026).

## Backend

| Компонент | Версия | Назначение |
|---|---|---|
| Python | 3.11 | Язык и рантайм (образ `python:3.11-slim`) |
| FastAPI | 0.141.1 | HTTP API, валидация, OpenAPI |
| Uvicorn | 0.34.0 | ASGI-сервер |
| Pydantic / pydantic-settings | 2.10.4 / 2.7.1 | Схемы и конфигурация из окружения |
| SQLAlchemy (async) | 2.0.36 | ORM, async-движок |
| asyncpg | 0.30.0 | Драйвер PostgreSQL |
| aiosqlite | 0.20.0 | Драйвер SQLite для dev и тестов |
| Alembic | 1.14.0 | Миграции схемы |
| python-jose, passlib[bcrypt] | 3.5.0 / 1.7.4 | JWT и хеширование паролей |
| Redis client | 5.2.1 | Кэш отчётов, потенциально — счётчики лимитов |
| minio | 7.2.10 | S3-совместимое хранилище файлов |
| APScheduler | 3.11.0 | Фоновые проверки «зависших» заявок |
| prometheus-fastapi-instrumentator | 8.1.0 | Метрики на `/metrics` |
| openpyxl, xlwt, xlrd, reportlab | — | Экспорт отчётов XLSX/XLS/PDF |
| loguru | 0.7.3 | Логирование |
| pytest, pytest-asyncio | 9.1.1 / 1.4.0 | Тесты |

## Frontend

| Компонент | Версия | Назначение |
|---|---|---|
| React | 18.2 | UI |
| TypeScript | 5.2 | Типизация |
| Vite | 5.0 | Сборка и dev-сервер |
| Ant Design | 5.12 | Компонентная библиотека |
| React Router | 6.20 | Маршрутизация |
| TanStack Query | 5.x | Серверное состояние и кэш |
| Zustand | 4.4 | Клиентское состояние |
| Axios | 1.6 | HTTP-клиент |
| Recharts | 3.x | Графики отчётов |
| dnd-kit | 6.x / 8.x | Drag-and-drop этапов воронки |

## Инфраструктура

| Компонент | Назначение |
|---|---|
| PostgreSQL | Основная БД (Yandex Managed PostgreSQL, контейнер на ВМ или Supabase) |
| Redis / KeyDB | Кэш агрегатов отчётов; KeyDB рекомендован заказчиком как более лёгкий |
| S3-хранилище | Файлы заявок: Yandex Object Storage или MinIO (S3-совместимое API) |
| Keycloak | Задел под корпоративную аутентификацию (закрытый контур) |
| Nginx | Reverse proxy, TLS, отдача статики |
| Docker Compose | Запуск всего контура одной командой |

## Внешние сервисы и интеграции

- **Yandex Cloud** — основной контур: Compute (ВМ), Managed PostgreSQL,
  Object Storage, Container Registry, Cloud DNS.
- **Render + Vercel + Supabase** — альтернативный контур без своей
  инфраструктуры (хостинг API, статика фронтенда, PostgreSQL).
- **GigaChat** — сводка по карточке взаимодействия (ФТ-6). Подключается по
  ключу авторизации; без него функция выключена и приложение работает как
  обычно.
- **LMS/Laravel** — задел под интеграцию (httpx), не в MVP.

## Требования к окружению

- Python 3.11+, Node.js 20+.
- Для полного контура: Docker и Docker Compose.
- Минимум для запуска API без инфраструктуры: SQLite + локальный `uploads/`.
