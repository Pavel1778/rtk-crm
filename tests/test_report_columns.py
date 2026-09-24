"""Тесты единого конфига колонок отчёта (config/report_columns.json).

Гарантия B.4: фронтенд, PDF и XLSX/XLS используют один и тот же список
колонок, поэтому состав выгрузки не может разойтись с интерфейсом.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
from app.services.report_columns import (
    column_keys,
    column_labels,
    column_short_labels,
    load_report_columns,
    row_values,
)

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "report_columns.json"

SAMPLE = {
    "university_name": "Московский государственный технический университет им. Н. Э. Баумана",
    "direction_name": "Искусственный интеллект",
    "product_name": "AI Studio",
    "stage_name": "Пилот завершён",
    "assigned_kam_name": "Иванов Иван Иванович",
    "contract_number": "RTK-2025-001",
    "contract_date": "2030",
}


def test_config_resolves_in_container_layout(tmp_path, monkeypatch) -> None:
    """При layout контейнера (/app + /config) конфиг находится через фолбэк.

    В образе код лежит в /app (build context — backend/), поэтому
    `parents[2]/config` указывает на `/config`, а не на корень репозитория.
    """
    import importlib

    from app.services import report_columns

    fake_config = tmp_path / "report_columns.json"
    fake_config.write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setenv("REPORT_COLUMNS_CONFIG", str(fake_config))
    reloaded = importlib.reload(report_columns)
    try:
        resolved = reloaded.CONFIG_PATH
        assert resolved == fake_config
        assert len(reloaded.load_report_columns()) > 0
    finally:
        monkeypatch.delenv("REPORT_COLUMNS_CONFIG", raising=False)
        importlib.reload(report_columns)


def test_error_when_config_missing(tmp_path, monkeypatch) -> None:
    """Отсутствие конфига даёт понятную ошибку, а не тихий пустой список."""
    import importlib

    from app.services import report_columns

    monkeypatch.setenv("REPORT_COLUMNS_CONFIG", str(tmp_path / "nope.json"))
    reloaded = importlib.reload(report_columns)
    try:
        with pytest.raises(FileNotFoundError):
            reloaded.load_report_columns()
    finally:
        monkeypatch.delenv("REPORT_COLUMNS_CONFIG", raising=False)
        importlib.reload(report_columns)


def test_config_is_valid_json_with_required_fields() -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert payload["columns"], "конфиг колонок не должен быть пустым"
    for column in payload["columns"]:
        assert column["key"] and column["label"]


def test_frontend_and_backend_read_same_file() -> None:
    """Ключи и заголовки берутся из того же файла, что читает фронтенд."""
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert list(column_keys()) == [column["key"] for column in payload["columns"]]
    assert list(column_labels()) == [column["label"] for column in payload["columns"]]


def test_pdf_columns_derive_from_shared_config() -> None:
    from app.services.excel_export import PDF_COLUMNS

    assert tuple(zip(column_keys(), column_short_labels(), strict=True)) == PDF_COLUMNS


def test_row_values_follows_config_order() -> None:
    values = row_values(SAMPLE)
    assert len(values) == len(column_keys())
    assert values[0] == SAMPLE["university_name"]
    assert values[-1] == SAMPLE["contract_date"]


def test_row_values_replaces_missing_with_placeholder() -> None:
    values = row_values({}, placeholder="—")
    assert values == ["—"] * len(column_keys())
    assert row_values({"university_name": ""})[0] == "—"


def test_xlsx_headers_match_shared_config() -> None:
    openpyxl = pytest.importorskip("openpyxl")
    from app.services.excel_export import generate_xlsx

    stream = generate_xlsx([SAMPLE])
    sheet = openpyxl.load_workbook(BytesIO(stream.getvalue())).active
    headers = [cell.value for cell in sheet[1]]

    assert headers == list(column_labels())


def test_xlsx_data_order_matches_shared_config() -> None:
    openpyxl = pytest.importorskip("openpyxl")
    from app.services.excel_export import generate_xlsx

    stream = generate_xlsx([SAMPLE])
    sheet = openpyxl.load_workbook(BytesIO(stream.getvalue())).active
    row = [cell.value for cell in sheet[2]]

    assert row == [SAMPLE[key] for key in column_keys()]


def test_xls_headers_match_shared_config() -> None:
    xlrd = pytest.importorskip("xlrd")
    from app.services.excel_export import generate_xls

    stream = generate_xls([SAMPLE])
    sheet = xlrd.open_workbook(file_contents=stream.getvalue()).sheet_by_index(0)
    headers = [sheet.cell_value(0, index) for index in range(sheet.ncols)]

    assert headers == list(column_labels())


def test_pdf_column_count_matches_shared_config() -> None:
    pytest.importorskip("reportlab")
    from app.services.excel_export import PDF_COLUMNS

    assert len(PDF_COLUMNS) == len(load_report_columns())
