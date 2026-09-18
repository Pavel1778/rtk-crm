from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class ReportFormat(str, Enum):
    XLSX = "xlsx"
    XLS = "xls"
    PDF = "pdf"
    JSON = "json"

class ReportFilters(BaseModel):
    start_date: Optional[date] = Field(None, description="Начало периода")
    end_date: Optional[date] = Field(None, description="Конец периода")
    product_ids: Optional[List[int]] = Field(None, description="ID продуктов")
    direction_ids: Optional[List[int]] = Field(None, description="ID направлений")
    kam_ids: Optional[List[int]] = Field(None, description="ID КАМов")
    university_ids: Optional[List[int]] = Field(None, description="ID ВУЗов")
    stage_ids: Optional[List[int]] = Field(None, description="ID этапов")
    format: ReportFormat = Field(ReportFormat.XLSX, description="Формат отчёта")

class ChartDataPoint(BaseModel):
    label: str
    value: int
    color: Optional[str] = None

class DashboardKPI(BaseModel):
    total_interactions: int = Field(..., description="Всего взаимодействий")
    active_interactions: int = Field(..., description="Активных взаимодействий")
    stale_interactions: int = Field(..., description="Просроченных (>14 дней)")
    completed_interactions: int = Field(..., description="Завершённых")
    total_universities: int = Field(..., description="Всего ВУЗов")
    total_kams: int = Field(..., description="Всего КАМов")

class DashboardResponse(BaseModel):
    kpi: DashboardKPI
    stage_distribution: List[ChartDataPoint]
    product_distribution: List[ChartDataPoint]
    dynamics_30_days: List[ChartDataPoint]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
