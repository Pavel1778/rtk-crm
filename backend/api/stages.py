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
from app.models.enums import UserRole, WorkflowScope
from app.schemas.entities import (
    WorkflowStageCreate,
    WorkflowStageRead,
    WorkflowStageUpdate,
)


class StageReorderRequest(BaseModel):
    stages: list[dict[str, int]]


class StageTransferOption(BaseModel):
    id: int
    name: str


class StageImpact(BaseModel):
    stage_id: int
    name: str
    active_count: int
    total_count: int
    transfer_options: list[StageTransferOption]


router = APIRouter(prefix="/api/stages", tags=["workflow"])


async def _active_count(db: AsyncSession, stage_id: int) -> int:
    count = await db.scalar(
        select(func.count(Interaction.id)).where(
            Interaction.stage_id == stage_id, Interaction.is_active.is_(True)
        )
    )
    return count or 0


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
    scope: WorkflowScope | None = Query(
        default=None, description="b2b или b2c; без параметра — все этапы"
    ),
    include_inactive: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[WorkflowStageRead]:
    """Этапы воркфлоу в порядке следования с числом активных взаимодействий."""
    stmt = select(WorkflowStageRef).order_by(
        WorkflowStageRef.scope, WorkflowStageRef.order
    )
    if scope is not None:
        stmt = stmt.where(WorkflowStageRef.scope == scope)
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
            WorkflowStageRef.scope == payload.scope,
            (WorkflowStageRef.code == payload.code)
            | (WorkflowStageRef.order == payload.order),
        )
    )
    if clash:
        raise HTTPException(
            status_code=409,
            detail="Этап с таким кодом или порядком уже существует в этом workflow",
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
    if update_data.get("is_active") is False and stage.is_active:
        active = await _active_count(db, stage_id)
        if active:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"В этапе «{stage.name}» {active} активных взаимодействий. "
                    "Перенесите их или удалите этап с переносом."
                ),
            )

    for field, value in update_data.items():
        setattr(stage, field, value)
    
    await db.commit()
    await db.refresh(stage)
    return await _with_counts(db, stage)


@router.get("/{stage_id}/impact", response_model=StageImpact)
async def stage_impact(
    stage_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StageImpact:
    """Предпросмотр последствий выключения или удаления этапа."""
    stage = await db.get(WorkflowStageRef, stage_id)
    if stage is None:
        raise HTTPException(status_code=404, detail="Этап не найден")

    total = await db.scalar(
        select(func.count(Interaction.id)).where(Interaction.stage_id == stage_id)
    )
    options = list(
        await db.scalars(
            select(WorkflowStageRef)
            .where(WorkflowStageRef.id != stage_id)
            .order_by(WorkflowStageRef.order)
        )
    )
    return StageImpact(
        stage_id=stage.id,
        name=stage.name,
        active_count=await _active_count(db, stage_id),
        total_count=total or 0,
        transfer_options=[
            StageTransferOption(id=option.id, name=option.name) for option in options
        ],
    )


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
    return await list_stages(None, False, db, current)
