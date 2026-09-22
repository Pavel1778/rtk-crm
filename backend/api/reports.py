from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.session import get_db
from app.models.entities import (
    Action,
    Interaction,
    ITDirection,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from app.schemas.entities import (
    ReportMetric,
    ReportDynamicsPoint,
    ReportProduct,
    ReportResponse,
    ReportStage,
    StageProgress,
    UniversityRead,
)
from app.services.excel_export import generate_xlsx, generate_xls, generate_pdf

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

    product_rows = (
        await db.execute(
            select(
                ITProduct.id,
                ITProduct.name,
                func.count(Interaction.id).label("count"),
            )
            .join(Interaction, Interaction.product_id == ITProduct.id)
            .where(active)
            .group_by(ITProduct.id, ITProduct.name)
            .having(func.count(Interaction.id) > 0)
            .order_by(func.count(Interaction.id).desc(), ITProduct.name)
        )
    ).all()
    by_product = [
        ReportProduct(product_id=row.id, name=row.name, count=row.count)
        for row in product_rows
    ]

    stage_rows = [
        ReportStage(
            stage_id=stage.id,
            name=stage.name,
            order=stage.order,
            count=counts.get(stage.id, 0),
        )
        for stage in stages
    ]

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=29)
    dynamics_rows = (
        await db.execute(
            select(
                func.date(Interaction.created_at).label("date"),
                func.count(Interaction.id).label("count"),
            )
            .where(
                active,
                Interaction.created_at >= datetime.combine(
                    start_date, datetime.min.time(), tzinfo=timezone.utc
                ),
            )
            .group_by(func.date(Interaction.created_at))
        )
    ).all()
    dynamics_by_date = {row.date: row.count for row in dynamics_rows}
    dynamics = [
        ReportDynamicsPoint(
            date=(start_date + timedelta(days=offset)).isoformat(),
            count=dynamics_by_date.get(start_date + timedelta(days=offset), 0),
        )
        for offset in range(30)
    ]

    return ReportResponse(
        metrics=metrics,
        stage_progress=stage_progress,
        by_stage=stage_rows,
        by_product=by_product,
        dynamics=dynamics,
        totals={
            "interactions": total_interactions,
            "products": len(by_product),
            "stages": len(stages),
        },
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
    date_from: str | None = None,
    date_to: str | None = None,
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

        # Get direction name from product
        direction_name = None
        if product:
            direction = await db.get(ITDirection, product.direction_id) if product.direction_id else None
            direction_name = direction.name if direction else None

        data.append({
            "id": interaction.id,
            "university_name": university.name if university else None,
            "direction_name": direction_name,
            "product_name": product.name if product else None,
            "stage_name": stage.name if stage else None,
            "contract_number": interaction.contract_number,
            "contract_date": interaction.contract_date,
            "assigned_kam_name": assigned_kam.full_name if assigned_kam else None,
            "university_specialist": interaction.university_specialist,
            "notes": interaction.notes,
            "is_active": interaction.is_active,
        })

    return data


@router.options("/xlsx")
async def xlsx_preflight():
    """CORS preflight для XLSX экспорта."""
    return Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })


@router.get("/xlsx")
async def export_xlsx(
    stage_id: int | None = Query(default=None),
    university_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Экспорт взаимодействий в XLSX формате."""
    data = await _build_interaction_data(db, stage_id, university_id, product_id, date_from, date_to)
    xlsx_data = generate_xlsx(data)

    filename = f"interactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return StreamingResponse(
        xlsx_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.options("/xls")
async def xls_preflight():
    """CORS preflight для XLS экспорта."""
    return Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })


@router.get("/xls")
async def export_xls(
    stage_id: int | None = Query(default=None),
    university_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Экспорт взаимодействий в XLS формате."""
    data = await _build_interaction_data(db, stage_id, university_id, product_id, date_from, date_to)
    xls_data = generate_xls(data)

    filename = f"interactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xls"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return StreamingResponse(
        xls_data,
        media_type="application/vnd.ms-excel",
        headers=headers,
    )


@router.options("/pdf")
async def pdf_preflight():
    """CORS preflight для PDF экспорта."""
    return Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })


@router.get("/pdf")
async def export_pdf(
    stage_id: int | None = Query(default=None),
    university_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Экспорт взаимодействий в PDF формате."""
    data = await _build_interaction_data(db, stage_id, university_id, product_id, date_from, date_to)
    pdf_data = generate_pdf(data)

    filename = f"interactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return StreamingResponse(
        pdf_data,
        media_type="application/pdf",
        headers=headers,
    )


@router.get("/json")
async def export_json(
    stage_id: int | None = Query(default=None),
    university_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Экспорт взаимодействий в JSON формате для LMS интеграции."""
    data = await _build_interaction_data(db, stage_id, university_id, product_id, date_from, date_to)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(data),
        "interactions": data,
    }
