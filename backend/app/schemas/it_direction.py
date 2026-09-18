from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class ITDirectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=300, description="Название направления")
    description: Optional[str] = Field(None, max_length=2000, description="Описание")

class ITDirectionCreate(ITDirectionBase):
    pass

class ITDirectionUpdate(ITDirectionBase):
    name: Optional[str] = None

class ITDirectionResponse(ITDirectionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ITDirectionListResponse(BaseModel):
    total: int
    items: list[ITDirectionResponse]
