"""Собирает сопроводительную документацию в единый PDF.

Запуск из корня репозитория:

    python scripts/build_docs_pdf.py

Документ собирается из Markdown-исходников `docs/` через pandoc с движком
xelatex: он тянет кириллицу и DejaVu, тогда как обычный pdflatex её не
знает. Результат — `docs/rtk-crm-documentation.pdf` и его копия в зеркале
`frontend/public/docs/` (оттуда файл отдаётся вкладкой «Помощь»).

Порядок разделов фиксирован скриптом, потому что содержание зависит от
задачи (ТЗ п. 10.4): титул → оглавление → аннотация → архитектура → стек →
функционал по ТЗ → методы обработки данных → ограничения → сборка →
безопасность → сценарии → глоссарий → приложения.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import ROOT  # noqa: E402

DOCS = ROOT / "docs"
TARGET = DOCS / "rtk-crm-documentation.pdf"
MIRROR = ROOT / "frontend" / "public" / "docs" / "rtk-crm-documentation.pdf"

PANDOC = "pandoc"

# Разделы документа: пары «заголовок раздела → файл от корня docs/».
# Пустые файлы пропускаются с предупреждением, чтобы сборка не падала на
# непринципиальном пропуске.
SECTIONS: list[tuple[str, str]] = [
    ("Архитектура системы", "architecture/ARCHITECTURE.md"),
    ("Технологический стек", "STACK.md"),
    ("Аутентификация и авторизация", "KEYCLOAK.md"),
    ("Сводка по взаимодействию (GigaChat)", "AI.md"),
    ("Безопасность и защита данных", "SECURITY.md"),
    ("Развёртывание", "DEPLOYMENT.md"),
    ("Отчёт о верификации", "VERIFICATION_REPORT.md"),
    ("Коды ошибок", "ERROR_CODES.md"),
    ("Руководство пользователя", "USER_GUIDE.md"),
    ("Руководство администратора", "ADMIN_GUIDE.md"),
    ("Вопросы жюри и ответы", "qa-jury.md"),
]

FRONT_MATTER = """\
---
title: "RTK CRM — Сопроводительная документация"
subtitle: "Кейс №6, Лидеры цифровой трансформации 2026"
author: "Команда RTK CRM"
lang: ru-RU
---

# Аннотация

RTK CRM — система контроля взаимодействия ИТ Школы Ростелекома с
вузами-партнёрами. Система переводит разрозненные коммуникации в единый
процесс с фиксированными этапами, ответственными и историей изменений.

Документ описывает архитектуру, функциональность, модель данных, методы
обработки данных, ограничения прототипа и порядок развёртывания. Все
требования технического задания сведены в таблицу ниже с отметкой о
реализации.

## Состав репозитория

| Артефакт | Назначение |
| --- | --- |
| `backend/` | FastAPI-сервис: API, бизнес-логика, экспорты |
| `frontend/` | SPA на React + TypeScript |
| `infra/` | Контур развёртывания Yandex Cloud |
| `docs/` | Документация, диаграммы, презентация |
| `scripts/` | Утилиты: seed, сиды, скриншоты, сборка PDF |
| `tests/` | Набор автотестов backend |
| `render.yaml` | Blueprint развёртывания Render + Vercel + Supabase |
"""

FUNCTIONAL_MATRIX = """\
# Функционал по техническому заданию

Таблица отмечает реализацию каждого пункта ТЗ. Отметка «Реализовано»
означает, что функциональность доступна в текущей сборке и покрыта тестами
(`pytest`, 200 тестов) либо подтверждена сквозной проверкой.

## Функциональные требования

| Требование | Реализация | Где в системе |
| --- | --- | --- |
| ФТ-1. Kanban-доска взаимодействий | Реализовано | Раздел «Доска», перемещение карточек `@dnd-kit` |
| ФТ-2. Карточка взаимодействия | Реализовано | Drawer с задачами, комментариями, договором |
| ФТ-3. Настройка этапов воркфлоу | Реализовано | «Настройки» → «Этапы воркфлоу» |
| ФТ-4. Справочники вузов, продуктов, направлений | Реализовано | Раздел «Справочники» |
| ФТ-5. Интеграция с LMS и CMS заказчика | Реализовано (mock-адаптер) | Вкладка «Интеграция» |
| ФТ-6. ИИ-сводка по взаимодействию | Реализовано | GigaChat, кнопка в карточке |
| ФТ-7. Отчёты и показатели | Реализовано | Раздел «Отчёты» |
| ФТ-8. Экспорт отчётов (XLSX, PDF, PNG, JSON) | Реализовано | Кнопки экспорта на «Отчётах» |
| ФТ-9. Импорт справочников из XLSX | Реализовано | «Справочники» → «Импорт» |
| ФТ-10. Авторизация через Keycloak | Реализовано | Кнопка «Войти через Keycloak» + PKCE |
| ФТ-11. Ролевая модель (RBAC) | Реализовано | Роли admin / manager / kam |
| ФТ-12. Задачи со сроками | Реализовано | Вкладка задач в карточке |
| ФТ-13. Файлы и вложения | Реализовано | S3-совместимое хранилище (MinIO / Object Storage) |

