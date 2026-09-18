from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class ITProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=300, description="Название продукта")
    vendor: str = Field(..., min_length=1, max_length=200, description="Производитель")
    description: Optional[str] = Field(None, max_length=2000, description="Описание")

class ITProductCreate(ITProductBase):
    pass

class ITProductUpdate(ITProductBase):
    name: Optional[str] = None
    vendor: Optional[str] = None

class ITProductResponse(ITProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ITProductListResponse(BaseModel):
    total: int
    items: list[ITProductResponse]
