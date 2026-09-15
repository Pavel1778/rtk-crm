from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.university import University
from app.schemas.university import UniversityCreate, UniversityUpdate, UniversityResponse
from typing import List, Optional

router = APIRouter(prefix="/api/v1/universities", tags=["universities"])


@router.get("/", response_model=List[UniversityResponse])
async def get_universities(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    manager_name: Optional[str] = None,
):
    query = select(University)
    if status:
        query = query.where(University.status == status)
    if manager_name:
        query = query.where(University.manager_name.ilike(f"%{manager_name}%"))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{university_id}", response_model=UniversityResponse)
async def get_university(university_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(University).where(University.id == university_id))
    university = result.scalar_one_or_none()
    if not university:
        raise HTTPException(status_code=404, detail="University not found")
    return university


@router.post("/", response_model=UniversityResponse, status_code=201)
async def create_university(data: UniversityCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(University).where(University.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="University with this name exists")
    new_uni = University(**data.model_dump())
    db.add(new_uni)
    await db.commit()
    await db.refresh(new_uni)
    return new_uni


@router.put("/{university_id}", response_model=UniversityResponse)
async def update_university(university_id: int, data: UniversityUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(University).where(University.id == university_id))
    university = result.scalar_one_or_none()
    if not university:
        raise HTTPException(status_code=404, detail="University not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(university, field, value)
    await db.commit()
    await db.refresh(university)
    return university


@router.delete("/{university_id}", status_code=204)
async def delete_university(university_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(University).where(University.id == university_id))
    university = result.scalar_one_or_none()
    if not university:
        raise HTTPException(status_code=404, detail="University not found")
    await db.delete(university)
    await db.commit()
