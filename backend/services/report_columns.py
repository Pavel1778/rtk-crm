"""Единый источник правды по колонкам отчёта.

Конфиг `config/report_columns.json` читают и фронтенд, и бэкенд, чтобы
набор колонок в интерфейсе и в выгрузках PDF/XLSX/XLS не расходился:
добавили колонку в конфиг — она появилась везде.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "report_columns.json"


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
