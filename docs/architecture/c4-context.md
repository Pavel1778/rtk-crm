# C4 Context

```mermaid
flowchart LR
    kam([КАМ / руководитель])
    admin([Администратор])
    b2c([Клиент B2C])
    crm[RTK CRM]
    db[(PostgreSQL)]
    cache[(Redis / KeyDB)]
    files[(S3 / MinIO)]
    lms[LMS / CMS вуза]
    export[Отчёты XLSX / XLS / PDF / JSON]

    kam -->|HTTPS, JWT| crm
    admin -->|HTTPS, JWT, RBAC| crm
    b2c -->|HTTPS, JWT, воронка B2C| crm
    crm -->|SQL через asyncpg| db
    crm -->|кэш отчётов, TTL 30 с| cache
    crm -->|файлы| files
    crm -.->|задел интеграции| lms
    crm --> export
```

Система принимает действия пользователей, ведёт два независимых workflow
(B2B — 14 этапов ИТ-Школы, B2C — упрощённая воронка), хранит рабочие данные
в PostgreSQL, кэширует агрегаты отчётов и формирует выгрузки в четырёх
форматах.
