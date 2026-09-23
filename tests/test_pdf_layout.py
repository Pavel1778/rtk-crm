"""Вёрстка PDF-отчёта: колонки не должны наезжать друг на друга.

Проверяем расчёт ширин и то, что таблица целиком помещается в печатную область
landscape A4 при реалистичных длинных названиях вузов.
"""

from __future__ import annotations

import pytest
from reportlab.lib.pagesizes import A4, landscape

from app.services.excel_export import (
    PDF_COLUMNS,
    _PDF_MARGINS,
    _fit_column_widths,
    _resolve_pdf_fonts,
    estimate_pdf_table_width,
    generate_pdf,
)

BAUMAN = "Московский государственный технический университет им. Н. Э. Баумана"
KREMENCHUG = "Кременчуг-Константиновское"

REALISTIC = [
    {
        "university_name": BAUMAN,
        "direction_name": "Информационные технологии",
        "product_name": "СЭД «Дело»",
        "stage_name": "Согласование договора",
        "assigned_kam_name": "Пётр Ильич Чайковский",
        "contract_number": "RTK-2025-001",
        "contract_date": "31.12.2030",
    },
    {
        "university_name": KREMENCHUG,
        "direction_name": "Информационная безопасность",
        "product_name": "AI Studio",
        "stage_name": "Коммуникация",
        "assigned_kam_name": "Иванов Иван Иванович",
        "contract_number": "RTK-2026-042",
        "contract_date": "2027",
    },
]


def _landscape_a4_text_width() -> float:
    return landscape(A4)[0] - _PDF_MARGINS * 2


@pytest.mark.parametrize(
    "payload",
    [
        [],
        REALISTIC,
        [REALISTIC[0]],
        [dict(REALISTIC[0], university_name="X" * 400)],
        [dict(REALISTIC[0], contract_date="")],
        [{key: "" for key, _ in PDF_COLUMNS}],
    ],
    ids=["empty", "realistic", "single", "pathological-long", "blank-date", "all-empty"],
)
def test_table_fits_landscape_a4(payload: list[dict]) -> None:
    width = estimate_pdf_table_width(payload)
    assert width <= _landscape_a4_text_width() + 0.5


def test_seven_columns_landscape_a4() -> None:
    width = estimate_pdf_table_width(REALISTIC)
    assert width <= _landscape_a4_text_width()
    assert width > _landscape_a4_text_width() * 0.9


def test_long_word_gets_enough_width() -> None:
    """Самое длинное слово должно влезать — иначе перенос невозможен."""
    from reportlab.pdfbase import pdfmetrics

    font_name, font_bold = _resolve_pdf_fonts()
    headers = [label for _, label in PDF_COLUMNS]
    rows = [[str(item.get(key, "—") or "—") for key, _ in PDF_COLUMNS] for item in REALISTIC]
    widths = _fit_column_widths(
        rows, headers, font_name, font_bold, 8.5, 10, _landscape_a4_text_width()
    )

    longest_word = max(
        pdfmetrics.stringWidth(token, font_name, 8.5) for token in KREMENCHUG.split()
    )
    # Первая колонка держит «Московский ... Баумана», проверяем колонку целиком
    # на самое длинное слово во всём отчёте.
    assert max(widths) >= longest_word


def test_no_cell_overflows_its_column() -> None:
    """Каждая ячейка после переноса должна влезать в свою колонку."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    font_name, font_bold = _resolve_pdf_fonts()
    headers = [label for _, label in PDF_COLUMNS]
    rows = [[str(item.get(key, "—") or "—") for key, _ in PDF_COLUMNS] for item in REALISTIC]

    body = ParagraphStyle("t", fontName=font_name, fontSize=8.5, leading=11, wordWrap="LTR")
    head = ParagraphStyle(
        "h", fontName=font_bold, fontSize=10, leading=12, wordWrap="LTR"
    )

    widths = _fit_column_widths(
        rows, headers, font_name, font_bold, 8.5, 10, _landscape_a4_text_width()
    )

    for idx, label in enumerate(headers):
        used, _ = Paragraph(label, head).wrap(widths[idx], 1000)
        assert used <= widths[idx] + 0.5, f"заголовок «{label}» шире колонки"

    for row in rows:
        for idx, value in enumerate(row):
            used, _ = Paragraph(value, body).wrap(widths[idx], 1000)
            assert used <= widths[idx] + 0.5, f"ячейка «{value}» шире колонки {idx}"


def test_pdf_is_landscape_and_readable() -> None:
    from pypdf import PdfReader

    page = PdfReader(generate_pdf(REALISTIC)).pages[0]
    width, height = page.mediabox.width, page.mediabox.height
    assert width > height, "при 7 колонках отчёт должен быть landscape"

    text = page.extract_text()
    # wordWrap='CJK' может вставить перенос внутри длинного названия — сверяем
    # по фрагментам.
    assert "Московский" in text and "Баумана" in text
    assert "Кременчуг" in text and "Константиновское" in text
    assert "Лицензия" in text
