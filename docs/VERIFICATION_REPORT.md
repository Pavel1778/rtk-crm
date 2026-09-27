# Статическая верификация RTK CRM

Дата: 2026-09-22  
Ветка: `dev`  
Репозиторий: `github.com/Pavel1778/rtk-crm`

Проверены исходный код, конфигурация, документация, генерация экспортов,
frontend build и разрешённый Locust-прогон. Браузерный smoke-test и Docker
Compose не запускались.

## Актуализация после performance/UI блока

Последующие коммиты на `dev`:

| Коммит | Что сделано |
|---|---|
| `4cac43e` | Redis/in-process TTL-кэш отчётов, инвалидация после mutations, индексы и устранение N+1 |
| `853de15` | Отдельный сценарий `ReportsUser` для параллельных отчётов |
| `0698e76` | Документация JWT/Keycloak, `MOCK_MODE`, production URLs и ссылки проекта |
| `354f67c` | Vite manual chunks и перевод legacy UI-цветов на `--atmr-*` tokens |
| `0df43eb` | Исправлен выбор `ReportsUser` в Locust CLI (`weight=1`) |

Фактический локальный прогон на SQLite backend:

- 50 пользователей / 60 секунд: 1613 запросов, 0 ошибок, aggregate p95 93 мс;
- 10 пользователей `ReportsUser` / 30 секунд: 322 запроса, 0 ошибок,
  p95 `/api/reports` 7 мс, aggregate p95 77 мс.
- 50 пользователей / 3 минуты, смешанный read/write: 4673 запроса, 0 ошибок,
  p95 create 32 мс, move 43 мс, comments 45 мс, upload 33 мс,
  XLSX 48 мс, XLS 76 мс, PDF 210 мс, aggregate p95 110 мс;
- 10 пользователей / 1 минута, exports-only: 308 запросов, 0 ошибок,
  p95 XLSX 37 мс, XLS 60 мс, PDF 180 мс;
- 10 администраторов / 30 секунд, toggle этапа: 308 запросов, 0 ошибок,
  p95 disable 17 мс, enable 16 мс.

Эти значения относятся к локальному SQLite окружению и не являются SLA
production Render/Supabase.

## Итог

- `✅ OK` — 35 пунктов;
- `⚠️ Warning` — 8 пунктов;
- `❌ Bug` — 0 незакрытых пунктов.

Найденные исправимые дефекты закрыты коммитами:

| Коммит | Что исправлено |
|---|---|
| `9611446` | RBAC справочников и импортов, production `SECRET_KEY`, CORS origins, проверка MIME/расширений, аудит, имена экспортов, тест экспортов, системный шрифт PDF, удаление секрета из Compose |
| `56d3fe0` | корневой `SECURITY.md`, актуальная архитектура документации, responsive/theme tokens, легенда и размеры графиков |
| `b69b813` | фильтры отчёта по периоду, этапу, вузу, продукту, направлению и ответственному; фильтры экспортов |
| `4155019` | устранение hardcoded-цветов в отчётах |
| `9643426` | удаление credential defaults из deployment-файлов и секретов из deployment-документации |
| `7324df1` | React Query caching для страницы отчётов |

## Актуализация после этапов A и B (23.09)

Коммиты на `dev`:

| Коммит | Что сделано |
|---|---|
| этап A | PDF-отчёт: динамические ширины колонок, перенос длинных значений, landscape при >5 колонках, DejaVu Sans; CORS с точным origin и `expose_headers`; единый date-picker диапазона с пресетами |
| этап A (доработка) | фильтр диапазона дат добавлен на Kanban-доску (`date_from`/`date_to` в `/api/interactions/board`), конец периода включается целиком, перевёрнутый диапазон даёт 400 |
| этап B | адаптивная лупа поиска по вузу; проценты на слайсах диаграммы «Доля продуктов»; единый компонент таблицы этапов |
| `7ccbbc0` | пересортировка этапов: двухпроходное обновление порядка вместо прямого присваивания, устранён 500 из-за `UNIQUE(scope, order)` |
| `017054c` | единый адаптивный `StageTable` для конструктора workflow и админских настроек |
| `d32a1f0` | единый конфиг колонок отчёта для интерфейса и выгрузок PDF/XLSX/XLS/JSON |

Проверки после этапов A и B:

- `python -m pytest` — 48 тестов, все зелёные (включая новые наборы
  `test_pdf_layout.py`, `test_cors.py`, `test_report_columns.py` и три
  регрессионных теста пересортировки этапов);
- `npx tsc --noEmit` — 0 ошибок; `npm run build` — успешно;
- браузерная проверка (Chromium, Playwright): таблица этапов на 375px
  показывает карточки, на 768px и 1440px — таблицу, горизонтального
  переполнения нет; страница отчётов на 375px использует короткие
  заголовки колонок (как в PDF), на 1440px — полные (как в XLSX);
- drag-and-drop этапов уходит одним запросом `POST /api/stages/reorder`
  и возвращает 200, порядок сохраняется в БД.

## Актуализация после этапа C (23.09)

Коммиты на `dev`:

| Коммит | Что сделано |
|---|---|
| `3dde8ca` | структурные проблемы валидации импорта и генератор XLSX-отчёта |
| `de4002d` | эндпоинт `POST /api/catalogs/import/report` |
| `e0633d7` | исправлена загрузка файлов из интерфейса (Content-Type для FormData) |
| `896535b` | сводка проверки и таблица проблем в окне импорта |
| `d1bc614` | кнопки «Импортировать только валидные / Отменить / Скачать отчёт» |
| `a465903` | тест смешанного импорта со счётчиком пропущенных |
| `d7b1077` | сервис рендера руководств в PDF и сборка `frontend/public/docs/*.pdf` |
| `579bdd2` | вкладка «Помощь»: оглавление с якорями, поиск, скачивание PDF |

### C.1. Проверка корректности импорта

Что проверено:

- `python -m pytest` — 60 тестов, все зелёные (добавлен
  `tests/test_import_report.py`: 8 модульных тестов валидации и 4 теста
  контракта эндпоинта — 401 без токена, XLSX с заголовками-счётчиками,
  400 на неизвестный `catalog_type` и на не-Excel файл, импорт только
  валидных строк);
- `npx tsc --noEmit` — 0 ошибок; `npm run build` — успешно;
- браузерная проверка (Chromium, Playwright) на `/directories`: файл из
  4 строк (1 ошибка, 2 предупреждения) открывает окно импорта, сводка
  показывает «Строк в файле: 4», «Ошибки: 1», «Предупреждения: 2»,
  таблица проблем содержит строку, поле, причину и уровень; кнопки
  «Импортировать только валидные (3)», «Отменить» и «Скачать отчёт об
  ошибках (XLSX)» доступны. Импорт создаёт 2 записи, тост сообщает
  «Импортировано записей: 2; пропущено строк: 1», окно закрывается,
  горизонтального переполнения нет.

