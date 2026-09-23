"""Регрессия на кириллицу в экспортах XLS/XLSX/PDF.

Проверяем полный цикл «запись → чтение файла → сравнение строки», чтобы
поймать потерю кодировки при открытии в Excel/просмотрщике PDF.
"""

from __future__ import annotations

from io import BytesIO

import pytest

from app.services.excel_export import generate_pdf, generate_xls, generate_xlsx

# Строка с «проблемными» для кодировок символами: дефис, №, буква ё.
UNIVERSITY = "ВУЗ им. Ленина №5, г. Москва"
TOUGH_UNIVERSITY = "Кременчуг-Константиновское"


def _row(university: str) -> list[dict]:
    return [
        {
            "university_name": university,
            "direction_name": "Информационные технологии",
            "product_name": "СЭД «Дело»",
            "stage_name": "Коммуникация",
            "assigned_kam_name": "Пётр Ильич Чайковский",
            "contract_number": "№ 42/2026",
            "contract_date": "2026",
        }
    ]


def test_xlsx_roundtrip_keeps_cyrillic() -> None:
    from openpyxl import load_workbook

    output = generate_xlsx(_row(UNIVERSITY))
    sheet = load_workbook(output).active

    assert sheet.cell(row=2, column=1).value == UNIVERSITY
    assert sheet.cell(row=2, column=2).value == "Информационные технологии"
    assert sheet.cell(row=2, column=5).value == "Пётр Ильич Чайковский"


def test_xlsx_roundtrip_tough_name() -> None:
    from openpyxl import load_workbook

    output = generate_xlsx(_row(TOUGH_UNIVERSITY))
    sheet = load_workbook(output).active
    assert sheet.cell(row=2, column=1).value == TOUGH_UNIVERSITY


def test_xls_roundtrip_keeps_cyrillic() -> None:
    import xlrd

    output = generate_xls(_row(UNIVERSITY))
    sheet = xlrd.open_workbook(file_contents=output.read()).sheet_by_index(0)

    assert sheet.cell_value(1, 0) == UNIVERSITY
    assert sheet.cell_value(1, 1) == "Информационные технологии"
    assert sheet.cell_value(1, 4) == "Пётр Ильич Чайковский"


def test_xls_roundtrip_tough_name() -> None:
    import xlrd

    output = generate_xls(_row(TOUGH_UNIVERSITY))
    sheet = xlrd.open_workbook(file_contents=output.read()).sheet_by_index(0)
    assert sheet.cell_value(1, 0) == TOUGH_UNIVERSITY


def test_pdf_roundtrip_keeps_cyrillic() -> None:
    """Извлекаем текст из PDF: кириллица должна читаться, а не теряться."""
    from pypdf import PdfReader

    output = generate_pdf(_row(UNIVERSITY))
    text = "\n".join(page.extract_text() for page in PdfReader(output).pages)

    assert UNIVERSITY in text
    assert "Информационные технологии" in text
    assert "Пётр Ильич Чайковский" in text


def test_pdf_roundtrip_tough_name() -> None:
    from pypdf import PdfReader

    output = generate_pdf(_row(TOUGH_UNIVERSITY))
    text = "\n".join(page.extract_text() for page in PdfReader(output).pages)
    assert TOUGH_UNIVERSITY in text
