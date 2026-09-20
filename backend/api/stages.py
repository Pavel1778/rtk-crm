from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.session import get_db
from app.models.entities import (
    Interaction,
    User,
    WorkflowStageRef,
)
from app.models.enums import UserRole
from app.schemas.entities import (
    WorkflowStageCreate,
    WorkflowStageRead,
    WorkflowStageUpdate,
)


class StageReorderRequest(BaseModel):
    stages: list[dict[str, int]]

router = APIRouter(prefix="/api/stages", tags=["workflow"])


async def _with_counts(
    db: AsyncSession, stage: WorkflowStageRef
) -> WorkflowStageRead:
    count = await db.scalar(
        select(func.count(Interaction.id)).where(
            Interaction.stage_id == stage.id, Interaction.is_active.is_(True)
        )
    )
    payload = WorkflowStageRead.model_validate(stage)
    return payload.model_copy(update={"interaction_count": count or 0})


@router.get("", response_model=list[WorkflowStageRead])
async def list_stages(
    include_inactive: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[WorkflowStageRead]:
    """Этапы воркфлоу в порядке следования с числом активных взаимодействий."""
    stmt = select(WorkflowStageRef).order_by(WorkflowStageRef.order)
    if not include_inactive:
        stmt = stmt.where(WorkflowStageRef.is_active.is_(True))
    stages = list(await db.scalars(stmt))
    return [await _with_counts(db, stage) for stage in stages]


@router.post("", response_model=WorkflowStageRead, status_code=201)
async def create_stage(
    payload: WorkflowStageCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> WorkflowStageRead:
    """Добавление этапа (настройка воркфлоу пользователем). Только для admin."""
    if current.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Только администраторы могут редактировать этапы"
        )
    clash = await db.scalar(
        select(WorkflowStageRef.id).where(
            (WorkflowStageRef.code == payload.code)
            | (WorkflowStageRef.order == payload.order)
        )
    )
    if clash:
        raise HTTPException(
            status_code=409,
            detail="Этап с таким кодом или порядком уже существует",
        )
    stage = WorkflowStageRef(**payload.model_dump())
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    return await _with_counts(db, stage)


@router.patch("/{stage_id}", response_model=WorkflowStageRead)
async def update_stage(
    stage_id: int,
    payload: WorkflowStageUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> WorkflowStageRead:
    if current.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Только администраторы могут редактировать этапы"
        )
    stage = await db.get(WorkflowStageRef, stage_id)
    if stage is None:
        raise HTTPException(status_code=404, detail="Этап не найден")
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stage, field, value)
    
    await db.commit()
    await db.refresh(stage)
    return await _with_counts(db, stage)


@router.delete("/{stage_id}", status_code=204)
async def delete_stage(
    stage_id: int,
    target_stage_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> None:
    """Удаление этапа. Только для admin.
    Если target_stage_id указан, взаимодействия переносятся на другой этап.
    """
    if current.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Только администраторы могут редактировать этапы"
        )
    stage = await db.get(WorkflowStageRef, stage_id)
    if stage is None:
        raise HTTPException(status_code=404, detail="Этап не найден")

    linked = await db.scalar(
        select(func.count(Interaction.id)).where(
            Interaction.stage_id == stage_id
        )
    )

    if linked:
        if target_stage_id is None:
            raise HTTPException(
                status_code=409,
                detail=f"На этапе {linked} взаимодействий. Укажите target_stage_id для переноса.",
            )
        target_stage = await db.get(WorkflowStageRef, target_stage_id)
        if target_stage is None:
            raise HTTPException(status_code=404, detail="Целевой этап не найден")

        interactions = list(
            await db.scalars(
                select(Interaction).where(Interaction.stage_id == stage_id)
            )
        )
        for interaction in interactions:
            interaction.stage_id = target_stage_id
        await db.commit()

    await db.delete(stage)
    await db.commit()


@router.post("/reorder", status_code=200)
async def reorder_stages(
    payload: StageReorderRequest,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[WorkflowStageRead]:
    """Пересортировка этапов. Только для admin."""
    if current.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Только администраторы могут редактировать этапы"
        )
    for item in payload.stages:
        stage = await db.get(WorkflowStageRef, item["id"])
        if stage:
            stage.order = item["order"]
    await db.commit()
    return await list_stages(False, db, current)