Важное исправление: глобальный заголовок `Content-Type: application/json`
перекрывал multipart-границу, и импорт справочников через интерфейс
отвечал `422 Field required: file`. Заголовок теперь снимается для
`FormData`, поэтому сценарий импорта работает end-to-end.

### C.2. Вкладка «Помощь»: навигация, поиск и PDF

Что проверено:

- `python -m pytest` — 65 тестов, все зелёные (добавлен
  `tests/test_guide_pdf.py`: 5 тестов на конвертер — все разделы
  `USER_GUIDE.md` и `ADMIN_GUIDE.md` доезжают до PDF, кириллица и inline
  разметка не теряются, картинки встраиваются как XObject, отсутствующая
  картинка не ломает рендер);
- `npx tsc --noEmit` — 0 ошибок; `npm run build` — успешно;
- `python scripts/render_guide_pdfs.py` — собирает `user-guide.pdf`
  (4 страницы) и `admin-guide.pdf` (3 страницы) в `frontend/public/docs/`;
- браузерная проверка (Chromium, Playwright) на `/help`: оглавление
  содержит 10 разделов, поиск фильтрует список по заголовкам, клик по
  пункту оглавления прокручивает документ к нужному заголовку,
  переключение на руководство администратора перестраивает оглавление,
  кнопка «Скачать PDF» доступна, 5 картинок руководства отрисованы,
  горизонтального переполнения и ошибок в консоли нет.

Важное исправление: `id` заголовков начинались с цифры
(`#3-dashbord-i-navigaciya`), из-за чего `querySelector` падал с
`SyntaxError` и переход по оглавлению не работал. Якоря получили префикс
`section-`. Заодно одиночная картинка Markdown больше не оборачивается в
`<figure>` внутри `<p>` — устранено предупреждение `validateDOMNesting`.

## 1. Экспорты и отчёты

| Проверка | Статус | Доказательство |
|---|---|---|
| XLSX генерируется через `openpyxl` | `✅ OK` | `backend/services/excel_export.py:6-11,30-107` |
| XLS генерируется через `xlwt` с именованным цветом | `✅ OK` | `backend/services/excel_export.py:13-17,110-157` |
| PDF генерируется ReportLab | `✅ OK` | `backend/services/excel_export.py:19-27,160-193` |
| Кириллица в PDF | `✅ OK` | `backend/services/excel_export.py:175-193`; `backend/Dockerfile:7-10` |
| PDF landscape и повтор заголовка таблицы | `✅ OK` | `backend/services/excel_export.py:166-173,235-248` |
| Обязательные колонки экспорта | `✅ OK` | `backend/services/excel_export.py:39-48,118-127,211-220` |
| `Content-Disposition` и CORS expose headers | `✅ OK` | `backend/api/reports.py:351-359,388-397,425-433`; `backend/main.py:63-70` |
| ASCII-имена `rtk-report-YYYYMMDD.ext` | `✅ OK` | `backend/api/reports.py:33-34` |
| Bearer-защита `/api/reports*` | `✅ OK` | `backend/api/reports.py:74-85,326-336,363-373,400-410`; прямой запрос без токена ожидаемо даёт 401 |
| In-memory экспорт | `✅ OK` | `scripts/export_smoke.py`; получены XLSX 5 KB, XLS 5 KB, PDF 47 KB; XLSX читается `openpyxl`, PDF имеет `%PDF` и DejaVu |

## 2. Данные графиков и фильтрация

| Проверка | Статус | Доказательство |
|---|---|---|
| `by_stage` содержит все активные этапы, включая нулевые | `✅ OK` | `backend/api/reports.py:140-166,192-200` |
| `by_product` не теряет взаимодействия без продукта | `✅ OK` | `backend/api/reports.py:168-190`; категория `Без продукта` |
| Динамика заполняет пропущенные даты нулями | `✅ OK` | `backend/api/reports.py:202-243` |
| Фильтры периода/этапа/вуза/продукта/направления/ответственного | `✅ OK` | `backend/api/reports.py:37-71,74-100`; `frontend/src/api/endpoints.ts:158-185` |
| UI-фильтр периода и передача фильтра в экспорт | `✅ OK` | `frontend/src/pages/ReportPage.tsx:32-62,117-152` |
| Вертикальная диаграмма этапов и усечение подписей | `✅ OK` | `frontend/src/pages/ReportPage.tsx:181-224` |
| Полное имя этапа в tooltip | `✅ OK` | `frontend/src/pages/ReportPage.tsx:210-216` |
| Круговая диаграмма продуктов и responsive legend | `✅ OK` | `frontend/src/pages/ReportPage.tsx:239-267` |
| Динамика без точек и с `minTickGap=24` | `✅ OK` | `frontend/src/pages/ReportPage.tsx:278-300` |
| Loading/empty/error states | `✅ OK` | `frontend/src/pages/ReportPage.tsx:63-86,170-176,235-237,273-275` |

## 3. Функциональное ТЗ 1–13

| Пункт | Статус | Доказательство / примечание |
|---|---|---|
| 1. Каталоги и импорт XLS/XLSX | `✅ OK` | `backend/api/catalogs.py:16-89`; маппинг в `backend/services/excel_import.py` |
| 2. Отчёты по периоду с фильтрами | `✅ OK` | `backend/api/reports.py:74-100`; UI периода в `frontend/src/pages/ReportPage.tsx:117-152` |
| 3. Фильтры вуз/направление/продукт/ответственный | `✅ OK` | API поддерживает все четыре фильтра: `backend/api/reports.py:47-56` |
| 4. Recharts и экспорт | `✅ OK` | `frontend/src/pages/ReportPage.tsx:181-300`; export routes |
| 5. Переходы этапов и комментарии | `✅ OK` | `backend/api/interactions.py:139-176,328-345`; frontend drawer/comments |
| 6. PNG/JPEG/PDF/ZIP/GZIP/RAR/DOC/DOCX/XLS/XLSX | `✅ OK` | `backend/api/files.py:20-50,74-98` |
| 7. Колонки XLS/XLSX/PDF | `✅ OK` | `backend/services/excel_export.py:39-48,118-127,211-220` |
| 8. JSON endpoint | `✅ OK` | `backend/api/reports.py` JSON route с `get_current_user` |
| 9. Создание/обновление workflow | `✅ OK` | `backend/api/stages.py:76-135`; mutation доступна admin |
| 10. Keycloak или MOCK_MODE | `⚠️ Warning` | Текущий рабочий контур использует JWT+bcrypt: `backend/auth/security.py:15-64`; Keycloak присутствует только в legacy/target Compose |
| 11. RBAC user/manager/admin | `✅ OK` | `backend/auth/security.py:67-88`; справочники и каталоги защищены manager/admin |
| 12. Web UI | `⚠️ Warning` | Код и production build проверены, браузерный smoke-test запрещён текущим заданием |
| 13. React Query caching | `✅ OK` | `frontend/src/main.tsx:13-21`; отчёты используют `useQuery`: `frontend/src/pages/ReportPage.tsx:34-49` |

