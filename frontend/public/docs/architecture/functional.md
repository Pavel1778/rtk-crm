# Функциональная архитектура

Схема отражает пользовательский путь КАМ (5 шагов: авторизация, просмотр,
фильтрация, актуализация статуса, отчёт) и сервисы бэкенда, которые его
обслуживают. Диаграмма в формате Mermaid отображается в GitHub/GitLab;
при необходимости экспортируется в PNG/PDF для презентации.

Та же модель в ArchiMate 3 — [`functional.archimate`](/docs/architecture/functional.archimate)
(открывается в [Archi](https://www.archimatetool.com/)), готовая
[PDF-версия](/docs/architecture/functional.pdf). Mermaid-исходник для рендера —
[`functional.mmd`](/docs/architecture/functional.mmd).

## Пользовательский путь и сервисы в Archi

```mermaid
flowchart TD
    subgraph BIZ["Бизнес-слой: пользовательский путь (раздел 2 ТЗ)"]
        direction LR
        S1["Шаг 1. Авторизация<br/>логин/пароль или Keycloak"]
        S2["Шаг 2. Просмотр взаимодействий<br/>КАМ — свои вузы, руководитель — все"]
        S3["Шаг 3. Фильтрация<br/>вуз, продукт, направление, B2B/B2C"]
        S4["Шаг 4. Актуализация статуса<br/>комментарий + файлы + смена этапа"]
        S5["Шаг 5. Отчёт<br/>сводка и выгрузка XLSX/XLS/PDF/JSON"]
        S1 --> S2 --> S3 --> S4 --> S5
    end
    subgraph APP["Прикладной слой: сервисы"]
        AUTH["Auth Service (Keycloak)"]
        BOARD["Board Service (Kanban)"]
        CARD["Interaction Service (карточки)"]
        REPORT["Report Service (отчёты)"]
        FILES["File Service (MinIO / S3)"]
        INTEG["Integration Service (LMS / CMS)"]
        AI["AI Service (GigaChat, ФТ-6)"]
    end
    OBJ[("Взаимодействие<br/>вуз + продукт")]
    S1 --> AUTH
    S2 --> BOARD
    S2 --> CARD
    S3 --> BOARD
    S4 --> CARD
    S4 --> FILES
    S4 -.->|по запросу| AI
    S5 --> REPORT
    S5 --> INTEG
    S4 --> OBJ
    S5 --> OBJ
```

## Операционный цикл: импорт → доска → карточка → отчёт

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

## Операции и обслуживающие сервисы

| Этап цикла | Экран | Backend-сервис | Ключевые сущности |
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
