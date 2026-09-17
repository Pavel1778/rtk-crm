from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import get_current_user
from backend.db.session import get_db
from backend.models.entities import (
    Action,
    Interaction,
    University,
    User,
    WorkflowStageRef,
)
from backend.schemas.entities import (
    ReportMetric,
    ReportResponse,
    StageProgress,
    UniversityRead,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=ReportResponse)
async def get_report(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ReportResponse:
    """Сводка: ключевые показатели и распределение по этапам воркфлоу."""
    active = Interaction.is_active.is_(True)

    total_universities = await db.scalar(select(func.count(University.id))) or 0
    total_interactions = await db.scalar(
        select(func.count(Interaction.id)).where(active)
    ) or 0
    with_contract = await db.scalar(
        select(func.count(Interaction.id)).where(
            active, Interaction.contract_number.isnot(None)
        )
    ) or 0
    open_actions = await db.scalar(
        select(func.count(Action.id)).where(Action.is_completed.is_(False))
    ) or 0
    done_actions = await db.scalar(
        select(func.count(Action.id)).where(Action.is_completed.is_(True))
    ) or 0

    metrics = [
        ReportMetric(
            key="universities", label="Всего вузов", value=total_universities
        ),
        ReportMetric(
            key="interactions",
            label="Активных взаимодействий",
            value=total_interactions,
        ),
        ReportMetric(
            key="contracts",
            label="Взаимодействий с договором",
            value=with_contract,
        ),
        ReportMetric(key="actions_open", label="Открытых задач", value=open_actions),
        ReportMetric(
            key="actions_done", label="Выполненных задач", value=done_actions
        ),
    ]

    stages = list(
        await db.scalars(
            select(WorkflowStageRef)
            .where(WorkflowStageRef.is_active.is_(True))
            .order_by(WorkflowStageRef.order)
        )
    )
    counts = dict(
        (
            await db.execute(
                select(Interaction.stage_id, func.count(Interaction.id))
                .where(active)
                .group_by(Interaction.stage_id)
            )
        ).all()
    )
    stage_progress = [
        StageProgress(
            stage_code=stage.code,
            stage_name=stage.name,
            count=counts.get(stage.id, 0),
            percent=round(counts.get(stage.id, 0) / total_interactions * 100, 1)
            if total_interactions
            else 0.0,
        )
        for stage in stages
    ]

    return ReportResponse(
        metrics=metrics,
        stage_progress=stage_progress,
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/universities", response_model=list[UniversityRead])
async def universities_report(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[University]:
    """Вузы в алфавитном порядке (для выгрузки в CSV на стороне клиента)."""
    result = await db.scalars(select(University).order_by(University.name))
    return list(result)
