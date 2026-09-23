"""Экспорт отчётов в XLSX, XLS и PDF форматы."""

from io import BytesIO
from datetime import datetime

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    from xlwt import Workbook as XlsWorkbook, easyxf
    XLWT_AVAILABLE = True
except ImportError:
    XLWT_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from app.services.report_columns import (
    column_keys,
    column_labels,
    load_report_columns,
)


# Колонки отчёта: ключ в данных + короткий заголовок для узкой шапки.
# Определяются в config/report_columns.json — общем конфиге фронта и бэкенда.
PDF_COLUMNS: tuple[tuple[str, str], ...] = tuple(
    (column.key, column.short_label) for column in load_report_columns()
)


def _resolve_pdf_fonts() -> tuple[str, str]:
    """Регистрирует DejaVu Sans и возвращает (regular, bold).

    DejaVu покрывает кириллицу; встроенные в reportlab Helvetica её не знают.
    """
    import os

    regular_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if not os.path.exists(regular_path):
        return "Helvetica", "Helvetica-Bold"

    if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DejaVu", regular_path))
    bold = "DejaVu"
    if os.path.exists(bold_path):
        if "DejaVu-Bold" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold_path))
        bold = "DejaVu-Bold"
    return "DejaVu", bold


def _fit_column_widths(
    rows: list[list[str]],
    headers: list[str],
    font_name: str,
    font_bold: str,
    body_size: float,
    head_size: float,
    available: float,
    padding: float = 12,
) -> list[float]:
    """Считает ширины колонок от содержимого так, чтобы таблица влезла в страницу.

    Минимум по колонке — самое длинное слово (без него текст не переносится),
    желаемая ширина — самая длинная ячейка/заголовок целиком. Свободное место
    раздаётся колонкам, которым не хватает до желаемой ширины.
    """
    min_widths: list[float] = []
    desired_widths: list[float] = []
    for idx, header in enumerate(headers):
        longest_word = pdfmetrics.stringWidth(header, font_bold, head_size)
        longest_cell = longest_word
        for row in rows:
            value = str(row[idx]) if idx < len(row) else ""
            longest_cell = max(longest_cell, pdfmetrics.stringWidth(value, font_name, body_size))
            for token in value.split():
                longest_word = max(
                    longest_word, pdfmetrics.stringWidth(token, font_name, body_size)
                )
        min_widths.append(longest_word + padding)
        desired_widths.append(max(longest_cell, longest_word) + padding)

    cap = available * 0.30  # ни одна колонка не забирает всю страницу
    desired_widths = [min(w, cap) for w in desired_widths]
    min_widths = [min(a, b) for a, b in zip(min_widths, desired_widths)]

    total_min = sum(min_widths)
    if total_min > available:  # экзотические данные: ужимаем пропорционально
        scale = available / total_min
        return [w * scale for w in min_widths]

    widths = list(min_widths)
    remaining = available - total_min
    deficits = [d - m for d, m in zip(desired_widths, min_widths)]
    total_deficit = sum(deficits)
    if total_deficit > 0:
        for i, deficit in enumerate(deficits):
            widths[i] += remaining * (deficit / total_deficit)
    elif remaining > 0:
        # Всем хватило: размазываем остаток поровну.
        even = remaining / len(widths)
        widths = [w + even for w in widths]
    return widths


def estimate_pdf_table_width(interactions: list[dict]) -> float:
    """Оценка итоговой ширины таблицы PDF — для тестов и проверок вёрстки."""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab не установлен. Установите: pip install reportlab")

    font_name, font_bold = _resolve_pdf_fonts()
    headers = [label for _, label in PDF_COLUMNS]
    rows = [[str(item.get(key, "—") or "—") for key, _ in PDF_COLUMNS] for item in interactions]
    page = A4 if len(PDF_COLUMNS) <= 5 else landscape(A4)
    margins = _PDF_MARGINS
    available = page[0] - margins * 2
    widths = _fit_column_widths(
        rows, headers, font_name, font_bold, _PDF_BODY_FONT_SIZE, _PDF_HEAD_FONT_SIZE, available
    )
    return sum(widths)


_PDF_MARGINS = 28
_PDF_BODY_FONT_SIZE = 8.5
_PDF_HEAD_FONT_SIZE = 10


