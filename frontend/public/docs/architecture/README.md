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

- [Текущее развёртывание](/docs/architecture/deployment-current.md) — Vercel → Render → Supabase.
- [Целевое развёртывание в Yandex Cloud](/docs/architecture/deployment-yandex-cloud.md) —
  подготовленный вариант в российском контуре.

Текущий production-контур: Vercel → Render → Supabase. Миграция в Yandex Cloud
является подготовленным целевым вариантом и не выполняется автоматически.

Полное описание архитектуры, стека и стратегии масштабирования —
в [`ARCHITECTURE.md`](/docs/architecture/ARCHITECTURE.md).
