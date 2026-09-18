"""Catalogs API router - universities, products, directions, users."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import get_current_user, CurrentUser, require_role
from app.models.university import University
from app.models.it_product import ITProduct
from app.models.it_direction import ITDirection
from app.models.user import User
from app.schemas.university import UniversityCreate, UniversityResponse
from app.schemas.it_product import ITProductCreate, ITProductResponse
from app.schemas.it_direction import ITDirectionCreate, ITDirectionResponse
from app.schemas.user import UserResponse
from app.services.excel_import import parse_catalog_file

router = APIRouter()


# Universities endpoints
@router.get("/universities", response_model=List[UniversityResponse])
async def get_universities(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all universities."""
    query = select(University).order_by(University.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/universities", response_model=UniversityResponse)
@require_role(["manager", "admin"])
async def create_university(
    data: UniversityCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create new university."""
    university = University(**data.model_dump())
    db.add(university)
    await db.commit()
    await db.refresh(university)
    return university


# Products endpoints
@router.get("/products", response_model=List[ITProductResponse])
async def get_products(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all IT products."""
    query = select(ITProduct).order_by(ITProduct.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/products", response_model=ITProductResponse)
@require_role(["manager", "admin"])
async def create_product(
    data: ITProductCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create new IT product."""
    product = ITProduct(**data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


# Directions endpoints
@router.get("/directions", response_model=List[ITDirectionResponse])
async def get_directions(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all IT directions."""
    query = select(ITDirection).order_by(ITDirection.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/directions", response_model=ITDirectionResponse)
@require_role(["manager", "admin"])
async def create_direction(
    data: ITDirectionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create new IT direction."""
    direction = ITDirection(**data.model_dump())
    db.add(direction)
    await db.commit()
    await db.refresh(direction)
    return direction


# Users endpoints (only for managers and admins)
@router.get("/users", response_model=List[UserResponse])
@require_role(["manager", "admin"])
async def get_users(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all users."""
    query = select(User).order_by(User.full_name)
    result = await db.execute(query)
    return result.scalars().all()


# Import endpoint
@router.post("/import/preview")
@require_role(["manager", "admin"])
async def preview_import(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Preview catalog import from Excel file."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are supported")
    
    try:
        content = await file.read()
        result = parse_catalog_file(content)
        return {
            "total_rows": len(result["rows"]),
            "columns": result["columns"],
            "preview": result["rows"][:10],  # First 10 rows
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
