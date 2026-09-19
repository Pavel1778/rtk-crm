from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import get_current_user
from backend.db.session import get_db
from backend.models.entities import (
    Action,
    Interaction,
    ITProduct,
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
from backend.services.excel_export import generate_xlsx, generate_xls, generate_pdf

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


async def _build_interaction_data(
    db: AsyncSession,
    stage_id: int | None = None,
    university_id: int | None = None,
    product_id: int | None = None,
) -> list[dict]:
    """Построение данных взаимодействий для экспорта."""
    filters: list = [Interaction.is_active.is_(True)]
    if stage_id is not None:
        filters.append(Interaction.stage_id == stage_id)
    if university_id is not None:
        filters.append(Interaction.university_id == university_id)
    if product_id is not None:
        filters.append(Interaction.product_id == product_id)
    
    interactions = list(
        await db.scalars(
            select(Interaction).where(*filters).order_by(Interaction.id)
        )
    )
    
    data = []
    for interaction in interactions:
        university = await db.get(University, interaction.university_id)
        product = await db.get(ITProduct, interaction.product_id) if interaction.product_id else None
        stage = await db.get(WorkflowStageRef, interaction.stage_id)
        assigned_kam = await db.get(User, interaction.assigned_kam_id) if interaction.assigned_kam_id else None
        assigned_kam = await db.get(User, interaction.assigned_kam_id) if interaction.assigned_kam_id else None
        
        data.append({
            "id": interaction.id,
            "university_name": university.name if university else None,
            "product_name": product.name if product else None,
            "stage_name": stage.name if stage else None,
            "contract_number": interaction.contract_number,
            "contract_date": interaction.contract_date,
            "rkn_specialist_name": rkn_specialist.full_name if rkn_specialist else None,
            "assigned_kam_name": assigned_kam.full_name if assigned_kam else None,
            "university_specialist": interaction.university_specialist,
            "notes": interaction.notes,
            "is_active": interaction.is_active,
        })
    
    return data


@router.get("/xlsx")
async def export_xlsx(
    stage_id: int | None = Query(default=None),
    university_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Экспорт взаимодействий в XLSX формате."""
    data = await _build_interaction_data(db, stage_id, university_id, product_id)
    xlsx_data = generate_xlsx(data)
    
    filename = f"interactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        xlsx_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/xls")
async def export_xls(
    stage_id: int | None = Query(default=None),
    university_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Экспорт взаимодействий в XLS формате."""
    data = await _build_interaction_data(db, stage_id, university_id, product_id)
    xls_data = generate_xls(data)
    
    filename = f"interactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xls"
    return StreamingResponse(
        xls_data,
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/pdf")
async def export_pdf(
    stage_id: int | None = Query(default=None),
    university_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Экспорт взаимодействий в PDF формате."""
    data = await _build_interaction_data(db, stage_id, university_id, product_id)
    pdf_data = generate_pdf(data)
    
    filename = f"interactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(
        pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
