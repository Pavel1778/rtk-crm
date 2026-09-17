from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import get_current_user
from backend.db.session import get_db
from backend.models.entities import (
    Interaction,
    ITDirection,
    ITProduct,
    User,
)
from backend.schemas.entities import (
    ITDirectionCreate,
    ITDirectionRead,
    ITProductCreate,
    ITProductRead,
)

router = APIRouter(prefix="/api", tags=["directories"])


# ---------- Направления ИТ ----------
@router.get("/directions", response_model=list[ITDirectionRead])
async def list_directions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ITDirection]:
    result = await db.scalars(select(ITDirection).order_by(ITDirection.name))
    return list(result)


@router.post("/directions", response_model=ITDirectionRead, status_code=201)
async def create_direction(
    payload: ITDirectionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ITDirection:
    exists = await db.scalar(
        select(ITDirection.id).where(ITDirection.name == payload.name)
    )
    if exists:
        raise HTTPException(
            status_code=409, detail="Такое направление уже есть в справочнике"
        )
    direction = ITDirection(name=payload.name)
    db.add(direction)
    await db.commit()
    await db.refresh(direction)
    return direction


@router.delete("/directions/{direction_id}", status_code=204)
async def delete_direction(
    direction_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    """Удаление направления вместе с привязанными продуктами."""
    direction = await db.get(ITDirection, direction_id)
    if direction is None:
        raise HTTPException(status_code=404, detail="Направление не найдено")

    product_ids = await db.scalars(
        select(ITProduct.id).where(ITProduct.direction_id == direction_id)
    )
    ids = list(product_ids)
    if ids:
        # отвязываем взаимодействия, чтобы не нарушить ссылочную целостность
        await db.execute(
            Interaction.__table__.update()
            .where(Interaction.product_id.in_(ids))
            .values(product_id=None)
        )
        await db.execute(ITProduct.__table__.delete().where(ITProduct.id.in_(ids)))
    await db.delete(direction)
    await db.commit()


# ---------- Продукты ----------
@router.get("/products", response_model=list[ITProductRead])
async def list_products(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ITProductRead]:
    stmt = (
        select(ITProduct, ITDirection.name.label("direction_name"))
        .outerjoin(ITDirection, ITProduct.direction_id == ITDirection.id)
        .order_by(ITProduct.name)
    )
    rows = (await db.execute(stmt)).all()
    return [
        ITProductRead(
            id=product.id,
            name=product.name,
            direction_id=product.direction_id,
            direction_name=direction_name,
        )
        for product, direction_name in rows
    ]


@router.post("/products", response_model=ITProductRead, status_code=201)
async def create_product(
    payload: ITProductCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ITProductRead:
    exists = await db.scalar(
        select(ITProduct.id).where(ITProduct.name == payload.name)
    )
    if exists:
        raise HTTPException(
            status_code=409, detail="Такой продукт уже есть в справочнике"
        )
    if payload.direction_id is not None:
        if await db.get(ITDirection, payload.direction_id) is None:
            raise HTTPException(status_code=404, detail="Направление не найдено")

    product = ITProduct(**payload.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)

    direction_name = None
    if product.direction_id:
        direction = await db.get(ITDirection, product.direction_id)
        direction_name = direction.name if direction else None
    return ITProductRead(
        id=product.id,
        name=product.name,
        direction_id=product.direction_id,
        direction_name=direction_name,
    )


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    product = await db.get(ITProduct, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    await db.execute(
        Interaction.__table__.update()
        .where(Interaction.product_id == product_id)
        .values(product_id=None)
    )
    await db.delete(product)
    await db.commit()
