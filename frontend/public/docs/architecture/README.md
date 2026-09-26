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

## Развёртывание

- [Основной контур в Yandex Cloud](/docs/architecture/deployment-yandex-cloud.md) — ВМ,
  nginx, PostgreSQL, Object Storage, KeyDB.
- [Внешний контур](/docs/architecture/deployment-current.md) — Vercel → Render → Supabase.

Основной контур — Yandex Cloud: данные размещаются в РФ, что требуется
152-ФЗ. Внешний контур поддерживается как публичный демонстрационный стенд
и разворачивается из того же кода без изменений.

Полное описание архитектуры, стека и стратегии масштабирования —
в [`ARCHITECTURE.md`](/docs/architecture/ARCHITECTURE.md).
