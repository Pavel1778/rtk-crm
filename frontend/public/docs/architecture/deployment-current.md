# Внешний контур (Render + Vercel + Supabase)

```mermaid
flowchart LR
    user([Пользователь]) -->|HTTPS| vercel[Vercel\nReact/Vite]
    vercel -->|HTTPS API| render[Render\nFastAPI]
    render -->|TLS PostgreSQL| supabase[(Supabase\nPostgreSQL)]
```

Vercel публикует статический frontend. Render обслуживает API. Supabase
предоставляет PostgreSQL. CORS backend ограничивает разрешённые origins.

Этот контур не требует своей инфраструктуры и используется как публичный
демонстрационный стенд. Основной контур — Yandex Cloud
(см. [deployment-yandex-cloud.md](/docs/architecture/deployment-yandex-cloud.md)).
