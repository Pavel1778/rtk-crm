from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Пользователи ----------
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(max_length=255)
    is_admin: bool = False


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserRead(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    is_admin: bool
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------- Вузы ----------
class UniversityBase(BaseModel):
    name: str = Field(max_length=500)
    city: str | None = None
    contact_person: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None


class UniversityCreate(UniversityBase):
    pass


class UniversityUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=500)
    city: str | None = None
    contact_person: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None


class UniversityRead(ORMModel, UniversityBase):
    id: int


class UniversityBrief(ORMModel):
    id: int
    name: str


# ---------- Направления ИТ ----------
class ITDirectionBase(BaseModel):
    name: str = Field(max_length=255)


class ITDirectionCreate(ITDirectionBase):
    pass


class ITDirectionRead(ORMModel, ITDirectionBase):
    id: int


# ---------- Продукты ----------
class ITProductBase(BaseModel):
    name: str = Field(max_length=255)
    direction_id: int | None = None


class ITProductCreate(ITProductBase):
    pass


class ITProductRead(ORMModel, ITProductBase):
    id: int
    direction_name: str | None = None


class ITProductBrief(ORMModel):
    id: int
    name: str


# ---------- Этапы воркфлоу ----------
class WorkflowStageBase(BaseModel):
    code: str = Field(max_length=50)
    name: str = Field(max_length=255)
    order: int
    color: str | None = None
    is_active: bool = True


class WorkflowStageCreate(WorkflowStageBase):
    pass


class WorkflowStageUpdate(BaseModel):
    code: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, max_length=255)
    order: int | None = None
    color: str | None = None
    is_active: bool | None = None


class WorkflowStageRead(ORMModel, WorkflowStageBase):
    id: int
    interaction_count: int = 0


# ---------- Взаимодействия ----------
class InteractionBase(BaseModel):
    university_id: int
    product_id: int | None = None
    stage_id: int
    contract_number: str | None = None
    contract_date: str | None = None
    assigned_kam_id: int | None = None
    university_specialist: str | None = None
    notes: str | None = None
    is_active: bool = True


class InteractionCreate(BaseModel):
    university_id: int
    product_id: int | None = None
    stage_id: int | None = None


class InteractionUpdate(BaseModel):
    product_id: int | None = None
    stage_id: int | None = None
    contract_number: str | None = None
    contract_date: str | None = None
    assigned_kam_id: int | None = None
    university_specialist: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class ActionRead(ORMModel):
    id: int
    interaction_id: int
    title: str
    description: str | None = None
    due_date: str | None = None
    is_completed: bool
    author_name: str | None = None


class CommentRead(ORMModel):
    id: int
    interaction_id: int
    text: str
    author_name: str | None = None
    created_at: datetime


class InteractionRead(ORMModel, InteractionBase):
    id: int
    university_name: str | None = None
    product_name: str | None = None
    stage_name: str | None = None
    stage_code: str | None = None
    assigned_kam_name: str | None = None


class InteractionCard(ORMModel):
    """Карточка канбан-доски: взаимодействие + счётчики задач и комментариев."""

    id: int
    university_id: int
    university_name: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    stage_id: int
    stage_name: str | None = None
    stage_code: str | None = None
    contract_number: str | None = None
    university_specialist: str | None = None
    assigned_kam_name: str | None = None
    is_active: bool
    actions_open: int = 0
    actions_total: int = 0
    comments_count: int = 0


class BoardColumn(BaseModel):
    stage: WorkflowStageRead
    interactions: list[InteractionCard]


class BoardResponse(BaseModel):
    columns: list[BoardColumn]
    total: int


# ---------- Действия ----------
class ActionBase(BaseModel):
    title: str = Field(max_length=500)
    description: str | None = None
    due_date: str | None = None


class ActionCreate(ActionBase):
    pass


class ActionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    due_date: str | None = None
    is_completed: bool | None = None


# ---------- Комментарии ----------
class CommentBase(BaseModel):
    text: str


class CommentCreate(CommentBase):
    pass


# ---------- Файлы ----------
class AttachedFileBase(BaseModel):
    filename: str = Field(max_length=255)
    size: int
    mime_type: str = Field(max_length=100)


class AttachedFileRead(ORMModel, AttachedFileBase):
    id: int
    interaction_id: int
    uploaded_by: int | None = None
    uploader_name: str | None = None
    created_at: datetime


# ---------- Отчётность ----------
class ReportMetric(BaseModel):
    key: str
    label: str
    value: int | float
    unit: str | None = None


class StageProgress(BaseModel):
    stage_code: str
    stage_name: str
    count: int
    percent: float


class ReportResponse(BaseModel):
    metrics: list[ReportMetric]
    stage_progress: list[StageProgress]
    generated_at: datetime


class HealthResponse(BaseModel):
    status: str
    app: str
    database: str