## 4. Безопасность и privacy

| Проверка | Статус | Доказательство |
|---|---|---|
| JWT expiry 1440 минут | `✅ OK` | `backend/core/config.py:22-24` |
| bcrypt | `✅ OK` | `backend/auth/security.py:15,25-30` |
| Production secret validation | `✅ OK` | `backend/core/config.py:39-48` |
| Явный CORS без wildcard при credentials | `✅ OK` | `backend/main.py:59-71` |
| User context в audit | `✅ OK` | `backend/auth/security.py:42-64`; `backend/middleware/audit.py:33-65` |
| Collection-level audit и редактирование секретных полей | `✅ OK` | `backend/middleware/audit.py:77-121` |
| MIME + extension + 50 MB upload limit | `✅ OK` | `backend/api/files.py:20-50,74-94` |
| SQLAlchemy ORM | `✅ OK` | Checked backend API/services; raw SQL only fixed health/DDL statements |
| `.env` не отслеживается, examples разрешены | `✅ OK` | `.gitignore`, tracked files `backend/.env.example`, `frontend/.env.example` |
| Старые секреты в Git history | `⚠️ Warning` | Текущие файлы очищены. Проверка всех 952 blob-объектов не нашла реальных сторонних учётных данных (Supabase/Render/GigaChat): в истории только placeholder'ы. Ротация сторонних ключей не требуется. Уточнено в `docs/CLEANUP_REPORT.md`: если контур поднимался из `docker-compose.yml` без переопределения, заменить нужно только локальный `SECRET_KEY` |

## 5. Workflow, RBAC и cookie consent

| Проверка | Статус | Доказательство |
|---|---|---|
| Все этапы в конструкторе | `✅ OK` | `frontend/src/pages/SettingsPage.tsx:285` загружает `listStages(true)`, `StageTable` показывает этапы выбранной воронки |
| Только активные этапы в Kanban | `✅ OK` | `frontend/src/pages/BoardPage.tsx` и `useStages('active')` |
| Optimistic update/rollback | `✅ OK` | `frontend/src/hooks/useStages.ts:27-59` |
| 409 при активных взаимодействиях | `✅ OK` | `backend/api/stages.py:120-130` |
| Impact и перенос при удалении | `✅ OK` | `backend/api/stages.py:41-59,180-205`; `frontend/src/components/workflow/DeleteStageModal.tsx` |
| Disabled opacity 0.55 | `✅ OK` | `frontend/src/index.css:401-404` |
| Cookie schema и necessary locked | `✅ OK` | `frontend/src/lib/cookieConsent.ts:1-94`; banner/settings components |
| Privacy routes и footer links | `✅ OK` | `frontend/src/pages/CookiePolicyPage.tsx`, `PrivacyPolicyPage.tsx`, `frontend/src/components/AppFooter.tsx:21-24` |
| Cookie-баннер на мобильных | `✅ OK` | Ручная проверка в DevTools (iPhone SE / Galaxy S20 / iPhone 14 Pro Max) — баннер 25–35% экрана, кнопки столбиком, модалка в пределах экрана |

## 6. Нефункциональные требования и документация

| Проверка | Статус | Доказательство / примечание |
|---|---|---|
| Production response target ≤1 s | `⚠️ Warning` | Локальный прогон достиг aggregate p95 93 мс, но production SLA отдельно не подтверждён |
| 50 concurrent users | `✅ OK` | Реальный локальный прогон: 1613 запросов, 0 ошибок |
| 10 concurrent report requests | `✅ OK` | Реальный `ReportsUser`: 322 запроса, 0 ошибок, `/api/reports` p95 7 мс |
| Write-профиль интерфейса | `✅ OK` | 4673 запроса за 3 минуты: create/move/comment/upload/export без ошибок |
| Toggle workflow stage | `✅ OK` | 308 запросов: disable/enable через PATCH без ошибок |
| SPA и viewport | `✅ OK` | `frontend/index.html:5`; React Router и Vite build |
| Коды 400/401/403/404/409/422/500 | `✅ OK` | Проверены статически по FastAPI routes/handlers; `422` handler: `backend/main.py:74-89` |
| USER_GUIDE и ADMIN_GUIDE | `✅ OK` | Файлы присутствуют |
| SECURITY.md с 152-ФЗ и миграцией Yandex Cloud | `✅ OK` | `docs/SECURITY.md:1-34` |
| DEPLOYMENT.md Render/Vercel/Supabase/Yandex Cloud | `✅ OK` | `docs/DEPLOYMENT.md`; credentials заменены placeholders |
| ARCHITECTURE и C4 Mermaid | `✅ OK` | `docs/architecture/ARCHITECTURE.md`, `c4-context.md`, `c4-components.md` |
| Archi: функциональная и компонентная (ТЗ 6.7) | `✅ OK` | `functional.archimate` (5 шагов пути + сервисы), `rtk-crm.archimate` (контейнеры); ER — `er.archimate`. PDF: `functional.pdf`, `er-model.pdf` |
| Pitch 11 слайдов | `✅ OK` | `docs/pitch.md` |
| QA 20 вопросов/ответов | `✅ OK` | `docs/qa-jury.md` |
| Реальные screenshots в `docs/images/` | `✅ OK` | 10 PNG в `docs/images/`, подставляются в руководства и PDF через `scripts/render_guide_pdfs.py` |

## 7. Atomaro UI и качество кода

| Проверка | Статус | Доказательство / примечание |
|---|---|---|
| `--atmr-*` tokens и theme classes | `✅ OK` | `frontend/src/index.css:1-24`; light class в `MainLayout.tsx` |
| Радиусы/spacing/responsive grids | `✅ OK` | `frontend/src/index.css`; report layout |
| Mobile table/export/chart handling | `✅ OK` | responsive classes in `frontend/src/index.css`; responsive legend in `ReportPage.tsx` |
| Footer safe-area и max-content | `✅ OK` | `frontend/src/components/AppFooter.tsx:8-15` |
| Hardcoded colors | `✅ OK` | Рабочие UI-использования переведены в `--atmr-*`; HEX остались только в определениях токенов и native color inputs |
| TypeScript build | `✅ OK` | `source ~/.nvm/nvm.sh && npm run build`; build завершён, Vite сообщил только размер bundle >500 KB |
| Python compileall | `✅ OK` | `python3 -m compileall -q backend/... scripts tests/load` |
| `git diff --check` | `✅ OK` | Выполнено после финальных правок |
| print/TODO/console.log/`: any` scan | `✅ OK` | Статический `rg` scan не выявил совпадений в проверенных директориях |

## Актуализация после аудита против ТЗ (23.09)

Коммиты на `dev`:

| Коммит | Что сделано |
|---|---|
| `f58b7a6` | доступ к взаимодействиям по id: КАМ работает только со своими карточками |
| `a8bf9c1` | управление пользователями в интерфейсе (вкладка «Пользователи») и журнал аудита 152-ФЗ (`GET /api/audit`, раздел «Журнал») |
| `ef1069c` | доступ к файлам наследует доступ взаимодействия; проверка общая в `backend/api/access.py` |

