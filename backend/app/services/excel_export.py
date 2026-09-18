"""Сервис экспорта данных в Excel (XLSX и XLS)."""
from typing import Any, Dict, List

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import xlwt


def generate_xlsx(data: List[Dict[str, Any]], filename: str = "export.xlsx") -> bytes:
    """
    Генерирует Excel файл формата XLSX.
    
    Args:
        data: Список словарей с данными
        filename: Имя файла (используется для заголовка)
    
    Returns:
        Байты Excel файла
    """
    if not data:
        wb = Workbook()
        ws = wb.active
        ws.title = "Данные"
        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()
    
    headers = list(data[0].keys())
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Данные"
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = cell.font.copy(bold=True)
    
    for row_num, row_data in enumerate(data, 2):
        for col_num, header in enumerate(headers, 1):
            value = row_data.get(header, "")
            ws.cell(row=row_num, column=col_num, value=value)
    
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width
    
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generate_xls(data: List[Dict[str, Any]], filename: str = "export.xls") -> bytes:
    """
    Генерирует Excel файл формата XLS (старый формат).
    
    Args:
        data: Список словарей с данными
        filename: Имя файла
    
    Returns:
        Байты Excel файла
    """
    if not data:
        wb = xlwt.Workbook()
        ws = wb.add_sheet("Данные")
        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()
    
    headers = list(data[0].keys())
    
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Данные")
    
    style_header = xlwt.XFStyle()
    font_header = xlwt.Font()
    font_header.bold = True
    style_header.font = font_header
    
    for col_num, header in enumerate(headers):
        ws.write(0, col_num, header, style_header)
    
    for row_num, row_data in enumerate(data, 1):
        for col_num, header in enumerate(headers):
            value = row_data.get(header, "")
            ws.write(row_num, col_num, value)
    
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


import io
