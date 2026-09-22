# Нагрузочный тест RTK CRM

Сценарий моделирует работу авторизованного пользователя: открытие отчётов,
канбан-доски, этапов workflow и справочников.

## Подготовка

Установите зависимости разработки:

```bash
pip install -r requirements-dev.txt
```

Для тестового пользователя можно задать переменные окружения:

```bash
export RTK_TEST_EMAIL="kam@rtk.ru"
export RTK_TEST_PASSWORD="kam123"
```

Используйте только тестовую учётную запись с минимальными правами. Секреты не
добавляйте в репозиторий.

## Запуск

Из корня проекта:

```bash
locust -f tests/load/locustfile.py \
  RTKUser \
  --headless \
  -u 50 \
  -r 5 \
  -t 60s \
  --host=http://localhost:8000 \
  --html=tests/load/report.html
```

Для запуска с интерфейсом:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

После запуска откройте `http://localhost:8089`.

## Критерии защиты

- Failure rate: 0% или близко к 0%.
- 95-й процентиль: менее 1000 мс.
- В отчёте должны быть видны итоговые Requests/s и распределение времени ответа.

`report.html` создаётся только после реального запуска против тестового
окружения и намеренно не подменяется синтетическими результатами.

## 10 параллельных отчётов

Сценарий `ReportsUser` выполняет отчёты с разными фильтрами. Запуск ровно
десяти одновременных пользователей:

```bash
locust -f tests/load/locustfile.py ReportsUser \
  --headless \
  -u 10 \
  -r 10 \
  -t 30s \
  --host=http://localhost:8000 \
  --html=tests/load/report-10-reports.html
```

`report-10-reports.html` создаётся только реальным прогоном. Результаты
записываются после проверки доступности тестового backend; синтетические
цифры в репозиторий не добавляются.

## Write-операции и тяжёлые экспорты

Профиль `RTKUser` дополнительно покрывает создание взаимодействия, переход
между этапами, комментарии, загрузку PNG-файла и XLS/XLSX/PDF. Профиль
`StageAdminUser` отдельно проверяет выключение и включение этапа через
`PATCH /api/stages/{id}`. Для создания взаимодействия ожидаемый `409` при
конфликте уникальности «вуз + продукт» помечается как успешный бизнес-ответ,
а не как инфраструктурная ошибка.

Команды:

```bash
locust -f tests/load/locustfile.py RTKUser \
  --headless -u 50 -r 5 -t 3m \
  --host=http://localhost:8000 \
  --html=tests/load/reports/full-profile-YYYYMMDD.html

locust -f tests/load/locustfile.py RTKUser --tags export \
  --headless -u 10 -r 2 -t 1m \
  --host=http://localhost:8000 \
  --html=tests/load/reports/exports-YYYYMMDD.html

locust -f tests/load/locustfile.py StageAdminUser \
  --headless -u 10 -r 2 -t 30s \
  --host=http://localhost:8000 \
  --html=tests/load/reports/stage-admin-YYYYMMDD.html
```

### Фактический write/export прогон 22.09.2026

Локальный SQLite backend, 50 пользователей, 3 минуты:

- 4673 запроса, 0 ошибок;
- `POST /api/interactions`: p95 32 мс;
- `POST /api/interactions/{id}/move`: p95 43 мс;
- `POST /api/interactions/{id}/comments`: p95 45 мс;
- `POST /api/files/interactions/{id}/upload`: p95 33 мс;
- `GET /api/reports/xlsx`: p95 48 мс;
- `GET /api/reports/xls`: p95 76 мс;
- `GET /api/reports/pdf`: p95 210 мс;
- агрегированный p95: 110 мс.

Экспорт-only, 10 пользователей, 1 минута:

- XLSX p95 37 мс, XLS p95 60 мс, PDF p95 180 мс;
- 308 запросов, 0 ошибок, агрегированный p95 120 мс.

Toggle этапа, 10 администраторов, 30 секунд:

- disable p95 17 мс, enable p95 16 мс;
- 308 запросов, 0 ошибок.

HTML-отчёты находятся в `tests/load/reports/`. Все цифры получены
фактическим запуском и относятся к локальному SQLite, а не к production.

## Локальный прогон 22.09.2026

Реальный headless-запуск выполнен на локальном SQLite backend:

- 50 пользователей, ramp-up 5 пользователей/с, 60 секунд;
- 1613 запросов, 0 ошибок;
- агрегированный p95: 93 мс, максимум 400 мс;
- p95 API без login: отчёты 17 мс, Kanban 76 мс, справочники 9–40 мс;
- HTML-отчёт: `tests/load/report-after.html`.

Отдельный прогон отчётов:

- 10 пользователей, ramp-up 10 пользователей/с, 30 секунд;
- 303 запроса, 0 ошибок;
- p95 отчётов: 7 мс, агрегированный p95: 77 мс;
- HTML-отчёт: `tests/load/report-10-reports.html`.

Целевой агрегированный p95 менее 1000 мс достигнут в этом локальном прогоне.
Результаты относятся к SQLite backend на машине разработки и не заменяют
проверку production-контура.