### Что проверено по бизнес-правилам ТЗ

- **«Вуз + продукт» единственным взаимодействием** — `_ensure_unique`
  проверяет и создание, и смену продукта; дубликат отклоняется `409`.
- **Не более двух параллельных взаимодействий на вуз** — `_ensure_parallel_limit`
  применяется при создании и при возврате карточки в активные.
- **Скоуп воронки** — карточка B2C не встаёт в B2B-колонку и наоборот.
- **RBAC** — КАМ (`user`) ограничен своими взаимодействиями на чтении,
  обновлении, перемещении, удалении, комментариях и файлах; руководитель
  и администратор видят всё. Навигация и страницы админа скрыты для
  остальных ролей.
- **Назначение ответственного** — КАМ при создании становится ответственным
  сам; руководитель/администратор выбирают любого КАМ в окне создания и
  может передать существующую карточку.

### Проверки

- `python -m pytest` — 90 тестов, все зелёные (`test_audit_log.py` — 8,
  `test_interaction_access.py` — 14, включая 5 сценариев доступа к файлам);
- `npx tsc --noEmit` — 0 ошибок; `npm run build` — успешно;
- `python scripts/render_guide_pdfs.py` — `admin-guide.pdf` пересобран с
  разделами про пользователей и журнал.

## Актуализация после финального аудита (24.09)

Коммиты на `dev`:

| Коммит | Что сделано |
|---|---|
| `86d57b8` | CI: линтер, типы и тесты в GitHub Actions, общий кодстайл |
| `3527936` | журнал аудита: фильтры по сотруднику и периоду, выгрузка CSV |

### Что добавлено/закрыто

- **Импорт JSON** — валидация верхнего уровня по JSON Schema (Draft 7):
  принимается массив объектов либо `{"data": [...]}`; ошибки возвращаются с
  путём до поля, пустые объекты записей и отсутствие обязательного
  `Название` отклоняются. Покрыто `tests/test_excel_import.py` (7 тестов).
- **Seed-скрипт** — `scripts/seed.py` (флаг `--reference`) как обёртка над
  `backend/seed.py`; общий бутстрап импорта вынесен в `scripts/_bootstrap.py`.
- **CORS** — хост стенда предпросмотра больше не зашит в код: шаблон приходит
  через `CORS_ORIGIN_REGEX`, по умолчанию выключен (см. `docs/DEPLOYMENT.md`).
- **SAST/SCA** — `docs/security/SAST-SCA.md`: пины зависимостей backend,
  `npm audit` = 0 уязвимостей, остаточный риск `ecdsa 0.19.2`
  (PYSEC-2026-1325) принят и обоснован (используется HS256).
- **Архитектура** — `docs/architecture/functional.md` и `er-model.md`
  добавлены; `ARCHITECTURE.md` дополнен разделом масштабирования 300+ (KeyDB).

### Проверки

- `python -m pytest` — 98 тестов, все зелёные;
- `ruff check backend/ tests/ scripts/ conftest.py` — All checks passed;
- `mypy backend/` — no issues found in 40 source files;
- `bandit -c pyproject.toml -r backend/` — 0 issues;
- `npx tsc --noEmit` — 0 ошибок; `npm run build` — успешно; `npm audit` — 0;
- `python scripts/seed.py` — справочники и демо-данные создаются идемпотентно.

## Актуализация после проверки структуры (24.09)

Проверка дерева проекта на расхождения выявила два дефекта; оба закрыты.

### 1. Зеркало документации расходилось с источниками

Вкладка «Помощь» отдаёт Markdown из `frontend/public/docs/`, но эта копия
поддерживалась вручную и отстала от `docs/`:

- `ADMIN_GUIDE.md`, `SECURITY.md`, `ARCHITECTURE.md` содержали более ранние
  редакции (не было воронки B2C, кэша отчётов, rate limit, планировщика);
- `architecture/functional.md`, `er-model.md`, `security/SAST-SCA.md` и
  `STACK.md` вообще отсутствовали, хотя исходные документы на них ссылаются, —
  внутренние ссылки в Help вели в никуда;
- картинка `10-help-docs.png` отличалась от исходной.

Теперь зеркало собирается детерминированно: `scripts/sync_public_docs.py`
копирует набор документов и переписывает относительные ссылки в абсолютные
(`/docs/...`), потому что страница рендерится по маршруту `/help`. Повторный
прогон не меняет дерево. За дрейфом следит `tests/test_docs_mirror.py`
(6 тестов): синхронизация воспроизводима, все ссылки разрешаются, относительных
ссылок и битых картинок нет.

### 2. Бэкенд в контейнере не находил конфиг колонок отчёта

`backend/services/report_columns.py` читал конфиг как
`Path(__file__).parents[2] / "config" / "report_columns.json"`. В образе код
лежит в `/app` (build context — `backend/`), поэтому путь указывал на
`/config/report_columns.json`, а каталог `config/` в образ не попадал —
выгрузки XLSX/XLS/PDF и `/api/reports/columns` падали бы в Docker.

Исправлено: путь выбирается из кандидатов (корень репозитория и `/config`) с
поддержкой явного `REPORT_COLUMNS_CONFIG`; в оба compose-файла добавлен
read-only mount `./config:/config`. Покрыто тестами в
`tests/test_report_columns.py`.

### Проверки

- `python -m pytest` — 110 тестов, все зелёные (было 98);
- `ruff check backend/ tests/ scripts/ conftest.py` — All checks passed;
- `mypy backend/` — no issues found in 40 source files;
- `npx tsc --noEmit` — 0 ошибок; `npm run build` — успешно;
- `python scripts/sync_public_docs.py` — идемпотентен, зеркало совпадает с `docs/`;
- `bash backend/start.sh` — поднимается и отдаёт `{"status":"ok"}` на `/api/health`.

## Актуализация: документация запуска (24.09, второй проход)

Проверка команд из README и `docs/DEPLOYMENT.md` на исполняемость выявила,
что документированный локальный запуск backend не работает.

### 3. `uvicorn backend.main:app` не мог запуститься

Приложение импортируется как пакет `app` (в контейнере — `/app`, в репозитории
— `backend/`), при этом `backend/main.py` импортирует `app.*`. Поэтому
`uvicorn backend.main:app` из корня падал с `ModuleNotFoundError: app`.
Именно поэтому тесты и `scripts/_bootstrap.py` создают временный алиас
`app -> backend`.

Добавлен `scripts/run_dev.py` — делает пакет импортируемым и поднимает uvicorn
с автоперезагрузкой (проверено: `/api/health` отвечает 200). README и
`docs/DEPLOYMENT.md` переведены на него.

### 4. `backend/start.sh` использовал тот же нерабочий путь

