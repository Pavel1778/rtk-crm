"""Сервис импорта каталогов из Excel (XLSX/XLS)."""
import io
from typing import Any, Dict, List, Optional, Tuple

import chardet
from openpyxl import load_workbook
from loguru import logger


def detect_encoding(file_content: bytes) -> str:
    """Определяет кодировку файла через chardet."""
    result = chardet.detect(file_content)
    encoding = result.get("encoding", "utf-8") or "utf-8"
    logger.info(f"Определена кодировка файла: {encoding}")
    return encoding


def parse_catalog_file(
    file_content: bytes, sheet_name: Optional[str] = None
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Парсит Excel файл и возвращает заголовки и строки.
    
    Args:
        file_content: Содержимое файла в байтах
        sheet_name: Имя листа (если None, берётся первый)
    
    Returns:
        (headers, rows) - кортеж из списка заголовков и списка словарей
    """
    try:
        encoding = detect_encoding(file_content)
        decoded_content = file_content.decode(encoding, errors="ignore")
        
        wb = load_workbook(filename=io.BytesIO(file_content))
        
        if sheet_name:
            if sheet_name not in wb.sheetnames:
                raise ValueError(f"Лист '{sheet_name}' не найден. Доступные: {wb.sheetnames}")
            ws = wb[sheet_name]
        else:
            ws = wb.active
        
        headers = []
        rows = []
        
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                headers = [str(cell).strip() if cell is not None else f"column_{j}" for j, cell in enumerate(row)]
            else:
                row_dict = {}
                for j, cell in enumerate(row):
                    if j < len(headers):
                        row_dict[headers[j]] = cell
                if any(v is not None for v in row_dict.values()):
                    rows.append(row_dict)
        
        logger.info(f"Успешно распарсено {len(rows)} строк с {len(headers)} колонками")
        return headers, rows
        
    except Exception as e:
        logger.error(f"Ошибка парсинга Excel файла: {e}")
        raise


def parse_rows_with_mapping(
    rows: List[Dict[str, Any]], mapping: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Преобразует строки согласно маппингу полей.
    
    Args:
        rows: Список словарей из файла
        mapping: Словарь маппинга {field_in_file: system_field}
    
    Returns:
        Список словарей с системными именами полей
    """
    result = []
    for row in rows:
        mapped_row = {}
        for file_field, system_field in mapping.items():
            if file_field in row:
                mapped_row[system_field] = row[file_field]
        result.append(mapped_row)
    return result
