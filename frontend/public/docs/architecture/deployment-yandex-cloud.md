# Целевое развёртывание в Yandex Cloud

```mermaid
flowchart LR
    user([Пользователь]) -->|HTTPS 443| nginx[Nginx + TLS\nYandex Cloud VM]
    nginx --> frontend[Frontend container]
    nginx --> backend[FastAPI container]
    backend --> postgres[(PostgreSQL volume)]
    postgres --> backup[/pg_dump backup\n7 days/]
```

Целевой вариант описан в `infra/yandex-cloud/`. Перенос требует отдельного
решения владельца системы, миграции данных, выпуска сертификата и проверки
152-ФЗ в выбранном контуре.
