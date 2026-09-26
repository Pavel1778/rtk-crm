# Функциональная архитектура

Схема отражает пользовательский путь из раздела 2 ТЗ (5 шагов) и сервисы
бэкенда, которые его обслуживают. Диаграмма в формате Mermaid отображается
в GitHub/GitLab; при необходимости экспортируется в PNG/PDF для презентации.

## Пользовательский путь

```mermaid
flowchart LR
    start([КАМ входит в систему]) --> s1[Шаг 1.<br/>Импорт данных<br/>XLS / XLSX / JSON]
    s1 --> s2[Шаг 2.<br/>Работа с доской<br/>Kanban по этапам]
    s2 --> s3[Шаг 3.<br/>Карточка взаимодействия<br/>договор, задачи, файлы]
    s3 --> s4[Шаг 4.<br/>Перемещение по этапам<br/>фиксация результата]
    s4 --> s5[Шаг 5.<br/>Отчёт и экспорт<br/>XLSX / XLS / PDF / JSON / PNG]

    s2 -.->|фильтры| f1[По вузу, продукту, scope B2B/B2C]
    s3 -.->|уведомления| f2[Зависшие заявки → руководителю]
    s5 -.->|аудит| f3[Журнал действий + CSV]
```

## Шаги и обслуживающие сервисы

| Шаг ТЗ | Экран | Backend-сервис | Ключевые сущности |
|---|---|---|---|
| 1. Импорт данных | `DirectoryPage` | `services/excel_import.py`, `services/import_report.py` | `University`, `ITProduct`, `Interaction` |
| 2. Доска | `BoardPage` | `api/interactions.py` (list, board) | `Interaction`, `WorkflowStageRef` |
| 3. Карточка | `InteractionDrawer` | `api/interactions.py`, `api/files.py` | `Action`, `Comment`, `FileObject` |
| 4. Смена этапа | доска / карточка | `api/interactions.py` (stage update) | `Interaction.stage_id` |
| 5. Отчёты и экспорт | `ReportPage`, `AuditLogPage` | `api/reports.py`, `api/audit.py`, `services/excel_export.py` | `ActionLog`, агрегаты |

## Функциональные блоки

```mermaid
flowchart TB
    subgraph Presentation["Presentation (React SPA)"]
        board[Kanban-доска]
        card[Карточка взаимодействия]
        report[Отчёты и диаграммы]
        dirs[Справочники и Wiki]
        audit_ui[Журнал аудита]
    end

    subgraph Application["Application (FastAPI)"]
        interactions[Interactions API]
        catalogs[Catalogs / Import API]
        reports_api[Reports / Export API]
        audit_api[Audit API]
        authz[Auth + RBAC]
    end

    subgraph Domain["Domain / Infrastructure"]
        workflow[Workflow: этапы B2B/B2C]
        cache[Report cache Redis/KeyDB]
        scheduler[Планировщик уведомлений]
        storage[File storage S3/MinIO]
        gigachat[GigaChat: сводка карточки]
        db[(PostgreSQL)]
    end

    board --> interactions
    card --> interactions
    dirs --> catalogs
    report --> reports_api
    audit_ui --> audit_api
    interactions --> authz
    catalogs --> authz
    reports_api --> authz
    audit_api --> authz
    interactions --> workflow --> db
    reports_api --> cache --> db
    catalogs --> storage
    scheduler --> db
    card -.->|сводка, ФТ-6| gigachat
```

Ключевая бизнес-логика — единый workflow без версий: изменение этапа
применяется мгновенно ко всем активным заявкам, а удаление этапа переносит
задачи на соседний, чтобы работа не останавливалась.

GigaChat вызывается только по запросу пользователя из карточки и не
участвует в основном сценарии: без ключа вкладка «Сводка» сообщает, что
сервис не настроен. Подробности — `docs/AI.md`.
