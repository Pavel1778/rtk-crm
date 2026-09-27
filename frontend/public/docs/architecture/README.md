# Архитектурные диаграммы

Диаграммы описывают текущий контур и целевую миграцию. Они написаны в
Mermaid и отображаются в GitHub, GitLab и совместимых Markdown-просмотрщиках.
Исходники версионируются вместе с кодом, отдельный экспорт в PNG/PDF не
требуется для ревью.

## C4

- [C4 Level 1 — System Context](/docs/architecture/c4-context.md)
- [C4 Level 2 — Containers / Components](/docs/architecture/c4-components.md)

## Дополнительно

- [Функциональная архитектура](/docs/architecture/functional.md) — пользовательский путь из ТЗ
  и обслуживающие сервисы.
- [Модель данных (ER)](/docs/architecture/er-model.md) — сущности, связи и правила целостности.

## Модели в Archi

Требование ТЗ 6.7 — функциональная и компонентная архитектура в Archi.
Все модели в формате ArchiMate 3, открываются в
[Archi](https://www.archimatetool.com/) бесплатно, файлы лежат в репозитории
рядом с Mermaid-схемами.

- [`functional.archimate`](/docs/architecture/functional.archimate) — функциональная модель:
  пользовательский путь КАМ из 5 шагов (авторизация, просмотр, фильтрация,
  актуализация статуса, отчёт) и обслуживающие сервисы. Готовая
  [PDF-версия](/docs/architecture/functional.pdf), Mermaid-исходник — [`functional.mmd`](/docs/architecture/functional.mmd).
- [`rtk-crm.archimate`](/docs/architecture/rtk-crm.archimate) — компонентная модель: контейнеры,
  внешние системы и целевое развёртывание.
- [`er.archimate`](/docs/architecture/er.archimate) — модель данных (ER) в ArchiMate 3: 14
  сущностей предметной области и связи между ними с правилами `ON DELETE`.
  Готовая [PDF-версия диаграммы](/docs/architecture/er-model.pdf) приложена рядом.
  Mermaid-исходник — [`er.mmd`](/docs/architecture/er.mmd), пересборка:
  `python scripts/extract_er_diagram.py`.

## Развёртывание

- [Основной контур в Yandex Cloud](/docs/architecture/deployment-yandex-cloud.md) — ВМ,
  nginx, PostgreSQL, Object Storage, KeyDB.
- [Внешний контур](/docs/architecture/deployment-current.md) — Vercel → Render → Supabase.

Основной контур — Yandex Cloud: данные размещаются в РФ, что требуется
152-ФЗ. Внешний контур поддерживается как публичный демонстрационный стенд
и разворачивается из того же кода без изменений.

Полное описание архитектуры, стека и стратегии масштабирования —
в [`ARCHITECTURE.md`](/docs/architecture/ARCHITECTURE.md).
