from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from datetime import datetime

class UniversityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=500, description="Полное название ВУЗа")
    city: str = Field(..., min_length=1, max_length=200, description="Город расположения")
    contact_person: Optional[str] = Field(None, max_length=300, description="Контактное лицо")
    phone: Optional[str] = Field(None, max_length=50, description="Телефон")
    email: Optional[EmailStr] = Field(None, description="Email для связи")

class UniversityCreate(UniversityBase):
    pass

class UniversityUpdate(UniversityBase):
    name: Optional[str] = None
    city: Optional[str] = None

class UniversityResponse(UniversityBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UniversityListResponse(BaseModel):
    total: int
    items: list[UniversityResponse]
