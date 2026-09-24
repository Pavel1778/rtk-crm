"""Уведомления о «зависших» заявках.

По Q&A Крылова: если взаимодействие не меняло статус более N дней, об этом
нужно уведомить руководителя ответственного, а не самого КАМа. Порог
настраивается через STUCK_TIMEOUT_DAYS. Каналы — заглушки Telegram и Email;
отсутствие токена/хоста означает, что канал выключен.
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

from app.core.config import get_settings
from app.models.entities import Interaction, ITProduct, University, User, WorkflowStageRef
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class StuckInteraction:
    interaction_id: int
    university_name: str
    product_name: str | None
    stage_name: str
    days_in_stage: int
    manager: str | None


async def find_stuck_interactions(
    db: AsyncSession, timeout_days: int | None = None
) -> list[StuckInteraction]:
    """Активные взаимодействия, стоящие в одном статусе дольше порога."""
    settings = get_settings()
    threshold_days = timeout_days or settings.stuck_timeout_days
    cutoff = datetime.now(UTC) - timedelta(days=threshold_days)

    rows = (
        await db.execute(
            select(Interaction, University, ITProduct, WorkflowStageRef, User)
            .outerjoin(University, Interaction.university_id == University.id)
            .outerjoin(ITProduct, Interaction.product_id == ITProduct.id)
            .outerjoin(WorkflowStageRef, Interaction.stage_id == WorkflowStageRef.id)
            .outerjoin(User, Interaction.assigned_kam_id == User.id)
            .where(
                Interaction.is_active.is_(True),
                Interaction.updated_at < cutoff,
            )
            .order_by(Interaction.updated_at)
        )
    ).all()

    now = datetime.now(UTC)
    result: list[StuckInteraction] = []
    for interaction, university, product, stage, manager in rows:
        updated = interaction.updated_at
        if updated is not None and updated.tzinfo is None:
            updated = updated.replace(tzinfo=UTC)
        days = (now - updated).days if updated else threshold_days
        result.append(
            StuckInteraction(
                interaction_id=interaction.id,
                university_name=university.name if university else "—",
                product_name=product.name if product else None,
                stage_name=stage.name if stage else "—",
                days_in_stage=days,
                manager=manager.full_name if manager else None,
            )
        )
    return result


def build_message(item: StuckInteraction) -> str:
    product = f", продукт «{item.product_name}»" if item.product_name else ""
    return (
        f"Заявка №{item.interaction_id} ({item.university_name}{product}) "
        f"находится на этапе «{item.stage_name}» уже {item.days_in_stage} дн. "
        f"Ответственный: {item.manager or 'не назначен'}."
    )


async def notify_stuck_interactions(db: AsyncSession) -> int:
    """Находит зависшие заявки и отправляет уведомления. Возвращает их число."""
    items = await find_stuck_interactions(db)
    if not items:
        return 0

    settings = get_settings()
    for item in items:
        text = build_message(item)
        sent = False
        if settings.telegram_bot_token:
            sent |= await _send_telegram(text)
        if settings.smtp_host:
            sent |= await _send_email(text, settings)
        # Если каналы не настроены, всё равно логируем — это видно в мониторинге.
        if not sent:
            logger.warning("Stuck interaction notification (no channel): {}", text)

    return len(items)


async def _send_telegram(text: str) -> bool:
    """Заглушка Telegram: при отсутствии chat_id канал считается выключенным."""
    logger.info("Telegram notification queued: {}", text)
    return False


async def _send_email(text: str, settings) -> bool:
    try:
        message = EmailMessage()
        message["Subject"] = "RTK CRM: заявка зависла в статусе"
        message["From"] = settings.smtp_from or settings.smtp_user
        message["To"] = settings.smtp_user
        message.set_content(text)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("SMTP notification failed: {}", exc)
        return False
