from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class WorkflowStageBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=300, description="Название этапа")
    description: Optional[str] = Field(None, max_length=2000, description="Описание этапа")
    order: int = Field(..., ge=1, description="Порядковый номер")
    is_active: bool = Field(True, description="Активен ли этап")

class WorkflowStageCreate(WorkflowStageBase):
    pass

class WorkflowStageUpdate(WorkflowStageBase):
    title: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None

class WorkflowStageResponse(WorkflowStageBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkflowStageReorder(BaseModel):
    stage_id: int
    new_order: int

class WorkflowStageListResponse(BaseModel):
    total: int
    items: list[WorkflowStageResponse]
