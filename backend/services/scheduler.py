"""Планировщик фоновых задач (APScheduler).

Регулярно проверяет «зависшие» заявки и рассылает уведомления. Планировщик
необязателен: если APScheduler не установлен или планировщик выключен
конфигом, приложение работает как обычно.
"""

from __future__ import annotations

from loguru import logger

from app.core.config import get_settings

_scheduler = None


def start_scheduler() -> None:
    """Запускает фоновые задачи. Безопасно вызывать повторно."""
    global _scheduler
    if _scheduler is not None:
        return

    settings = get_settings()
    if not settings.notifications_enabled:
        return

    try:  # pragma: no cover - зависит от установленного пакета
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.warning("APScheduler не установлен: уведомления запускаются вручную")
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_stuck_check,
        IntervalTrigger(hours=settings.notifications_interval_hours),
        id="stuck-interactions",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "Планировщик уведомлений запущен: каждые {} ч",
        settings.notifications_interval_hours,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


async def _run_stuck_check() -> None:
    from app.db.session import SessionLocal
    from app.services.notifications import notify_stuck_interactions

    try:
        async with SessionLocal() as session:
            count = await notify_stuck_interactions(session)
        if count:
            logger.info("Отправлено уведомлений о зависших заявках: {}", count)
    except Exception as exc:  # noqa: BLE001
        logger.error("Ошибка проверки зависших заявок: {}", exc)
