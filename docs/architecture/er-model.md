# Модель данных (ER)

ER-диаграмма по фактическим моделям SQLAlchemy
(`backend/models/entities.py`). Диаграмма экспортируется в PNG/PDF средствами
GitHub или Mermaid CLI; исходник версионируется вместе с кодом.

Готовые артефакты рядом: [`er.mmd`](er.mmd) — извлечённый Mermaid-исходник,
[`er-model.pdf`](er-model.pdf) — отрендеренная диаграмма,
[`er.archimate`](er.archimate) — та же схема в ArchiMate 3 для Archi.
Пересборка: `python scripts/extract_er_diagram.py`, затем
`mmdc -i er.mmd -o er-model.pdf`.

```mermaid
erDiagram
    USERS ||--o{ INTERACTIONS : "assigned_kam"
    USERS ||--o{ ACTIONS : "author"
    USERS ||--o{ COMMENTS : "author"
    USERS ||--o{ ATTACHED_FILES : "uploaded_by"
    USERS ||--o{ ACTION_LOGS : "user"

    UNIVERSITIES ||--o{ INTERACTIONS : "university"
    IT_DIRECTIONS ||--o{ IT_PRODUCTS : "direction"
    IT_PRODUCTS ||--o{ INTERACTIONS : "product"
    WORKFLOW_STAGES ||--o{ INTERACTIONS : "stage"

    INTERACTIONS ||--o{ ACTIONS : "tasks"
    INTERACTIONS ||--o{ COMMENTS : "comments"
    INTERACTIONS ||--o{ ATTACHED_FILES : "files"

    USERS {
        int id PK
        string email UK
        string full_name
        string hashed_password
        enum role "user|manager|admin"
        bool is_admin
        bool is_active
    }

    UNIVERSITIES {
        int id PK
        string name
        string city
        string contact_person
        string contact_email
        string contact_phone
    }

    IT_DIRECTIONS {
        int id PK
        string name UK
    }

    IT_PRODUCTS {
        int id PK
        string name UK
        int direction_id FK
    }

    WORKFLOW_STAGES {
        int id PK
        string code
        enum scope "b2b|b2c"
        string name
        int order
        string color
        bool is_active
    }

    INTERACTIONS {
        int id PK
        int university_id FK
        int product_id FK
        int stage_id FK
        enum scope "b2b|b2c"
        string contract_number
        string contract_date
        int assigned_kam_id FK
        string university_specialist
        text notes
        bool is_active
    }

    ACTIONS {
        int id PK
        int interaction_id FK
        string title
        text description
        string due_date
        bool is_completed
        int author_id FK
    }

    COMMENTS {
        int id PK
        int interaction_id FK
        text text
        int author_id FK
    }

    ATTACHED_FILES {
        int id PK
        int interaction_id FK
        string filename
        string file_path
        int size
        string mime_type
        int uploaded_by FK
    }

    ACTION_LOGS {
        int id PK
        int user_id FK
        string action "CREATE|UPDATE|DELETE"
        string entity_type
        int entity_id
        text old_value
        text new_value
        string ip_address
    }
```

## Правила целостности

| Связь | On delete | Смысл |
|---|---|---|
| `interactions.university_id → universities.id` | `CASCADE` | Вуз с историей взаимодействий не удаляется в отрыве — история уходит вместе с ним |
| `interactions.product_id → it_products.id` | `SET NULL` | Удаление продукта не рушит карточку |
| `interactions.stage_id → workflow_stages.id` | `RESTRICT` | Активный этап нельзя удалить, пока на нём есть карточки — сначала перенос задач |
| `interactions.assigned_kam_id → users.id` | `SET NULL` | Увольнение сотрудника не удаляет заявки |
| `actions/ comments / attached_files .interaction_id` | `CASCADE` | Дочерние записи живут только внутри карточки |
| `*_logs.user_id → users.id` | `SET NULL` | Записи аудита сохраняются после удаления пользователя |

## Индексирование

Индексы заведены на внешние ключи и поля фильтрации (`interactions.university_id`,
`interactions.stage_id`, `action_logs.user_id`) и на часто фильтруемые
строки (`universities.name`). Это обеспечивает приемлемую скорость при
фильтрации доски и построении отчётов на целевой нагрузке 300+.

## Workflow B2B и B2C

Два набора этапов различаются значением `workflow_stages.scope`:
`WORKFLOW_STAGES` (14 этапов ИТ-Школы) для B2B и `B2C_STAGES` (упрощённая
воронка «заявка → оплата → обучение → завершено») для B2C. Версионирование
не применяется: изменение этапа действует на все активные заявки сразу.
