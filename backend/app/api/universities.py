from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from datetime import timedelta

from app.database import get_db
from app.models.university import University
from app.models.workflow import WorkflowStage
from app.models.user import User
from app.models.file import AttachedFile
from app.models.comment import Comment
from app.schemas.university import (
    UniversityCreate, UniversityUpdate, UniversityResponse,
    WorkflowStageResponse, FileUploadResponse, CommentCreate, CommentResponse,
    ActionLogResponse, UserCreate, UserResponse, UserLogin, Token
)
from app.core.security import get_password_hash, create_access_token, verify_password
from app.core.dependencies import get_current_user, require_role
from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/api/v1", tags=["universities"])


@router.get("/universities/", response_model=List[UniversityResponse])
async def get_universities(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = None,
    manager_name: Optional[str] = None,
):
    """Получение списка вузов с фильтрацией."""
    query = select(University)
    if status_filter:
        query = query.where(University.status == status_filter)
    if manager_name:
        query = query.where(University.manager_name.ilike(f"%{manager_name}%"))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/universities/{university_id}", response_model=UniversityResponse)
async def get_university(university_id: int, db: AsyncSession = Depends(get_db)):
    """Получение информации о вузе."""
    result = await db.execute(select(University).where(University.id == university_id))
    university = result.scalar_one_or_none()
    if not university:
        raise HTTPException(status_code=404, detail="University not found")
    return university


@router.post("/universities/", response_model=UniversityResponse, status_code=201)
async def create_university(
    data: UniversityCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создание нового вуза (требует авторизации)."""
    existing = await db.execute(select(University).where(University.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="University with this name exists")
    
    new_uni = University(**data.model_dump())
    db.add(new_uni)
    await db.commit()
    await db.refresh(new_uni)
    
    # Логирование
    logger = AuditLogger(db)
    client_ip = request.client.host if request.client else "unknown"
    await logger.log_create(new_uni, user=current_user.username, ip=client_ip)
    
    return new_uni


@router.put("/universities/{university_id}", response_model=UniversityResponse)
async def update_university(
    university_id: int,
    data: UniversityUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновление данных вуза (требует авторизации)."""
    result = await db.execute(select(University).where(University.id == university_id))
    university = result.scalar_one_or_none()
    if not university:
        raise HTTPException(status_code=404, detail="University not found")
    
    old_data = {
        "name": university.name,
        "status": university.status,
        "manager_name": university.manager_name,
        "current_workflow_stage_id": university.current_workflow_stage_id,
    }
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(university, field, value)
    
    await db.commit()
    await db.refresh(university)
    
    # Логирование изменений
    logger = AuditLogger(db)
    client_ip = request.client.host if request.client else "unknown"
    new_data = {
        "name": university.name,
        "status": university.status,
        "manager_name": university.manager_name,
        "current_workflow_stage_id": university.current_workflow_stage_id,
    }
    await logger.log_update(university, old_data, new_data, user=current_user.username, ip=client_ip)
    
    return university


@router.delete("/universities/{university_id}", status_code=204)
async def delete_university(
    university_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаление вуза (требует авторизации)."""
    result = await db.execute(select(University).where(University.id == university_id))
    university = result.scalar_one_or_none()
    if not university:
        raise HTTPException(status_code=404, detail="University not found")
    
    uni_name = university.name
    await db.delete(university)
    await db.commit()
    
    # Логирование
    logger = AuditLogger(db)
    client_ip = request.client.host if request.client else "unknown"
    await logger.log_delete(university_id, uni_name, user=current_user.username, ip=client_ip)


# Workflow Stages
@router.get("/workflow-stages/", response_model=List[WorkflowStageResponse])
async def get_workflow_stages(db: AsyncSession = Depends(get_db)):
    """Получение всех этапов воркфлоу."""
    result = await db.execute(select(WorkflowStage).order_by(WorkflowStage.order))
    return result.scalars().all()


# Comments
@router.get("/universities/{university_id}/comments", response_model=List[CommentResponse])
async def get_comments(university_id: int, db: AsyncSession = Depends(get_db)):
    """Получение комментариев к вузу."""
    result = await db.execute(
        select(Comment)
        .where(Comment.university_id == university_id)
        .order_by(Comment.created_at.desc())
    )
    return result.scalars().all()


@router.post("/universities/{university_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    university_id: int,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Добавление комментария к вузу."""
    result = await db.execute(select(University).where(University.id == university_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="University not found")
    
    comment = Comment(
        university_id=university_id,
        text=data.text,
        author=data.author or current_user.username
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


# Files
@router.post("/universities/{university_id}/files", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    university_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Загрузка файла к вузу (заглушка для реализации)."""
    result = await db.execute(select(University).where(University.id == university_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="University not found")
    
    # TODO: Реализовать загрузку файлов
    raise HTTPException(status_code=501, detail="File upload not implemented yet")


# Logs
@router.get("/universities/{university_id}/logs", response_model=List[ActionLogResponse])
async def get_logs(
    university_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Получение логов действий по вузу (только для админов)."""
    result = await db.execute(
        select(ActionLog)
        .where(ActionLog.university_id == university_id)
        .order_by(ActionLog.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()
