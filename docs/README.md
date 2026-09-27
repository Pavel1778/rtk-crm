# RTK CRM — Документация

## 📚 Содержание

1. [Архитектура системы](architecture/ARCHITECTURE.md)
2. [Руководство пользователя](USER_GUIDE.md)
3. [Руководство администратора](ADMIN_GUIDE.md)
4. [Диаграммы архитектуры](architecture/README.md)
5. [API документация](http://localhost:8000/api/docs)

## 🏗 Архитектура

Текущий контур — SPA и один FastAPI-сервис с PostgreSQL:

- **Frontend**: React 18 + TypeScript + Vite + Ant Design
- **Backend**: FastAPI (Python 3.11) + SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL (Yandex Managed PostgreSQL, контейнер или Supabase)
- **Storage**: S3-совместимое (Yandex Object Storage или MinIO)
- **Auth**: JWT + bcrypt с RBAC
- **Deploy**: Yandex Cloud (ВМ + nginx) или Render + Vercel

Keycloak, Redis и Nginx описаны только как варианты будущего целевого
контура Yandex Cloud, а не как обязательные зависимости текущей сборки.

## 🚀 Быстрый старт

```bash
# Клонировать репозиторий
git clone https://github.com/Pavel1778/rtk-crm.git
cd rtk-crm

# Backend запускается по инструкции в корневом README
pip install -r backend/requirements.txt

# Инициализировать БД справочниками и демо-данными
python scripts/seed.py

# В контейнере код лежит в /app, поэтому путь другой:
docker exec rtk_backend python /app/seed.py

# Проверить статус
docker-compose ps
```

## 📁 Структура проекта

```
rtk-crm/
├── backend/           # FastAPI приложение (пакет app в контейнере)
│   ├── core/         #   настройки из окружения
│   ├── db/           #   база и сессии
│   ├── models/       #   SQLAlchemy модели и перечисления
│   ├── schemas/      #   Pydantic схемы
│   ├── api/          #   API-роутеры
│   ├── auth/         #   JWT, пароли, RBAC
│   ├── middleware/   #   аудит и ограничение попыток входа
│   ├── services/     #   бизнес-логика и экспорты
│   ├── config/       #   копия конфига колонок (попадает в образ)
│   ├── alembic/      #   миграции
│   ├── seed.py       #   справочники и демо-данные
│   └── start.sh      #   старт на Render без Docker
├── frontend/          # React приложение (Vite)
│   └── src/
│       ├── components/
│       ├── pages/
│       └── api/
├── config/           # канонический конфиг колонок отчёта
├── scripts/          # утилиты (seed, sync, smoke, dev-сервер)
├── nginx/            # Конфигурация Nginx
├── infra/            # Контур Yandex Cloud
├── docs/             # Документация
└── docker-compose.yml
```

Канонический `config/report_columns.json` дублируется в
`backend/config/report_columns.json` скриптом `scripts/sync_report_columns.py`:
backend собирается с build context `backend/`, поэтому корневой `config/` в
образ не попадает и без копии приложение падает на старте.

## 🔐 Безопасность

- JWT Bearer-аутентификация (HS256), пароли — bcrypt.
- RBAC (`user`, `manager`, `admin`).
- Логирование действий (152-ФЗ, приказ ФСТЭК № 117).
- HTTPS на целевом контуре (Nginx в Yandex Cloud).

Keycloak в текущей сборке не используется: интеграция описана как
альтернатива для целевого контура, активный режим — JWT.

## 📊 Воркфлоу (14 этапов)

1. Поиск контактов ответственного в вузе
2. Коммуникация и уточнение актуальности программ
3. Организация встречи с представителями вуза
4. Обмен необходимым пакетом документов для подписания
5. Корректировка документов перед подписанием
6. Подписание документов
7. Передача обучающих материалов, лицензии и документации
8. Сопровождение внедрения ИТ-продуктов в вузе
9. Обучение преподавателей
10. Актуализация учебной программы
11. Ведение занятий
12. Актуализация документации по продукту и материалам
13. Повышение квалификации преподавателей
14. Контроль за исполнением каждого этапа

## 🛠 Технологии

| Компонент | Технология | Версия |
|-----------|------------|--------|
| Backend | Python + FastAPI | 3.11 / 0.141 |
| Frontend | React + TypeScript | 18 / 5.x |
| Database | PostgreSQL (Yandex Managed / контейнер / Supabase) | 16 |
| Cache | Redis / KeyDB (отчёты, TTL 30 с) | 5.2 |
| Auth | JWT (HS256) + bcrypt | — |
| Web Server | Nginx (целевой контур Yandex Cloud) | Alpine |

## 📞 Контакты

Команда разработки: RTK CRM, Ростов-на-Дону (познакомились в РКСИ)
Почта: team@rtk-crm.ru
Хакатон: "Лидеры цифровой трансформации 2026"
Кейс №6: ИТ Школа Ростелекома
