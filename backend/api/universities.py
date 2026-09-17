from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import get_current_user
from backend.db.session import get_db
from backend.models.entities import Interaction, University, User
from backend.schemas.entities import (
    UniversityCreate,
    UniversityRead,
    UniversityUpdate,
)

router = APIRouter(prefix="/api/universities", tags=["universities"])


async def _get_or_404(db: AsyncSession, university_id: int) -> University:
    university = await db.get(University, university_id)
    if university is None:
        raise HTTPException(status_code=404, detail="Вуз не найден")
    return university


@router.get("", response_model=list[UniversityRead])
async def list_universities(
    search: str | None = Query(default=None, description="Поиск по названию"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[University]:
    stmt = select(University).order_by(University.name)
    if search:
        stmt = stmt.where(University.name.ilike(f"%{search}%"))
    result = await db.scalars(stmt)
    return list(result)


@router.get("/{university_id}", response_model=UniversityRead)
async def get_university(
    university_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> University:
    return await _get_or_404(db, university_id)


@router.post("", response_model=UniversityRead, status_code=201)
async def create_university(
    payload: UniversityCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> University:
    university = University(**payload.model_dump())
    db.add(university)
    await db.commit()
    await db.refresh(university)
    return university


@router.patch("/{university_id}", response_model=UniversityRead)
async def update_university(
    university_id: int,
    payload: UniversityUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> University:
    university = await _get_or_404(db, university_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(university, field, value)
    await db.commit()
    await db.refresh(university)
    return university


@router.delete("/{university_id}", status_code=204)
async def delete_university(
    university_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    """Удаление вуза. Запрещено, если есть активные взаимодействия."""
    university = await _get_or_404(db, university_id)
    linked = await db.scalar(
        select(func.count(Interaction.id)).where(
            Interaction.university_id == university_id,
            Interaction.is_active.is_(True),
        )
    )
    if linked:
        raise HTTPException(
            status_code=409,
            detail=f"Нельзя удалить: {linked} активных взаимодействий",
        )
    await db.delete(university)
    await db.commit()
