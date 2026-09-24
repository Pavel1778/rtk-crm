"""Единый источник правды по колонкам отчёта.

Конфиг `config/report_columns.json` читают и фронтенд, и бэкенд, чтобы
набор колонок в интерфейсе и в выгрузках PDF/XLSX/XLS не расходился:
добавили колонку в конфиг — она появилась везде.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Конфиг колонок отчёта читается на импорте модуля, поэтому путь обязан
# существовать в любом окружении. В контейнере код лежит в /app (build
# context — backend/), и корневой config/ в образ не попадает: при деплое на
# Render (контекст backend/) приложение падало с FileNotFoundError на
# /config/report_columns.json. Поэтому канонический файл дублируется внутрь
# backend/config/ (см. scripts/sync_report_columns.py) и проверяется первым —
# он гарантированно есть и в образе, и в репозитории.
_CONFIG_NAME = "report_columns.json"


def config_candidates(module_file: str | Path) -> tuple[Path, ...]:
    """Пути-кандидаты к конфигу для конкретного расположения модуля.

    Порядок: копия внутри пакета (`backend/config/`), корневой `config/`
    репозитория, затем смонтированный `/config` в контейнере Compose.
    """
    module_path = Path(module_file).resolve()
    return (
        module_path.parents[1] / "config" / _CONFIG_NAME,
        module_path.parents[2] / "config" / _CONFIG_NAME,
        Path("/config") / _CONFIG_NAME,
    )


_CANDIDATES = config_candidates(__file__)


def _config_path() -> Path:
    override = os.environ.get("REPORT_COLUMNS_CONFIG")
    if override:
        return Path(override)
    for candidate in _CANDIDATES:
        if candidate.exists():
            return candidate
    return _CANDIDATES[0]


CONFIG_PATH = _config_path()


@dataclass(frozen=True)
class ReportColumn:
    """Описание одной колонки отчёта."""

    key: str
    label: str
    short_label: str
    width: int
    align: str


@lru_cache(maxsize=1)
def load_report_columns() -> tuple[ReportColumn, ...]:
    """Читает и кэширует конфиг колонок."""
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return tuple(
        ReportColumn(
            key=item["key"],
            label=item["label"],
            short_label=item.get("short_label", item["label"]),
            width=int(item.get("width", 20)),
            align=item.get("align", "left"),
        )
        for item in payload["columns"]
    )


def column_keys() -> tuple[str, ...]:
    """Ключи колонок в порядке отображения."""
    return tuple(column.key for column in load_report_columns())


def column_labels() -> tuple[str, ...]:
    """Полные заголовки для выгрузок (XLSX/XLS)."""
    return tuple(column.label for column in load_report_columns())


def column_short_labels() -> tuple[str, ...]:
    """Короткие заголовки для узкой шапки PDF."""
    return tuple(column.short_label for column in load_report_columns())


def row_values(interaction: dict, placeholder: str = "—") -> list[str]:
    """Значения колонок для одной записи в порядке отображения."""
    return [
        str(interaction.get(column.key) or placeholder)
        for column in load_report_columns()
    ]
