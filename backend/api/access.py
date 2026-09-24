"""Проверка прав доступа к взаимодействиям.

КАМ (роль `user`) работает только со своими карточками. Списки и доска
это фильтруют, но точечные операции по id нужно проверять отдельно —
иначе чужой id открывает карточку. Руководитель и администратор видят
все взаимодействия. Логика вынесена в один модуль, чтобы одинаково
применяться и в `interactions`, и в `files`.
"""

from app.models.entities import Interaction, User
from app.models.enums import UserRole
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


async def get_interaction_or_404(
    db: AsyncSession, interaction_id: int
) -> Interaction:
    interaction = await db.get(Interaction, interaction_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="Взаимодействие не найдено")
    return interaction


def ensure_can_access(interaction: Interaction, current: User) -> None:
    if current.role == UserRole.USER and interaction.assigned_kam_id != current.id:
        raise HTTPException(
            status_code=403,
            detail="Взаимодействие не принадлежит текущему пользователю",
        )


async def get_accessible_interaction(
    db: AsyncSession, interaction_id: int, current: User
) -> Interaction:
    """Взаимодействие, если у пользователя есть к нему доступ."""
    interaction = await get_interaction_or_404(db, interaction_id)
    ensure_can_access(interaction, current)
    return interaction
