from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UniversityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    vendor: Optional[str] = None
    product: Optional[str] = None
    contract_number: Optional[str] = None
    license_signed: bool = False
    license_expiry_year: Optional[int] = None
    status: str = Field(..., min_length=1, max_length=50)
    manager_name: Optional[str] = None
    university_responsible: Optional[str] = None
    comment: Optional[str] = None
    current_workflow_stage_id: Optional[int] = None


class UniversityUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    vendor: Optional[str] = None
    product: Optional[str] = None
    contract_number: Optional[str] = None
    license_signed: Optional[bool] = None
    license_expiry_year: Optional[int] = None
    status: Optional[str] = None
    manager_name: Optional[str] = None
    university_responsible: Optional[str] = None
    comment: Optional[str] = None
    current_workflow_stage_id: Optional[int] = None


class UniversityResponse(BaseModel):
    id: int
    name: str
    vendor: Optional[str] = None
    product: Optional[str] = None
    contract_number: Optional[str] = None
    license_signed: bool
    license_expiry_year: Optional[int] = None
    status: str
    manager_name: Optional[str] = None
    university_responsible: Optional[str] = None
    comment: Optional[str] = None
    current_workflow_stage_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
