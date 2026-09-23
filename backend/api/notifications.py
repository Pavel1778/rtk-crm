"""API уведомлений и контроля «зависших» заявок."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import User
from app.services.notifications import (
    build_message,
    find_stuck_interactions,
    notify_stuck_interactions,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class StuckInteractionRead(BaseModel):
    interaction_id: int
    university_name: str
    product_name: str | None
    stage_name: str
    days_in_stage: int
    manager: str | None
    message: str


class StuckResponse(BaseModel):
    timeout_days: int
    generated_at: datetime
    count: int
    items: list[StuckInteractionRead]


@router.get("/stuck", response_model=StuckResponse)
async def list_stuck(
    timeout_days: int | None = Query(
        default=None, ge=1, description="Порог в днях; по умолчанию из настроек"
    ),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> StuckResponse:
    """Список заявок, стоящих в одном статусе дольше порога (только admin)."""
    settings = get_settings()
    threshold = timeout_days or settings.stuck_timeout_days
    items = await find_stuck_interactions(db, threshold)
    return StuckResponse(
        timeout_days=threshold,
        generated_at=datetime.now(timezone.utc),
        count=len(items),
        items=[
            StuckInteractionRead(
                **item.__dict__, message=build_message(item)
            )
            for item in items
        ],
    )


@router.post("/stuck/dispatch", status_code=202)
async def dispatch_stuck(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, int]:
    """Ручной запуск рассылки уведомлений о зависших заявках (только admin)."""
    return {"notified": await notify_stuck_interactions(db)}