def generate_pdf(interactions: list[dict]) -> BytesIO:
    """Генерация PDF отчёта по взаимодействиям."""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab не установлен. Установите: pip install reportlab")

    font_name, font_bold = _resolve_pdf_fonts()

    headers = [label for _, label in PDF_COLUMNS]
    rows = [
        [str(item.get(key, "—") or "—") for key, _ in PDF_COLUMNS] for item in interactions
    ]

    # 7 колонок в портрет A4 не влезают — переходим на landscape.
    page_size = A4 if len(PDF_COLUMNS) <= 5 else landscape(A4)
    available = page_size[0] - _PDF_MARGINS * 2
    col_widths = _fit_column_widths(
        rows,
        headers,
        font_name,
        font_bold,
        _PDF_BODY_FONT_SIZE,
        _PDF_HEAD_FONT_SIZE,
        available,
    )

    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=page_size,
        rightMargin=_PDF_MARGINS,
        leftMargin=_PDF_MARGINS,
        topMargin=_PDF_MARGINS,
        bottomMargin=_PDF_MARGINS,
        title="Отчёт по взаимодействиям с ВУЗами",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "RtkTitle",
        parent=styles["Title"],
        alignment=1,
        fontName=font_bold,
        fontSize=16,
        textColor=colors.HexColor("#6E41F2"),
    )
    meta_style = ParagraphStyle(
        "RtkMeta",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        textColor=colors.HexColor("#6B6B72"),
    )
    # Обычный перенос по словам: минимальная ширина колонки уже >= самого
    # длинного слова, поэтому слова не разрезаются, а длинные значения
    # переносятся на следующую строку.
    head_cell_style = ParagraphStyle(
        "RtkHeadCell",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=_PDF_HEAD_FONT_SIZE,
        leading=_PDF_HEAD_FONT_SIZE + 2,
        textColor=colors.whitesmoke,
        wordWrap="LTR",
    )
    body_cell_style = ParagraphStyle(
        "RtkBodyCell",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=_PDF_BODY_FONT_SIZE,
        leading=_PDF_BODY_FONT_SIZE + 2.5,
        wordWrap="LTR",
    )

    data = [[Paragraph(label, head_cell_style) for label in headers]]
    data += [
        [Paragraph(value, body_cell_style) for value in row] for row in rows
    ]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6E41F2")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5FC")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E5")),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#5A31D9")),
            ]
        )
    )

    title = Paragraph("Отчёт по взаимодействиям с ВУЗами", title_style)
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    meta_text = Paragraph(
        f"Сформирован: {date_str} | Всего записей: {len(interactions)}",
        meta_style,
    )
    # Разделитель. Используем meta_style, иначе Paragraph берёт Normal
    # с Helvetica и в PDF попадает шрифт без кириллицы.
    spacer = Paragraph("<br/><br/>", meta_style)

    doc.build([title, meta_text, spacer, table])

    output.seek(0)
    return output


def generate_xlsx(interactions: list[dict]) -> BytesIO:
    """Генерация XLSX отчёта по взаимодействиям."""
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl не установлен. Установите: pip install openpyxl")

    wb = Workbook()
    ws = wb.active
    ws.title = "Отчёт по взаимодействиям"

    # Заголовки из общего конфига config/report_columns.json
    headers = list(column_labels())

    # Стиль заголовков
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="6E41F2", end_color="6E41F2", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Запись заголовков
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # Запись данных
    keys = column_keys()
    for row_num, interaction in enumerate(interactions, 2):
        for col_num, key in enumerate(keys, 1):
            ws.cell(row=row_num, column=col_num, value=interaction.get(key, ""))

        # Применение границ к ячейкам данных
        for col_num in range(1, len(keys) + 1):
            cell = ws.cell(row=row_num, column=col_num)
            cell.border = thin_border

    # Строка итогов
    total_row = len(interactions) + 2
    total_cell = ws.cell(row=total_row, column=1, value=f"Всего записей: {len(interactions)}")
    total_cell.font = Font(bold=True, size=11)
    last_letter = ws.cell(row=1, column=len(keys)).column_letter
    ws.merge_cells(f"A{total_row}:{last_letter}{total_row}")

    # Автоподбор ширины колонок
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width

    # Сохранение в BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def generate_xls(interactions: list[dict]) -> BytesIO:
    """Генерация XLS отчёта по взаимодействиям."""
    if not XLWT_AVAILABLE:
        raise ImportError("xlwt не установлен. Установите: pip install xlwt")

    wb = XlsWorkbook(encoding='utf-8')
    ws = wb.add_sheet("Отчёт по взаимодействиям")

    # Заголовки из общего конфига config/report_columns.json
    headers = list(column_labels())

    # Стиль заголовков
    header_style = easyxf(
        'font: bold on, color white, height 220; align: horiz center, vert centre; '
        'pattern: pattern solid, fore_colour dark_purple'
    )

    # Запись заголовков
    for col_num, header in enumerate(headers):
        ws.write(0, col_num, header, header_style)

    # Запись данных
    keys = column_keys()
    for row_num, interaction in enumerate(interactions, 1):
        for col_num, key in enumerate(keys):
            ws.write(row_num, col_num, interaction.get(key, ""))

    # Строка итогов
    total_row = len(interactions) + 1
    ws.write(total_row, 0, f"Всего записей: {len(interactions)}", easyxf('font: bold on'))

    # Сохранение в BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

