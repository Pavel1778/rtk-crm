from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict
from datetime import datetime

class ImportMapping(BaseModel):
    """Маппинг колонок файла на поля системы"""
    file_column: str = Field(..., description="Название колонки в файле")
    system_field: str = Field(..., description="Поле системы")
    
class ImportPreview(BaseModel):
    """Превью импорта"""
    total_rows: int = Field(..., description="Всего строк в файле")
    valid_rows: int = Field(..., description="Валидных строк")
    invalid_rows: int = Field(..., description="Невалидных строк")
    mapping: Dict[str, str] = Field(..., description="Маппинг полей")
    sample_data: List[Dict[str, str]] = Field(..., description="Пример данных (первые 5 строк)")
    
class ImportErrorDetail(BaseModel):
    """Детали ошибки импорта"""
    row_number: int
    error_message: str
    row_data: Dict[str, str]

class ImportResult(BaseModel):
    """Результат импорта"""
    success: bool
    imported_count: int = Field(..., description="Количество импортированных записей")
    skipped_count: int = Field(..., description="Количество пропущенных записей")
    error_count: int = Field(..., description="Количество ошибок")
    errors: Optional[List[ImportErrorDetail]] = None
    
    model_config = ConfigDict(from_attributes=True)

class ImportExecuteRequest(BaseModel):
    """Запрос на выполнение импорта"""
    mapping: Dict[str, str] = Field(..., description="Маппинг полей")
    skip_existing: bool = Field(True, description="Пропускать существующие записи")
