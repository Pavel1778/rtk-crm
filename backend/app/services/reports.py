"""
Сервис генерации отчётов и дашбордов.
Предоставляет данные для графиков и KPI-метрик.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from loguru import logger

from app.models.interaction import Interaction
from app.models.university import University
from app.models.it_product import ITProduct
from app.models.it_direction import ITDirection
from app.models.workflow_stage import WorkflowStage
from app.models.user import User
from app.core.config import settings


async def build_dashboard(db: AsyncSession) -> Dict[str, Any]:
    """
    Построение данных для дашборда: KPI + данные для графиков.

    :param db: Сессия базы данных
    :return: Словарь с данными дашборда
    """
    # KPI метрики
    total_interactions = await db.scalar(select(func.count()).select_from(Interaction))
    
    # Активные взаимодействия (не на финальном этапе)
    final_stage = await db.scalar(
        select(WorkflowStage.id).order_by(WorkflowStage.order.desc()).limit(1)
    )
    active_interactions = await db.scalar(
        select(func.count())
        .select_from(Interaction)
        .where(Interaction.current_stage_id != final_stage)
    )
    
    # Просроченные (> STALE_STATUS_DAYS дней без изменений)
    stale_date = datetime.utcnow() - timedelta(days=settings.STALE_STATUS_DAYS)
    stale_interactions = await db.scalar(
        select(func.count())
        .select_from(Interaction)
        .where(Interaction.updated_at < stale_date)
    )
    
    # Количество ВУЗов
    universities_count = await db.scalar(
        select(func.count(distinct(Interaction.university_id)))
    )
    
    # Количество продуктов
    products_count = await db.scalar(
        select(func.count(distinct(Interaction.product_id)))
    )
    
    # Количество КАМов
    kam_count = await db.scalar(
        select(func.count(distinct(Interaction.assigned_kam_id)))
    )

    kpi = {
        "total_interactions": total_interactions or 0,
        "active_interactions": active_interactions or 0,
        "stale_interactions": stale_interactions or 0,
        "universities_count": universities_count or 0,
        "products_count": products_count or 0,
        "kam_count": kam_count or 0,
    }

    # Данные для графика по этапам (Bar chart)
    stages_data = await db.execute(
        select(WorkflowStage.title, func.count(Interaction.id))
        .join(Interaction, WorkflowStage.id == Interaction.current_stage_id, isouter=True)
        .group_by(WorkflowStage.id, WorkflowStage.title, WorkflowStage.order)
        .order_by(WorkflowStage.order)
    )
    stage_chart = [
        {"stage": row[0], "count": row[1] or 0}
        for row in stages_data.fetchall()
    ]

    # Данные для графика по продуктам (Pie chart)
    products_data = await db.execute(
        select(ITProduct.name, func.count(Interaction.id))
        .join(Interaction, ITProduct.id == Interaction.product_id, isouter=True)
        .group_by(ITProduct.id, ITProduct.name)
    )
    product_chart = [
        {"product": row[0] or "Без продукта", "count": row[1] or 0}
        for row in products_data.fetchall()
    ]

    # Данные для графика динамики за 30 дней (Line chart)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    dynamics_data = await db.execute(
        select(func.date_trunc('day', Interaction.created_at), func.count(Interaction.id))
        .where(Interaction.created_at >= thirty_days_ago)
        .group_by(func.date_trunc('day', Interaction.created_at))
        .order_by(func.date_trunc('day', Interaction.created_at))
    )
    dynamics_chart = [
        {"date": row[0].strftime('%Y-%m-%d'), "count": row[1]}
        for row in dynamics_data.fetchall()
    ]

    # Заполняем пропущенные дни нулями
    all_dates = [(thirty_days_ago + timedelta(days=i)).date() for i in range(31)]
    dynamics_dict = {item["date"]: item["count"] for item in dynamics_chart}
    dynamics_chart_full = [
        {"date": d.strftime('%Y-%m-%d'), "count": dynamics_dict.get(d.strftime('%Y-%m-%d'), 0)}
        for d in all_dates
    ]

    dashboard = {
        "kpi": kpi,
        "charts": {
            "stage_bar": stage_chart,
            "product_pie": product_chart,
            "dynamics_line": dynamics_chart_full,
        }
    }

    logger.info(f"Дашборд сформирован: {len(stage_chart)} этапов, {len(product_chart)} продуктов")
    return dashboard


async def get_report_data(
    db: AsyncSession,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Получение данных для отчёта по взаимодействиям.

    :param db: Сессия базы данных
    :param filters: Фильтры (period_start, period_end, product_ids, direction_ids, kam_ids)
    :return: Список словарей с данными
    """
    query = select(
        Interaction.id,
        University.name.label('university_name'),
        ITProduct.name.label('product_name'),
        ITDirection.name.label('direction_name'),
        WorkflowStage.title.label('stage_title'),
        Interaction.contract_number,
        Interaction.license_sign_date,
        Interaction.license_expiry_year,
        User.full_name.label('kam_name'),
        Interaction.university_responsible,
        Interaction.created_at,
        Interaction.updated_at,
    ).join(University, Interaction.university_id == University.id) \
     .join(ITProduct, Interaction.product_id == ITProduct.id, isouter=True) \
     .join(ITDirection, Interaction.direction_id == ITDirection.id, isouter=True) \
     .join(WorkflowStage, Interaction.current_stage_id == WorkflowStage.id) \
     .join(User, Interaction.assigned_kam_id == User.id, isouter=True)

    if filters:
        if filters.get('period_start'):
            query = query.where(Interaction.created_at >= filters['period_start'])
        if filters.get('period_end'):
            query = query.where(Interaction.created_at <= filters['period_end'])
        if filters.get('product_ids'):
            query = query.where(Interaction.product_id.in_(filters['product_ids']))
        if filters.get('direction_ids'):
            query = query.where(Interaction.direction_id.in_(filters['direction_ids']))
        if filters.get('kam_ids'):
            query = query.where(Interaction.assigned_kam_id.in_(filters['kam_ids']))

    result = await db.execute(query)
    rows = result.fetchall()

    data = [
        {
            "id": row.id,
            "ВУЗ": row.university_name,
            "Продукт": row.product_name or "-",
            "Направление": row.direction_name or "-",
            "Этап": row.stage_title,
            "Договор": row.contract_number or "-",
            "Дата подписания": row.license_sign_date.strftime('%d.%m.%Y') if row.license_sign_date else "-",
            "Год окончания": row.license_expiry_year or "-",
            "КАМ": row.kam_name or "-",
            "Ответственный ВУЗа": row.university_responsible or "-",
            "Создано": row.created_at.strftime('%d.%m.%Y'),
            "Обновлено": row.updated_at.strftime('%d.%m.%Y'),
        }
        for row in rows
    ]

    logger.info(f"Отчёт сформирован: {len(data)} строк")
    return data
