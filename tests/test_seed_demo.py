"""Идемпотентность и полнота демо-данных.

Демо-сид вызывается при старте приложения. База может быть заполнена
частично (например, справочники уже есть, а продукты ещё нет — так бывает
после прерванного сида или при `SEED_DEMO_DATA=true` на существующей БД),
поэтому сид обязан дозаполнять недостающее и не падать.
"""

from __future__ import annotations

import pytest
from app.db.base import Base
from app.db.session import engine
from app.models.entities import Interaction, ITProduct, University
from app.seed import _seed_demo_interactions, seed_demo
from sqlalchemy import func, select


@pytest.fixture
async def clean_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def test_seed_demo_fills_products_and_interactions(clean_db) -> None:
    """Полный сид пустой базы создаёт продукты и карточки."""
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        created = await seed_demo(session)
        assert created is True

        products = await session.scalar(select(func.count(ITProduct.id)))
        interactions = await session.scalar(select(func.count(Interaction.id)))
        universities = await session.scalar(select(func.count(University.id)))

    assert products > 0, "демо-сид должен создать ИТ-продукты"
    assert universities > 0, "демо-сид должен создать вузы"
    assert interactions > 0, "демо-сид должен создать карточки взаимодействий"


async def test_seed_demo_is_idempotent(clean_db) -> None:
    """Повторный сид ничего не дублирует и не падает."""
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        await seed_demo(session)
        first_products = await session.scalar(select(func.count(ITProduct.id)))
        first_interactions = await session.scalar(select(func.count(Interaction.id)))

    async with SessionLocal() as session:
        await seed_demo(session)
        second_products = await session.scalar(select(func.count(ITProduct.id)))
        second_interactions = await session.scalar(select(func.count(Interaction.id)))

    assert first_products == second_products
    assert first_interactions == second_interactions


async def test_demo_interactions_recover_when_products_missing(clean_db) -> None:
    """Частично заполненная база: справочники есть, продукты — нет.

    Регрессия: `_seed_demo_interactions` падал с IndexError, потому что
    брал продукт по индексу из пустого списка.
    """
    from app.db.session import SessionLocal
    from app.seed import seed_reference

    async with SessionLocal() as session:
        await seed_reference(session)
        # Имитируем частичное состояние: продукты не созданы.
        for product in await session.scalars(select(ITProduct)):
            await session.delete(product)
        await session.commit()

    async with SessionLocal() as session:
        created = await _seed_demo_interactions(session)
        await session.commit()
        assert created is True
        interactions = await session.scalar(select(func.count(Interaction.id)))
        assert interactions > 0
