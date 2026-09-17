"""Загрузка справочников и демо-данных. Идемпотентна: при данных пропускается."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import hash_password
from backend.models.entities import (
    Action,
    Comment,
    Interaction,
    ITDirection,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)

# 13 этапов воркфлоу: (код, название, цвет колонки канбан-доски)
WORKFLOW_STAGES: list[tuple[str, str, str]] = [
    ("lead", "Лиды", "#8c8c8c"),
    ("meeting", "Встреча", "#1677ff"),
    ("commercial_proposal", "КП", "#13c2c2"),
    ("contract", "Договор", "#2f54eb"),
    ("license", "Лицензия", "#722ed1"),
    ("implementation", "Внедрение", "#fa8c16"),
    ("academy", "Академия", "#eb2f96"),
    ("exams", "Экзамены", "#f5222d"),
    ("ranking", "Рейтинг", "#faad14"),
    ("grants", "Гранты", "#a0d911"),
    ("conference", "Конференция", "#52c41a"),
    ("extension", "Продление", "#389e0d"),
    ("done", "Завершено", "#237804"),
]

DIRECTIONS: list[str] = [
    "Информационная безопасность",
    "Разработка ПО",
    "Data Science",
    "Сетевые технологии",
    "Искусственный интеллект",
]

PRODUCTS: list[tuple[str, str | None]] = [
    ("RUBOTYAKA", "Информационная безопасность"),
    ("RUBTSC", "Информационная безопасность"),
    ("Skill Portal", "Разработка ПО"),
    ("Cyber Range", "Информационная безопасность"),
    ("AI Studio", "Искусственный интеллект"),
]

UNIVERSITIES: list[tuple[str, str, str]] = [
    ("МГТУ им. Н. Э. Баумана", "Москва", "Иванов И. И."),
    ("ИТМО", "Санкт-Петербург", "Петров П. П."),
    ("Университет ИТЭГ", "Казань", "Сидоров С. С."),
    ("МГУ им. М. В. Ломоносова", "Москва", "Кузнецова А. А."),
    ("НГУ", "Новосибирск", "Смирнова Е. В."),
]

DEMO_USERS: list[tuple[str, str, str, bool]] = [
    ("admin@rtk.ru", "Администратор РТК", "admin123", True),
    ("manager@rtk.ru", "Менеджер РТК", "manager123", False),
]


async def seed_demo(session: AsyncSession) -> bool:
    """Заполняет пустую базу. Возвращает True, если что-то создано."""
    created_any = False
    created_any |= await _seed_stages(session)
    created_any |= await _seed_users(session)
    created_any |= await _seed_directories(session)
    created_any |= await _seed_demo_interactions(session)
    if created_any:
        await session.commit()
    return created_any


async def _seed_stages(session: AsyncSession) -> bool:
    existing = await session.scalar(
        select(func.count(WorkflowStageRef.id)).where(
            WorkflowStageRef.code == WORKFLOW_STAGES[0][0]
        )
    )
    if existing:
        return False
    for order, (code, name, color) in enumerate(WORKFLOW_STAGES, start=1):
        session.add(
            WorkflowStageRef(code=code, name=name, order=order, color=color)
        )
    return True


async def _seed_users(session: AsyncSession) -> bool:
    existing = await session.scalar(
        select(func.count(User.id)).where(User.email == DEMO_USERS[0][0])
    )
    if existing:
        return False
    for email, full_name, password, is_admin in DEMO_USERS:
        session.add(
            User(
                email=email,
                full_name=full_name,
                is_admin=is_admin,
                hashed_password=hash_password(password),
            )
        )
    return True


async def _seed_directories(session: AsyncSession) -> bool:
    existing = await session.scalar(
        select(func.count(ITDirection.id)).where(ITDirection.name == DIRECTIONS[0])
    )
    if existing:
        return False

    for name in DIRECTIONS:
        session.add(ITDirection(name=name))
    await session.flush()

    directions = {
        d.name: d.id
        for d in await session.scalars(select(ITDirection))
    }
    for name, direction_name in PRODUCTS:
        session.add(
            ITProduct(name=name, direction_id=directions.get(direction_name))
        )
    return True


async def _seed_demo_interactions(session: AsyncSession) -> bool:
    """Демо-взаимодействия, задачи и комментарии (только для пустой базы)."""
    existing = await session.scalar(select(func.count(Interaction.id)))
    if existing:
        return False

    universities = list(await session.scalars(select(University).order_by(University.id)))
    if not universities:
        for name, city, contact in UNIVERSITIES:
            university = University(name=name, city=city, contact_person=contact)
            session.add(university)
            universities.append(university)
        await session.flush()

    products = list(await session.scalars(select(ITProduct).order_by(ITProduct.id)))
    stages = {
        s.code: s
        for s in await session.scalars(
            select(WorkflowStageRef).order_by(WorkflowStageRef.order)
        )
    }
    manager = await session.scalar(select(User).where(User.is_admin.is_(False)))

    # карточки: (индекс вуза, индекс продукта, код этапа, номер договора)
    demo_cards: list[tuple[int, int | None, str, str | None]] = [
        (0, 0, "lead", None),
        (1, 1, "meeting", None),
        (2, 2, "contract", "РТК-2026-001"),
        (3, 3, "license", "РТК-2026-002"),
        (4, 4, "implementation", "РТК-2026-003"),
        (0, 2, "academy", "РТК-2026-004"),
        (1, 3, "done", "РТК-2025-114"),
    ]
    for university_idx, product_idx, stage_code, contract in demo_cards:
        product = products[product_idx] if product_idx is not None else None
        session.add(
            Interaction(
                university_id=universities[university_idx].id,
                product_id=product.id if product else None,
                stage_id=stages[stage_code].id,
                contract_number=contract,
                university_specialist=universities[university_idx].contact_person,
            )
        )
    await session.flush()

    first = await session.scalar(
        select(Interaction).order_by(Interaction.id).limit(1)
    )
    if first is not None:
        session.add(
            Action(
                interaction_id=first.id,
                title="Согласовать дату встречи",
                due_date="2026-04-15",
            )
        )
        session.add(
            Comment(
                interaction_id=first.id,
                text="Первый контакт установлен, ждём обратную связь от проректора.",
            )
        )
    return True