## Нефункциональные требования

| Требование | Реализация | Подтверждение |
| --- | --- | --- |
| НФТ-1. Производительность | Реализовано | Нагрузочный прогон Locust: 50 пользователей / 60 с, 1613 запросов, 0 ошибок, p95 93 мс (`docs/VERIFICATION_REPORT.md`) |
| НФТ-2. Производительность отчётов | Реализовано | Кэш агрегатов в Redis/KeyDB (`backend/services/cache.py`) |
| НФТ-3. Стабильные коды ошибок | Реализовано | `docs/ERROR_CODES.md` |
| НФТ-4. Адаптивность интерфейса | Реализовано | Мобильный вид Kanban, одна колонка |
| НФТ-5. Выгрузка документации в PDF | Реализовано | `scripts/build_docs_pdf.py`, кнопки в `/help` |
| НФТ-6. Безопасность и 152-ФЗ | Реализовано | `docs/SECURITY.md`, аудит, RBAC |
| НФТ-7. Наблюдаемость | Реализовано | `/healthz`, `/readyz`, Prometheus-метрики |
"""

DATA_METHODS = """\
# Методы обработки данных

- **Хранение.** PostgreSQL 16 (или SQLite для локального запуска). Доступ
  через SQLAlchemy 2.0 в асинхронном режиме.
- **Импорт XLSX.** Разбор `openpyxl` с диалоговым сопоставлением колонок:
  пользователь видит предпросмотр и подтверждает маппинг до записи.
  Импорт справочников идемпотентен по натуральному ключу.
- **Обмен с LMS/CMS.** Пакеты JSON проходят валидацию схемой
  (`jsonschema`) в режиме dry-run. Импорт идемпотентен по
  `contract_number`: повтор пакета обновляет запись, а не создаёт дубль.
- **Экспорт.** XLSX (`openpyxl`), PDF и PNG (`reportlab`), JSON. Экспорты
  выгружаются с учётом прав: КАМ видит только свои вузы.
- **Аудит.** Каждое изменяющее действие пишется в журнал (`ActionLog`) с
  автором, сущностью и временем; журнал доступен администратору.
- **Кэширование.** Агрегаты отчётов кэшируются в Redis/KeyDB с
  инвалидацией при изменении взаимодействий.
"""

LIMITATIONS = """\
# Ограничения прототипа

- **LMS и CMS — mock-адаптеры.** Внешние системы не подключены: адаптеры
  возвращают детерминированные данные по контракту обмена. Замена на
  реальные API выполняется реализацией того же интерфейса.
- **GigaChat.** Без ключа функция выключена: API отвечает `503`, а при
  включённом демо-режиме (`GIGACHAT_FALLBACK_ENABLED=true`) возвращается
  локальная сводка с явной пометкой, что модель не вызывалась.
- **Ограничение бизнес-модели.** У одного вуза не более двух активных
  взаимодействий; проверка выполняется на backend.
- **Файлы.** В прототипе хранилище — MinIO или Yandex Object Storage;
  virus-скан не подключён.
"""

BUILD_SECTION = """\
# Сборка и запуск

```bash
# Backend
pip install -r backend/requirements.txt
python scripts/run_dev.py --port 8000

# Frontend
cd frontend && npm ci && npm run dev

# Тесты
python -m pytest -q
ruff check backend tests
```

Полный контур через Docker Compose описан в `README.md`. Развёртывание на
Yandex Cloud и на Render + Vercel + Supabase — в разделе «Развёртывание».
"""

SCENARIOS = """\
# Сценарии работы

## КАМ

1. Вход, доска с карточками своих вузов.
2. Открытие карточки, постановка задачи со сроком, комментарий.
3. Перемещение карточки по этапам.
4. Запрос ИИ-сводки по взаимодействию.
5. Отчёт по своим вузам и экспорт в XLSX/PDF.

## Администратор

1. Управление пользователями и ролями.
2. Настройка этапов воркфлоу: порядок, цвет, включение.
3. Импорт справочников из XLSX с сопоставлением колонок.
4. Просмотр журнала аудита.
5. Настройка интеграции с LMS/CMS: предпросмотр и импорт пакета.
"""

GLOSSARY = """\
# Глоссарий