Render-скрипт импортировал `backend.db.session` / `backend.seed` и запускал
`uvicorn backend.main:app`. Теперь он создаёт алиас `app -> backend` (как в
`conftest.py`) и работает через `app.*`; проверено запуском.

### 5. Расхождения в документации

- `docs/README.md`: дерево проекта описывало несуществующий вид
  (`backend/api/models/`, `backend/api/api/`, отсутствие `auth/`,
  `middleware/`, `services/`, `config/`); технологическая таблица указывала
  FastAPI 0.104 (фактически 0.141) и активный Keycloak 24.0 (фактически JWT);
  команда инициализации БД была `docker exec rtk_backend python seed.py` —
  в контейнере код в `/app`, поэтому верно `python /app/seed.py` или
  `python scripts/seed.py` из репозитория.
- `README.md` и `docs/DEPLOYMENT.md`: `.env` предлагалось класть в `backend/`,
  но `Settings` читает `.env` из текущего каталога — при запуске из корня файл
  игнорировался.
- `README.md`: ссылка на `docs/ARCHITECTURE.md`, которого нет (`docs/README.md`
  и `docs/architecture/` вместо него).
- `docs/DEPLOYMENT.md`: утверждалось, что `start.sh` — это CMD образа; на деле
  CMD — `uvicorn app.main:app`, схема и справочники создаются в lifespan
  приложения.
- `docs/architecture/ARCHITECTURE.md`: Keycloak 24.0 был указан как активный
  Auth Server; заменено на JWT + bcrypt с пометкой про целевой контур.

За регрессиями следит `tests/test_dev_entrypoint.py`.

## Критично: падение деплоя на Render (24.09)

Прод падал при старте с `FileNotFoundError: '/config/report_columns.json'` и
`Exited with status 1`. Разбор:

- `backend/services/report_columns.py` читает конфиг **на импорте модуля**;
- Docker/Render собирают образ с build context `backend/`, поэтому корневой
  `config/` в образ не попадает;
- в Compose путь закрывался монтированием `./config:/config:ro`, а на Render
  монтирования нет — `/config/report_columns.json` отсутствует, импорт
  `app.main` падает, контейнер завершается с кодом 1.

Исправление:

- канонический конфиг дублируется в `backend/config/report_columns.json`
  (`scripts/sync_report_columns.py`); копия попадает в образ;
- `report_columns.config_candidates()` проверяет пути по порядку:
  bundled `backend/config/` → корневой `config/` → `/config`;
- `REPORT_COLUMNS_CONFIG` по-прежнему переопределяет путь.

Проверено симуляцией layout образа (`app/` = только содержимое `backend/`,
без корневого `config/`): импорт `app.main` и `PDF_COLUMNS` проходят.
Регрессии — `tests/test_report_columns.py` (bundled-копия, порядок
кандидатов, идемпотентность синхронизации).

Дополнительно исправлено:

- `scripts/test_export.py` → `scripts/export_smoke.py`: скрипт назывался
  `test_*` (pytest его не собирает, т.к. лежит вне `tests/`) и падал с
  `ModuleNotFoundError: app` — импортировал `backend.services.*` без
  bootstrap-алиаса. Теперь использует `ensure_app_importable()` и запускается.

## Осталось

1. Ротировать credentials, которые ранее попали в историю Git; удаление из текущего
   состояния не отзывает старые значения.
2. Отдельно проверить production latency на Render/Supabase; локальный target достигнут.
3. При необходимости заменить JWT на Keycloak/добавить явно документированный
   `MOCK_MODE`, если это обязательное условие комиссии, а не альтернативный вариант.

## Прод-инцидент 24.09: схема БД без `scope` (исправлено)

Симптом (лог Render): `Ошибка загрузки демо-данных: column
workflow_stages.scope does not exist`; прод-база пустая; `GET /` → 404.

Причина: прод-схема создана ранней версией приложения через
`create_all(checkfirst=True)`, который существующие таблицы не изменяет.
Alembic-миграция схему описывала, но не применялась: `alembic.ini` лежит в
корне репозитория, а Docker build context — `backend/`, поэтому CLI в образе
недоступен. В прод-БД отсутствовали `workflow_stages.scope`,
`interactions.scope`, а уникальность задавалась глобально по `code`/`order`.

