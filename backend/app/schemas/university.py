from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum as PyEnum


class UserRole(str, PyEnum):
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"


# User Schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.USER


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Workflow Stage Schemas
class WorkflowStageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    order: int = Field(..., ge=1, le=14)
    description: Optional[str] = None
    is_active: bool = True


class WorkflowStageResponse(BaseModel):
    id: int
    name: str
    order: int
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# University Schemas
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


# File Schemas
class FileUploadResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    file_size: int
    mime_type: Optional[str] = None
    uploaded_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Comment Schemas
class CommentCreate(BaseModel):
    text: str = Field(..., min_length=1)
    author: Optional[str] = None


class CommentResponse(BaseModel):
    id: int
    text: str
    author: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Log Schemas
class ActionLogResponse(BaseModel):
    id: int
    action: str
    description: Optional[str] = None
    user: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