| Термин | Определение |
| --- | --- |
| Взаимодействие | Связка «вуз + ИТ-продукт», основная сущность системы |
| Этап | Стадия воронки, по которой перемещается взаимодействие |
| КАМ | Клиентский менеджер, ответственный за взаимодействие |
| Вуз | Университет-партнёр ИТ Школы |
| Контракт обмена | Схема JSON-пакета для интеграции с LMS/CMS |
| Идемпотентный импорт | Повторный импорт не создаёт дублей |
| Dry-run | Проверка пакета без записи в базу |
| RBAC | Ролевое разграничение доступа |
| PKCE | Расширение Authorization Code Flow для публичных клиентов |
"""


def _strip_md_links(text: str) -> str:
    """Убирает внутренние Markdown-ссылки, оставляя текст.

    В едином PDF локальные ссылки ведут на файл или якорь, которых в
    документе нет как отдельных ресурсов: pandoc делает из них гиперссылку
    на несуществующий якорь и печатает предупреждение. Текст ссылки при
    этом полезен, поэтому ссылку разворачиваем в него. Внешние (`http`)
    ссылки сохраняем.
    """
    without_files = re.sub(
        r"\[([^\]]+)\]\((?!https?:)[^)]*\.md(?:#[^)]*)?\)", r"\1", text
    )
    return re.sub(r"\[([^\]]+)\]\((?!https?:)#[^)]*\)", r"\1", without_files)


def _read_section(path: Path) -> str | None:
    if not path.exists():
        print(f"  пропуск: нет файла {path.relative_to(ROOT)}")
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        print(f"  пропуск: пустой файл {path.relative_to(ROOT)}")
        return None
    return text


def assemble(version: str) -> str:
    """Собирает единый Markdown. Разделы нумеруются сквозной нумерацией
    pandoc, поэтому собственные заголовки файлов понижаются на уровень:
    иначе каждый документ начинался бы новым разделом первого уровня."""
    parts: list[str] = [FRONT_MATTER]
    parts.append(FUNCTIONAL_MATRIX)
    parts.append(DATA_METHODS)
    parts.append(LIMITATIONS)
    parts.append(BUILD_SECTION)

    for title, relative in SECTIONS:
        body = _read_section(DOCS / relative)
        if body is None:
            continue
        # Убираем YAML-заголовок включённого файла и понижаем заголовки.
        if body.startswith("---"):
            end = body.find("\n---", 3)
            if end != -1:
                body = body[end + 4 :].strip()
        body = "\n".join(
            f"#{line}" if line.startswith("#") else line
            for line in _strip_md_links(body).splitlines()
        )
        parts.append(f"# {title}\n\n{body}")

    parts.append(SCENARIOS)
    parts.append(GLOSSARY)
    parts.append(
        f"""\
# Приложения

## Скриншоты интерфейса

Актуальные снимки экранов (светлая и тёмная темы, десктоп и мобильный)
лежат в `docs/images/` и зеркалируются в `frontend/public/docs/images/`:
вход, доска, карточка, фильтры, справочники, импорт, отчёты, конструктор
воркфлоу, пользователи, журнал, интеграция, помощь.

## Примеры отчётов

Образцы выгрузок: `docs/examples/report-b2b-2026-09-24.pdf`,
`docs/examples/report-longnames-2026-09-24.pdf`.

## Диаграммы

Исходники ArchiMate (компонентная, функциональная, ER) — в
`docs/architecture/`; C4-схемы — там же в Markdown.

---

Дата сборки: {date.today().isoformat()}. Версия документа: {version}.
"""
    )
    return "\n\n".join(parts) + "\n"


def build(version: str) -> int:
    if shutil.which(PANDOC) is None:
        print("pandoc не найден: установите pandoc и движок texlive-xetex")
        return 1

    document = assemble(version)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "documentation.md"
        source.write_text(document, encoding="utf-8")
        # pandoc разрешает пути картинок относительно входного файла,
        # поэтому ресурсы указываем явно на корень docs/.
        command = [
            PANDOC,
            str(source),
            "-o",
            str(TARGET),
            "--toc",
            "--toc-depth=2",
            "--number-sections",
            "--pdf-engine=xelatex",
            "-V",
            "mainfont=DejaVu Sans",
            "-V",
            "sansfont=DejaVu Sans",
            "-V",
            "monofont=DejaVu Sans Mono",
            "-V",
            "geometry:margin=2cm",
            "--resource-path",
            str(DOCS),
            "--metadata",
            "title=RTK CRM — Сопроводительная документация",
            "--metadata",
            "author=Команда RTK CRM",
            "--metadata",
            "lang=ru-RU",
        ]
        print("pandoc: сборка PDF…")
        result = subprocess.run(command, capture_output=True, text=True)
        errors = [
            line
            for line in result.stderr.splitlines()
            if "Missing character" not in line and line.strip()
        ]
        for line in errors[:20]:
            print("  ", line)
        if result.returncode != 0:
            print("Сборка PDF не удалась")
            return result.returncode

    MIRROR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TARGET, MIRROR)
    size_mb = TARGET.stat().st_size / 1024 / 1024
    print(f"Готово: {TARGET.relative_to(ROOT)} ({size_mb:.1f} МБ)")
    print(f"Зеркало: {MIRROR.relative_to(ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=date.today().isoformat())
    args = parser.parse_args()
    return build(args.version)


if __name__ == "__main__":
    raise SystemExit(main())
