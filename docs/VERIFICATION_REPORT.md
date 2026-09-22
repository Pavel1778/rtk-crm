# Статическая верификация RTK CRM

Дата: 2026-09-22  
Ветка: `dev`  
Репозиторий: `github.com/Pavel1778/rtk-crm`

Проверка выполнена без запуска серверов, Docker Compose и браузерных
прогонов. Проверены исходный код, конфигурация, документация и генерация
экспортов в памяти.

## Итог

- `✅ OK` — 34 пункта;
- `⚠️ Warning` — 9 пунктов;
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
| In-memory экспорт | `✅ OK` | `scripts/test_export.py`; получены XLSX 5 KB, XLS 5 KB, PDF 47 KB; XLSX читается `openpyxl`, PDF имеет `%PDF` и DejaVu |

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
| Старые секреты в Git history | `⚠️ Warning` | Текущие файлы очищены, но ранее опубликованные credentials нельзя считать отозванными: их нужно немедленно ротировать в Supabase/Render |

## 5. Workflow, RBAC и cookie consent

| Проверка | Статус | Доказательство |
|---|---|---|
| Все этапы в конструкторе | `✅ OK` | `frontend/src/pages/WorkflowPage.tsx:22` использует `useStages('all')` |
| Только активные этапы в Kanban | `✅ OK` | `frontend/src/pages/BoardPage.tsx` и `useStages('active')` |
| Optimistic update/rollback | `✅ OK` | `frontend/src/hooks/useStages.ts:27-59` |
| 409 при активных взаимодействиях | `✅ OK` | `backend/api/stages.py:120-130` |
| Impact и перенос при удалении | `✅ OK` | `backend/api/stages.py:41-59,180-205`; `frontend/src/components/workflow/DeleteStageModal.tsx` |
| Disabled opacity 0.55 | `✅ OK` | `frontend/src/index.css:401-404` |
| Cookie schema и necessary locked | `✅ OK` | `frontend/src/lib/cookieConsent.ts:1-94`; banner/settings components |
| Privacy routes и footer links | `✅ OK` | `frontend/src/pages/CookiePolicyPage.tsx`, `PrivacyPolicyPage.tsx`, `frontend/src/components/AppFooter.tsx:21-24` |

## 6. Нефункциональные требования и документация

| Проверка | Статус | Доказательство / примечание |
|---|---|---|
| Production response target ≤1 s | `⚠️ Warning` | Предыдущий Locust: 50 пользователей, 1460 запросов, 0% ошибок, aggregate p95 1600 ms; API endpoints без login 37–480 ms. `tests/load/README.md:59-65` |
| 50 concurrent users | `✅ OK` | `tests/load/README.md:59-60` |
| 10 concurrent report requests | `⚠️ Warning` | Сценарий проверяет отчёты в общем профиле Locust, отдельный доказательный тест ровно на 10 report requests не зафиксирован |
| SPA и viewport | `✅ OK` | `frontend/index.html:5`; React Router и Vite build |
| Коды 400/401/403/404/409/422/500 | `✅ OK` | Проверены статически по FastAPI routes/handlers; `422` handler: `backend/main.py:74-89` |
| USER_GUIDE и ADMIN_GUIDE | `✅ OK` | Файлы присутствуют |
| SECURITY.md с 152-ФЗ и миграцией Yandex Cloud | `✅ OK` | `docs/SECURITY.md:1-34` |
| DEPLOYMENT.md Render/Vercel/Supabase/Yandex Cloud | `✅ OK` | `docs/DEPLOYMENT.md`; credentials заменены placeholders |
| ARCHITECTURE и C4 Mermaid | `✅ OK` | `docs/architecture/ARCHITECTURE.md`, `c4-context.md`, `c4-components.md` |
| Pitch 11 слайдов | `✅ OK` | `docs/pitch.md` |
| QA 20 вопросов/ответов | `✅ OK` | `docs/qa-jury.md` |
| Реальные screenshots в `docs/images/` | `⚠️ Warning` | Файлы отсутствуют. Браузерный прогон и создание фальшивых изображений запрещены текущим заданием; нужен отдельный разрешённый UI-pass |

## 7. Atomaro UI и качество кода

| Проверка | Статус | Доказательство / примечание |
|---|---|---|
| `--atmr-*` tokens и theme classes | `✅ OK` | `frontend/src/index.css:1-24`; light class в `MainLayout.tsx` |
| Радиусы/spacing/responsive grids | `✅ OK` | `frontend/src/index.css`; report layout |
| Mobile table/export/chart handling | `✅ OK` | responsive classes in `frontend/src/index.css`; responsive legend in `ReportPage.tsx` |
| Footer safe-area и max-content | `✅ OK` | `frontend/src/components/AppFooter.tsx:8-15` |
| Hardcoded colors | `⚠️ Warning` | Ключевые report colors переведены в tokens; в legacy UI остаются отдельные inline/CSS цвета, не влияющие на функциональность |
| TypeScript build | `✅ OK` | `source ~/.nvm/nvm.sh && npm run build`; build завершён, Vite сообщил только размер bundle >500 KB |
| Python compileall | `✅ OK` | `python3 -m compileall -q backend/... scripts tests/load` |
| `git diff --check` | `✅ OK` | Выполнено после финальных правок |
| print/TODO/console.log/`: any` scan | `✅ OK` | Статический `rg` scan не выявил совпадений в проверенных директориях |

## Осталось

1. Ротировать credentials, которые ранее попали в историю Git; удаление из текущего
   состояния не отзывает старые значения.
2. Отдельно провести разрешённый браузерный UI-pass и сохранить минимум 8 реальных
   screenshots в `docs/images/`.
3. Оптимизировать login/p95 и повторить Locust до aggregate p95 < 1000 ms.
4. При необходимости полностью перевести legacy hardcoded CSS colors в tokens.
5. При необходимости заменить JWT на Keycloak/добавить явно документированный
   `MOCK_MODE`, если это обязательное условие комиссии, а не альтернативный вариант.
