# Разработка RTK CRM

Заметки для разработчиков по репозиторию RTK CRM.

## Команды

| Задача | Команда |
| --- | --- |
| Backend-тесты | `python -m pytest -q` |
| Frontend typecheck + сборка | `cd frontend && npm run build` |
| Локальный backend | `uvicorn backend.main:app --reload` |
| Локальный frontend | `cd frontend && npm run dev` |
| Пересборка презентации | `python3 scripts/check_presentation_layout.py` — проверка вёрстки готового PPTX/PDF |
| Рендер презентации в PDF | `soffice --headless --convert-to pdf --outdir /tmp/render docs/presentation/RTK-CRM-LCT2026.pptx` |

Линтера во frontend нет: `npm run build` запускает `tsc` и падает на ошибках типов.

## Устройство

- `backend/` — FastAPI + SQLAlchemy 2 async. Схему БД синхронизирует
  `backend/db/schema_sync.py`; при изменении моделей правьте и его.
- `frontend/src/` — React 18 + TypeScript + Ant Design 5.
- `docs/` — руководства, архитектура, презентация и питч.
- Воронки B2B и B2C различаются через `WorkflowScope`; scope передаётся в
  фильтры доски, создание заявок и отчёты, чтобы воронки не смешивались.

## Цвета и тема

Все цвета интерфейса задаются токенами: CSS-переменные `--atmr-*` в
`frontend/src/index.css` и палитры в `frontend/src/theme/theme.ts`. Новый цвет
добавляйте в оба тёмных блока CSS (`prefers-color-scheme` и `data-theme='dark'`)
и в светлый `:root`. HEX в компонентах допустим только как значение данных
(например, цвет этапа workflow, сохраняемый в БД) — для него есть
`DEFAULT_STAGE_COLOR`.

Тёмная тема переключается через `themeStore` (светлая → тёмная → системная),
anti-flicker скрипт живёт в `frontend/index.html`.

## Тесты

Тесты лежат в `tests/`. Написаны на реальном коде без моков: поднимают
приложение через TestClient и работают с временной БД SQLite.

## Ветки и публикация

Работа идёт в `dev`, `main` — стабильная ветка. После завершения изменений
`dev` вливается в `main` сразу, без отдельного согласования.

```bash
git push origin dev
git push origin dev:main
```

Пуш в `main` должен проходить fast-forward: если `main` разошёлся с `dev`,
сначала приведите `dev` к `main`, а не создавайте merge-коммит.

Коммиты подписываются владельцем репозитория — `Pavel1778
<sabadaspaha@gmail.com>` и для автора, и для коммиттера. Следы инструментов
разработки в сообщениях коммитов, трейлерах и описаниях PR не оставляем:
история должна читаться как работа владельца.
