# C4 Components

```mermaid
flowchart TB
    browser[Browser]
    app[React + Ant Design]
    client[Axios API client]
    api[FastAPI routers]
    auth[JWT auth + RBAC]
    ratelimit[Rate limit middleware]
    audit[Audit middleware]
    domain[Domain services]
    workflow[Workflow B2B / B2C]
    imports[Import: XLS / XLSX / JSON]
    exports[Export: XLSX / XLS / PDF / JSON]
    scheduler[APScheduler: зависшие заявки]
    orm[SQLAlchemy async]
    cache[Report cache Redis/KeyDB]
    postgres[(PostgreSQL)]
    storage[File storage S3/MinIO]

    browser --> app --> client --> api
    api --> ratelimit --> auth
    api --> domain
    api --> audit --> orm
    domain --> workflow --> orm
    api --> imports --> orm
    api --> exports --> orm
    api --> cache --> orm
    domain --> storage
    scheduler --> orm
    orm --> postgres
```

Frontend отвечает за представление и интеракции, backend — за авторизацию,
валидацию, бизнес-правила, аудит и доступ к данным. Кэш агрегатов отчётов
и планировщик уведомлений вынесены в отдельные сервисы, чтобы не блокировать
обработку запросов.
