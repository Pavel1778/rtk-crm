from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import (
    Action,
    AttachedFile,
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
from app.services.report_cache import get_report_cache, set_report_cache

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _report_filename(extension: str) -> str:
    return f"rtk-report-{datetime.now(timezone.utc):%Y%m%d}.{extension}"


def _report_filters(
    stage_id: int | None,
    university_id: int | None,
    product_id: int | None,
    direction_id: int | None,
    assigned_kam_id: int | None,
    date_from: date | None,
    date_to: date | None,
) -> list:
    filters: list = [Interaction.is_active.is_(True)]
    if stage_id is not None:
        filters.append(Interaction.stage_id == stage_id)
    if university_id is not None:
        filters.append(Interaction.university_id == university_id)
    if product_id is not None:
        filters.append(Interaction.product_id == product_id)
    if direction_id is not None:
        filters.append(Interaction.product.has(ITProduct.direction_id == direction_id))
    if assigned_kam_id is not None:
        filters.append(Interaction.assigned_kam_id == assigned_kam_id)
    if date_from is not None:
        filters.append(
            Interaction.created_at
            >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        )
    if date_to is not None:
        filters.append(
            Interaction.created_at
            < datetime.combine(
                date_to + timedelta(days=1),
                time.min,
                tzinfo=timezone.utc,
            )
        )
    return filters


@router.get("", response_model=ReportResponse)
async def get_report(
    stage_id: int | None = Query(default=None),
    university_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    direction_id: int | None = Query(default=None),
    assigned_kam_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ReportResponse:
    """Сводка: ключевые показатели и распределение по этапам воркфлоу."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="Дата начала не может быть позже даты окончания",
        )
    cache_key = (
        "reports:v1:"
        f"{stage_id}:{university_id}:{product_id}:{direction_id}:"
        f"{assigned_kam_id}:{date_from}:{date_to}"
    )
    cached = await get_report_cache(cache_key)
    if cached is not None:
        return ReportResponse.model_validate_json(cached)

    filters = _report_filters(
        stage_id,
        university_id,
        product_id,
        direction_id,
        assigned_kam_id,
        date_from,
        date_to,
    )

    total_universities = await db.scalar(
        select(func.count(func.distinct(Interaction.university_id))).where(*filters)
    ) or 0
    total_interactions = await db.scalar(
        select(func.count(Interaction.id)).where(*filters)
    ) or 0
    with_contract = await db.scalar(
        select(func.count(Interaction.id)).where(
            *filters, Interaction.contract_number.isnot(None)
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
                .where(*filters)
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
            .select_from(Interaction)
            .outerjoin(ITProduct, Interaction.product_id == ITProduct.id)
            .where(*filters)
            .group_by(ITProduct.id, ITProduct.name)
            .having(func.count(Interaction.id) > 0)
            .order_by(func.count(Interaction.id).desc(), ITProduct.name.nulls_last())
        )
    ).all()
    by_product = [
        ReportProduct(
            product_id=row.id or 0,
            name=row.name or "Без продукта",
            count=row.count,
        )
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
    dynamics_end = date_to or today
    dynamics_start = date_from or dynamics_end - timedelta(days=29)
    if dynamics_start > dynamics_end:
        raise HTTPException(
            status_code=400,
            detail="Период отчёта не может начинаться в будущем",
        )
    dynamics_filters = _report_filters(
        stage_id,
        university_id,
        product_id,
        direction_id,
        assigned_kam_id,
        dynamics_start,
        dynamics_end,
    )
    dynamics_rows = (
        await db.execute(
            select(
                func.date(Interaction.created_at).label("date"),
                func.count(Interaction.id).label("count"),
            )
            .where(*dynamics_filters)
            .group_by(func.date(Interaction.created_at))
        )
    ).all()
    dynamics_by_date = {
        str(row.date)[:10]: row.count
        for row in dynamics_rows
    }
    dynamics = [
        ReportDynamicsPoint(
            date=(dynamics_start + timedelta(days=offset)).isoformat(),
            count=dynamics_by_date.get(
                (dynamics_start + timedelta(days=offset)).isoformat(),
                0,
            ),
        )
        for offset in range((dynamics_end - dynamics_start).days + 1)
    ]

    response = ReportResponse(
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
    await set_report_cache(cache_key, response.model_dump_json())
    return response


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
    direction_id: int | None = None,
    assigned_kam_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    """Построение данных взаимодействий для экспорта."""
    filters = _report_filters(
        stage_id,
        university_id,
        product_id,
        direction_id,
        assigned_kam_id,
        date_from,
        date_to,
    )

    rows = (
        await db.execute(
            select(
                Interaction,
                University.name,
                ITDirection.name,
                ITProduct.name,
                WorkflowStageRef.name,
                User.full_name,
                WorkflowStageRef.scope,
                ITProduct.direction_id,
            )
            .join(University, Interaction.university_id == University.id)
            .outerjoin(ITProduct, Interaction.product_id == ITProduct.id)
            .outerjoin(ITDirection, ITProduct.direction_id == ITDirection.id)
            .join(WorkflowStageRef, Interaction.stage_id == WorkflowStageRef.id)
            .outerjoin(User, Interaction.assigned_kam_id == User.id)
            .where(*filters)
            .order_by(Interaction.id)
        )
    ).all()

    data = []
    for (
        interaction,
        university_name,
        direction_name,
        product_name,
        stage_name,
        assigned_kam_name,
        scope,
        direction_id,
    ) in rows:
        data.append({
            "id": interaction.id,
            "university_name": university_name,
            "direction_name": direction_name,
            "product_name": product_name,
            "stage_name": stage_name,
            "contract_number": interaction.contract_number,
            "contract_date": interaction.contract_date,
            "assigned_kam_name": assigned_kam_name,
            "university_specialist": interaction.university_specialist,
            "notes": interaction.notes,
            "is_active": interaction.is_active,
            # Ключи связи с БД: id сущностей и внешние ключи. Нужны LMS/CMS,
            # чтобы сопоставить выгрузку с записями на своей стороне.
            "scope": scope.value if hasattr(scope, "value") else scope,
            "university_id": interaction.university_id,
            "product_id": interaction.product_id,
            "stage_id": interaction.stage_id,
            "direction_id": direction_id,
            "assigned_kam_id": interaction.assigned_kam_id,
        })

    return data


@router.get("/xlsx")
async def export_xlsx(
    stage_id: int | None = Query(default=None),
    university_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    direction_id: int | None = Query(default=None),
    assigned_kam_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Экспорт взаимодействий в XLSX формате."""
    data = await _build_interaction_data(
        db,
        stage_id,
        university_id,
        product_id,
        direction_id,
        assigned_kam_id,
        date_from,
        date_to,
    )
    xlsx_data = generate_xlsx(data)

    filename = _report_filename("xlsx")
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return StreamingResponse(
        xlsx_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/xls")
async def export_xls(
    stage_id: int | None = Query(default=None),
    university_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    direction_id: int | None = Query(default=None),
    assigned_kam_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Экспорт взаимодействий в XLS формате."""
    data = await _build_interaction_data(
        db,
        stage_id,
        university_id,
        product_id,
        direction_id,
        assigned_kam_id,
        date_from,
        date_to,
    )
    xls_data = generate_xls(data)

    filename = _report_filename("xls")
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return StreamingResponse(
        xls_data,
        media_type="application/vnd.ms-excel",
        headers=headers,
    )


@router.get("/pdf")
async def export_pdf(
    stage_id: int | None = Query(default=None),
    university_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    direction_id: int | None = Query(default=None),
    assigned_kam_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Экспорт взаимодействий в PDF формате."""
    data = await _build_interaction_data(
        db,
        stage_id,
        university_id,
        product_id,
        direction_id,
        assigned_kam_id,
        date_from,
        date_to,
    )
    pdf_data = generate_pdf(data)

    filename = _report_filename("pdf")
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
    direction_id: int | None = Query(default=None),
    assigned_kam_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Экспорт взаимодействий в JSON для LMS-интеграции.

    По Q&A Крылова выгрузка должна содержать не только данные карточек, но и
    ключи связи: id/внешние ключи записей БД и ключи файлов в S3-хранилище,
    чтобы принимающая сторона могла сопоставить объекты и скачать вложения.
    """
    data = await _build_interaction_data(
        db,
        stage_id,
        university_id,
        product_id,
        direction_id,
        assigned_kam_id,
        date_from,
        date_to,
    )

    interaction_ids = [item["id"] for item in data]
    files_by_interaction = await _files_by_interaction(db, interaction_ids)
    for item in data:
        item["files"] = files_by_interaction.get(item["id"], [])

    settings = get_settings()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(data),
        "storage": {
            "type": "s3" if settings.s3_enabled else "local",
            "bucket": settings.s3_bucket if settings.s3_enabled else None,
        },
        # Применённые фильтры: выгрузка воспроизводима по этим параметрам.
        "filters": {
            "stage_id": stage_id,
            "university_id": university_id,
            "product_id": product_id,
            "direction_id": direction_id,
            "assigned_kam_id": assigned_kam_id,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
        },
        "interactions": data,
    }


async def _files_by_interaction(
    db: AsyncSession, interaction_ids: list[int]
) -> dict[int, list[dict]]:
    """Вложения, сгруппированные по взаимодействию, с ключами связи с S3."""
    if not interaction_ids:
        return {}

    settings = get_settings()
    rows = await db.scalars(
        select(AttachedFile).where(AttachedFile.interaction_id.in_(interaction_ids))
    )
    grouped: dict[int, list[dict]] = {}
    for attached in rows:
        grouped.setdefault(attached.interaction_id, []).append({
            "file_id": attached.id,
            "interaction_id": attached.interaction_id,
            "filename": attached.filename,
            # file_path — это ключ объекта в бакете (или путь в uploads/).
            "bucket": settings.s3_bucket if settings.s3_enabled else None,
            "key": attached.file_path,
            "size": attached.size,
            "mime_type": attached.mime_type,
            "uploaded_by": attached.uploaded_by,
        })
    return grouped