Исправление (коммит `5cf3855`, PR #13):

| Изменение | Что делает |
|---|---|
| `backend/db/schema_sync.py` | идемпотентная сверка схемы с моделями: добавляет `scope` (`DEFAULT 'b2b'`) и индексы, заменяет глобальные UNIQUE на составные `(scope, code)`/`(scope, order)`; SQLite — пересоздание с копированием данных, Postgres — `ALTER TABLE`; помечает головную ревизию Alembic |
| `backend/main.py` | `ensure_schema()` в `lifespan`; `GET /` отдаёт ссылки вместо 404 |
| `backend/start.sh` | тот же порядок инициализации без Docker |
| `README.md`, `docs/DEPLOYMENT.md`, `LoginPage.tsx` | реальный демо-аккаунт КАМ `kam@rtk.ru`/`kam123` вместо несуществовавшего `user@rtk.ru` |

Проверка после деплоя (24.09, Render/Supabase):

- `GET /` → 200 `{"service":"RTK CRM",...}`;
- `GET /healthz` → 200; `GET /readyz` → 200 (`database: ok`);
- этапы: 18 (14 B2B + 4 B2C);
- вузы: 5; взаимодействия: 7 — демо-данные загружены.

Локальная верификация: 125 тестов зелёные, `ruff`/`mypy` чисто, `tsc` без
ошибок; E2E на legacy-схеме — сверка применена, `compare_metadata` без
расхождений.

## Актуализация: запуск одной командой и CI SourceCraft (26.09)

Задача — чтобы `docker compose up -d` работал на чистой машине и чтобы
проверки выполнялись и на зеркале в SourceCraft.

### 1. `docker compose` не собирался без переменных окружения

`docker compose config` завершался с ошибкой интерполяции: compose требует
`MINIO_ROOT_PASSWORD` и `KEYCLOAK_ADMIN_PASSWORD` (синтаксис `${VAR:?}`),
а шаблона `.env.example` в корне репозитория не было — существовали только
`backend/.env.example` и `frontend/.env.example`, где этих имён нет.

Добавлен корневой `.env.example`. Имена переменных взяты из
`docker-compose.yml` и `backend/core/config.py`, а не из стороннего описания:
в частности, хранилище настраивается через `MINIO_ROOT_*`/`S3_*`, а не
`MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`, ключ GigaChat называется
`GIGACHAT_CREDENTIALS`, а не `GIGACHAT_AUTH_KEY`.

Проверено: `docker compose --env-file <тест> config` → exit 0, 7 сервисов
(`redis`, `minio`, `minio-init`, `backend`, `frontend`, `keycloak`, `nginx`).

### 2. Переменные не доходили до контейнера backend

Compose передавал в backend только `DATABASE_URL`, `REDIS_URL`, `S3_*`,
`KEYCLOAK_URL`, `PYTHONPATH` и `CORS_ORIGINS`. Всё остальное, включая
`SECRET_KEY`, `AUTH_MODE` и `GIGACHAT_*`, в контейнер не попадало: приложение
работало на значениях по умолчанию из `config.py`, а переключить
`AUTH_MODE=keycloak` через `.env` было невозможно.

Добавлена передача `SECRET_KEY`, `AUTH_MODE`, `KEYCLOAK_REALM`,
`KEYCLOAK_CLIENT_ID`, `KEYCLOAK_AUDIENCE`, `GIGACHAT_*`, `SEED_DEMO_DATA` и
параметров уведомлений. Логин администратора Keycloak вынесен в
`KEYCLOAK_ADMIN_USERNAME` (раньше был захардкожен `admin`).

Проверено разбором `docker compose config`: значения доходят до сервиса
backend.

### 3. Миграции и seed вручную запускать не нужно

`backend/main.py` в `lifespan` выполняет `create_tables()` → `ensure_schema()`
→ `seed_demo()`. Поэтому команда вида `alembic upgrade head && python -m
scripts.seed && uvicorn ...` в контейнере нерабочая: `alembic.ini` лежит в
корне репозитория и в образ не попадает (build context — `backend/`), а
`scripts/` в образ не копируется. Это уже приводило к прод-инциденту 24.09
(см. раздел выше). В README зафиксировано, что инициализация автоматическая.

### 4. CI для SourceCraft

Добавлен `.sourcecraft/ci.yaml` с теми же проверками, что в
`.github/workflows/ci.yml`: `ruff`, `mypy`, `pytest` для backend и
`tsc --noEmit` + `npm run build` для фронтенда. Пути соответствуют структуре
репозитория — тесты лежат в `tests/`, а не в `backend/tests/`.

### Проверка контейнеров

Ранее запуск контейнеров выполнить не удавалось: Docker-демон был недоступен,
доступна только CLI, поэтому проверка была статической. Docker поднят, стек
проверен вживую.

Что запускалось: `redis`, `backend`, `frontend`, `nginx` — собраны из
репозитория и подняты в одной пользовательской сети. Образы `minio/minio` и
`minio/mc` в этой среде недоступны (pull access denied), поэтому S3-хранилище
проверялось в режиме `S3_ENDPOINT=""`: файлы пишутся в локальный `uploads/`.
Контейнер `keycloak` проверялся отдельно при отладке `redirect_uri`.

| Проверка | Результат |
|---|---|
| `GET /healthz` | `200`, `{"status":"ok"}` |
| `GET /readyz` | `200`, `{"status":"ok","checks":{"database":"ok","cache":"ok","storage":"local"}}` |
| `GET /` | `200`, отдаёт ссылки на `docs`/`healthz`/`readyz` |
| Старт приложения | схема сверена (`ensure_schema`), демо-данные загружены, планировщик запущен |
| `POST /api/auth/login` (admin, manager) | токен выдан |
| `GET /api/auth/me` с токеном | `200`, роль и `is_admin` соответствуют пользователю |
| `GET /api/universities` без токена | `401` |
| `GET /` через frontend (nginx) | `200`, отдаётся `index.html` приложения |
| SPA-fallback (`/interactions`) | `200` |
| `/api/auth/me` через прокси frontend | `200` — same-origin схема работает |
| `/api/health`, `/health` через корневой nginx | `200` |

Найден и исправлен дефект корневого nginx: конфиг `nginx/nginx.conf` отдавал
`location /` из `/usr/share/nginx/html`, но в образе nginx собранной статики
нет — запрос на порт 80 возвращал дефолтную страницу «Welcome to nginx!»,
хотя README указывает `http://localhost` как точку входа. Теперь `location /`
проксирует на контейнер `frontend`, как в прод-контуре на ВМ
(`infra/yandex-cloud/nginx-http.conf.template`).

`readyz` со статусом `unavailable` по кэшу воспроизводится только при запуске
контейнеров в дефолтной сети Docker: имена сервисов там не разрешаются, и
backend не видит `redis`. В пользовательской сети проверка проходит. На ВМ
используется отдельная сеть, поэтому к продукту это не относится.

## Актуализация: ER-модель, вёрстка презентации и Q&A (27.09)

Финальный проход перед сдачей. Три направления проверены отдельно, каждое —
на реальном артефакте, а не только по коду.

### 1. ER-диаграмма стала воспроизводимой

Раньше схема данных жила только текстом в `er-model.md`. Теперь Mermaid-блок
извлекается скриптом `scripts/extract_er_diagram.py` в `docs/architecture/er.mmd`,
а `mmdc` рендерит его в `er-model.pdf` и `er-model.png`.

Дополнительно собран файл Archi `docs/architecture/er.archimate` (ArchiMate 3,
5.0.0): 32 элемента в папке «Данные (ER)» — 11 сущностей, 14 связей и 7
Mini-Of-Entity. Файл открывается в [Archi](https://www.archimatetool.com/)
бесплатно, рядом лежит готовый PDF для тех, кому Archi не нужен.

| Проверка | Результат |
|---|---|
| `scripts/extract_er_diagram.py` | пишет `er.mmd`, 107 строк, начинается с `erDiagram` |
| Рендер `mmdc -i er.mmd -o er-model.pdf` | PDF ~170 КБ, одна страница |
| `er.archimate` | well-formed XML, `id="model-rtk-crm-er"`, 32 элемента |
| Ссылки в `ARCHITECTURE.md` и `architecture/README.md` | добавлены, зеркало синхронно |

### 2. Вёрстка презентации проверена рендером

Добавлен `scripts/check_presentation_layout.py`. Он конвертирует `.pptx` в PDF
через LibreOffice и ищет дефекты: текст за границей слайда, наложение
текстовых блоков, кегль меньше 14pt на обязательных слайдах 7–11 и
расхождение сетки этих слайдов с исходным шаблоном. Эвристики по
`python-pptx` для поиска наложений не используются — они давали ложные
срабатывания на групповых фигурах шаблона.

Обязательный блок ЛЦТ теперь занимает позиции 7–11 и повторяет слайды 7–11
шаблона один в один: сверка по геометрии блоков проходит с 0 дефектов.
Проверено при 960×540 pt: 11 слайдов, 0 дефектов вёрстки. Метаданные чистые:
`author` и `last_modified_by` — «Сабадаш Павел».

### 3. Вопросы жюри разложены на два блока

`docs/qa-jury.md` переработан: часть I — 20 продуктовых вопросов (проблема,
пользователь, Kanban, 14 этапов, доступ, данные, 152-ФЗ, экспорт, нагрузка,
масштабирование, мобильные, следующий шаг), часть II — 20 технических
(интеграция, версионирование workflow, аудит, RBAC, целостность при
параллельном обновлении, XLSX-импорт, KeyDB, LLM, Docker, документация).
Каждый ответ ссылается на конкретный файл, а не пересказывает ТЗ.

### Вывод

Все три артефакта воспроизводятся одной командой, зеркало документации не
расходится с источниками (`tests/test_docs_mirror.py` — 6 passed), а у
презентации нет визуальных дефектов при рендере.

## Актуализация: cookie-баннер на мобильных (27.09)

Проверка на реальных размерах экранов выявила пять дефектов в согласии на
cookie, которые видны только на телефоне.

### Что было сломано

| Дефект | Проявление |
|---|---|
| Баннер занимал экран | На iPhone SE (375×667) баннер — 70% высоты, кнопки столбиком в три ряда |
| `column` + `flex-wrap` | Кнопки уезжали во вторую колонку за пределы экрана |
| z-index баннера 1100 | Перекрывал футер модалки настроек: «Сохранить выбор» не нажималась |
| Модалка выше экрана | 4 категории + текст не влезали, кнопки оказывались за нижней кромкой |
| Хардкод отступа | `padding-bottom: 168px` был меньше реальной высоты мобильного баннера |

### Что изменено

- `.cookie-banner`: `z-index` снижен до 900 (модалка antd — 1000, поэтому
  футер снова доступен); ограничение `max-height: 55vh` со скроллом внутри;
  `env(safe-area-inset-bottom)` для iPhone с «чёлкой».
- Мобильные `.cookie-banner__actions`: `flex-wrap: nowrap`, столбик,
  кнопки на всю ширину — три ряда подписей больше не обрезаются.
- Модалка `.cookie-settings-modal`: на `≤575px` ограничена
  `max-height: calc(100vh - 24px)`, тело скроллится, футер — `column-reverse`
  с кнопками на всю ширину.
- `CookieConsentBanner.tsx`: высота баннера измеряется `ResizeObserver` и
  пишется в `--cookie-banner-h`; `body.has-cookie-banner` берёт отступ из
  этой переменной вместо хардкода.
- Политики `.policy-card`: текст 14px, таблица cookie-категорий скроллится
  локально (`scroll={{ x: 640 }}`), заголовки сохранены крупнее.

### Проверка

Проверка выполнена в DevTools (responsive-режим) на iPhone SE, Galaxy S20 и
iPhone 14 Pro Max: сверялись размер баннера, укладка кнопок, модалка,
localStorage и страницы политик. Прогон на старой сборке воспроизводит
дефекты, на новой — проходит:

```
before: iphone-se: баннер занимает 70% экрана
before: iphone-se/galaxy-s20/iphone-14-pro-max: кнопку сохранения модалки перекрывает другой элемент
after:  OK
```

| Устройство | Высота баннера до | после |
|---|---|---|
| iPhone SE 375×667 | 70% | 35% |
| Galaxy S20 360×800 | — | 29% |
| iPhone 14 Pro Max 430×932 | — | 25% |
| iPad 820×1180 | — | 10% |
| Desktop 1440×900 | — | 9% |

Дополнительно: ни на одной странице нет горизонтальной прокрутки, отступ
`body` совпадает с высотой баннера на всех проверенных маршрутах, модалка и
её футер целиком в пределах экрана, контраст кнопок 13.9 (dark) и 16.8
(light). Полный прогон backend-тестов — 200 passed.

Скриншоты: `docs/images/mobile/cookie-{before,after}-*`,
`policy-after-*`. Зеркало документации синхронизировано
(`python scripts/sync_public_docs.py`).

## Синхронизация репозиториев (27.09)

Работа идёт в двух зеркалах: `github.com/Pavel1778/rtk-crm` — основное,
`git.sourcecraft.dev/lct-hackaton-2026/case-16-edtech-crm-team-54` — зеркало,
с которого рабочая ВМ на Yandex Cloud тянет код для демо-стенда.

Рабочий прототип: **https://crm-rtk.pixel-minds.ru** (домен, HTTPS,
Let's Encrypt).

Состояние на момент отчёта:

| Площадка | Ветка | Примечание |
|---|---|---|
| GitHub | `main` | источник, сюда попадают все коммиты |
| SourceCraft | `main` | зеркало, с него ВМ тянет код для демо-стенда |

Порядок синхронизации — GitHub → SourceCraft: сначала коммит уходит в
основное зеркало, затем та же история переносится в SourceCraft и оттуда
подтягивается на ВМ. Токен SourceCraft в репозиторий и в `.git/config` не
пишется: используется `GIT_ASKPASS` или credential helper, чтобы секрет не
осел в рабочей копии.

## Обезличивание данных кейсодержателя

Кейсодержатель передал три выгрузки: `Вендоры.xlsx` (каталог ИТ-продуктов и
вендоров), `Данные оплат.json` (заявки B2C) и `Загрузка пользователей.xlsx`
(анкета физлица). В анкете есть поля персональных данных: СНИЛС, серия и
номер паспорта, кем и когда выдан, код подразделения, адрес регистрации и
индекс.

Перед добавлением в репозиторий анкета была **специально обезличена**: все
ПДн-поля заменены на сгенерированные заглушки (`000-000-000 00`,
`0000 000000`, `ОТДЕЛОМ УФМС РОССИИ`, `01.01.2020`, `000-000`,
`г. Москва, ул. Примерная, д. 1, кв. 1`, `000000`). ФИО, телефон и email
оставлены тестовыми. Пересборка — `scripts/anonymize_case_data.py`. Оригинал
хранится вне репозитория. Это соответствует требованиям 152-ФЗ и политике
безопасности проекта (см. `docs/SECURITY.md`, `docs/examples/README.md`).

Обезличенные образцы лежат в `docs/examples/` вместе с зеркалом в
`frontend/public/docs/examples/`: `vendors.xlsx`, `payments_b2c.json`,
`users_b2c.xlsx`. Именование латиницей — чтобы файлы не ломались на
Linux-стенде и в URL вкладки «Помощь».

Проверено: `git log --all --full-history -- "*Загрузка*"` — пусто, реальные
ПДн в истории отсутствуют.


### Что входит в сдачу

- `docs/qa-jury.md` — 40 вопросов (20 продуктовых и 20 технических) с опорой
  на файлы кода, а не на пересказ ТЗ.
- `docs/architecture/functional.archimate`, `functional.pdf`, `functional.mmd` —
  функциональная модель (ТЗ 6.7): пользовательский путь из 5 шагов и сервисы,
  модель ArchiMate 3 и отрендеренная диаграмма.
- `docs/architecture/rtk-crm.archimate` — компонентная модель (ТЗ 6.7):
  контейнеры, внешние системы и целевое развёртывание.
- `docs/architecture/er.mmd`, `er-model.pdf`, `er.archimate` — ER-модель:
  Mermaid-исходник, отрендеренная диаграмма и модель ArchiMate 3 (32 элемента).
- `docs/rtk-crm-documentation.pdf` — единый PDF (67 страниц) со всеми
  разделами, включая ER и Q&A для жюри.
- `docs/presentation/RTK-CRM-LCT2026.pptx` — презентация, 11 слайдов.
- `docs/examples/` — образцы форматов от кейсодержателя для демонстрации
  импорта: `vendors.xlsx`, `payments_b2c.json`, `users_b2c.xlsx`
  (обезличен). Синхронизируются в зеркало.
- `frontend/public/docs/` — зеркало документации для вкладки «Помощь»
  (`scripts/sync_public_docs.py`, ссылки переписаны в абсолютные `/docs/...`).

### Осталось до сдачи

- **Деплой и проверка стенда `https://crm-rtk.pixel-minds.ru`** — Postgres, Redis/KeyDB, MinIO,
  Keycloak, backend, frontend, nginx.
- **MinIO на стенде.** В изолированной среде сборки образы MinIO не тянулись,
  поэтому прототип проверялся на S3-fallback с локальным `uploads/`. На ВМ
  MinIO поднимается (`pgsty/minio`) — нужно убедиться, что backend пишет
  вложения именно туда, а не на локальный диск.
- **Нагрузочный отчёт на целевом контуре.** Локальный прогон Locust дал 1613
  запросов за 60 секунд, 0 ошибок, aggregate p95 93 мс. Цифры на ВМ нужно
  перепроверить и обновить `tests/load/report.html`.

## Финальная проверка (27.09.2026)

Финальный проход перед сдачей: презентация приведена к требованиям
организаторов, проверены ссылки сдачи, документация и тесты.

### Презентация — блок ЛЦТ на позициях 7–11

Организаторы требуют сохранять слайды 7–11 в исходном дизайне шаблона.
Обязательный блок перенесён на позиции 7–11 и повторяет слайды 7–11
шаблона один в один: сетка, шрифты и цвета не менялись, заполнены только
плейсхолдеры. Слайды 1–6 (решение) оформлены свободно.

| Проверка | Результат |
|---|---|
| Позиции 7–11 против шаблона (`check_presentation_layout.py`) | сетка совпадает, 0 дефектов |
| Переполнение/наложения/кегль на 7–11 | 0 дефектов, минимум 14pt |
| Слайд состава команды | 5 карточек; при меньшем составе лишние удаляются |
| Домен на слайде демо | `https://crm-rtk.pixel-minds.ru` |
| PPTX | `docs/presentation/RTK-CRM-LCT2026.pptx`, 11 слайдов |
| PDF | `docs/presentation/RTK-CRM-LCT2026.pdf`, 11 страниц |
| Шрифт | Montserrat (Regular/Bold) подставлен при рендере, подмены нет |
| Метаданные PPTX/PDF | `author` — «Сабадаш Павел», без следов генератора |

### Четыре ссылки сдачи

| # | Ссылка | Результат |
|---|---|---|
| 1 | `github.com/Pavel1778/rtk-crm` | публичный: README, LICENSE (MIT), бейдж CI |
| 2 | `docs/presentation/RTK-CRM-LCT2026.pptx` + PDF | лежат в репозитории рядом |
| 3 | `crm-rtk.pixel-minds.ru` | открывается; демо-логины проверены |
| 4 | `docs/rtk-crm-documentation.pdf` | 67 страниц |

Проверено без сессии: `/help` — 200, `/docs/rtk-crm-documentation.pdf` — 200,
`/docs/USER_GUIDE.md` — 200, `/health` — 200. Три демо-логина отвечают 200 на
`POST /api/auth/login`: `admin@rtk.ru`, `manager@rtk.ru`, `kam@rtk.ru`.

### README закрыт по чек-листу

Проверено, что README содержит ссылку на прототип, таблицу демо-логинов,
команду `docker compose up -d --build` и Swagger UI. Добавлено то, чего не
хватало: ссылки на презентацию (PPTX + PDF) и раздел «Лицензия».

Отдельно пояснено расхождение по `/docs` на домене: путь `/docs` занят
статической документацией фронтенда (`frontend/public/docs/`), поэтому
браузер туда отдаёт SPA. Swagger UI доступен локально на
`http://localhost:8000/docs`.

### Тесты и линтеры

| Проверка | Результат |
|---|---|
| `pytest -q` | 207 passed |
| `ruff check backend/ tests/ scripts/ conftest.py` | clean |
| `mypy backend/` | clean (48 файлов) |
| `tsc --noEmit` (frontend) | clean |
| `vite build` (frontend) | собрано |
| `sync_public_docs.py` | зеркало не расходится |

## Актуализация: демо-данные B2B/B2C и дозаполнение сида (27.09)

Демо-контур кейсодержателя должен показывать не по одной карточке на этап, а
портфель из нескольких вузов с содержательными задачами. Заодно устранён
дефект дозаполнения: раньше `_seed_demo_interactions` выходила сразу при
непустой таблице взаимодействий, поэтому база, засеянная до появления
B2C-воронки, навсегда оставалась без B2C-карточек.

Что изменено:

- B2B-карточки задаются по именам (вуз, продукт, этап) вместо индексов;
  индексы падали при неполном справочнике и зависели от порядка создания.
- Сид досоздаёт недостающие карточки и задачи, а не пропускает весь набор
  целиком. Ключ карточки — пара (вуз, продукт): этап не входит в ключ, иначе
  перенос карточки на другую колонку приводил бы к дублю при рестарте.
- Состав демо: 10 активных B2B-карточек (по 2 на вуз — предел правила
  «не более 2 активных взаимодействий на вуз», занято 10 из 14 этапов) и
  5 B2C-заявок; 7 задач (4 открытых, 3 выполненных) и комментарий.

Проверка (локально, SQLite):

```
pytest -q                        -> 208 passed
ruff check backend/ tests/ ...   -> clean
mypy backend/                    -> clean
python scripts/seed.py (дважды)  -> b2b 10, b2c 5; дублей нет
```

## Актуализация: вёрстка KPI-плиток и номеров шагов (27.09)

Две правки после проверки интерфейса и рендера презентации:

- Отчёты, плитки KPI. В сетке было жёстко задано 4 колонки, а показателей
  пять: пятая плитка («Выполненных задач») оставалась одна во втором ряду и
  выглядела обрезанной. Сетка переведена на `auto-fit`: на 1440 и 1024 px все
  пять плиток в один ряд, на 768 — в два, на мобильном — в три.
- Презентация, слайд 10. Фирменный Montserrat шире шаблонного Arial, и в
  рамке шириной 0.24" номера шагов «02» и «03» переносились на две строки
  («0» и «2»). Числовые маркеры переведены в `wrap="none"` и их рамка
  расширена до 0.6"; номера «01», «02», «03» снова в одну строку.

Проверка:

```
pytest -q                              -> 208 passed
ruff / mypy                            -> clean
npm --prefix frontend run build        -> собрано, tsc без ошибок
scripts/check_presentation_layout.py   -> дефектов вёрстки 0
```

В `check_presentation_layout.py` добавлена регрессия: разбитый на две строки
номер шага у правого края слайда теперь считается дефектом вёрстки.
