"""Загрузка справочников и демо-данных. Идемпотентна: при данных пропускается."""

from app.auth.security import hash_password
from app.models.entities import (
    Action,
    Comment,
    Interaction,
    ITDirection,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from app.models.enums import B2C_STAGES, UserRole, WorkflowScope
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# 14 этапов воркфлоу по ТЗ (код, название, цвет колонки канбан-доски).
# Порядок списка = порядок этапов 1..14.
WORKFLOW_STAGES: list[tuple[str, str, str]] = [
    ("contact_search", "Поиск контактов ответственного в вузе", "#8c8c8c"),
    ("communication", "Коммуникация и уточнение актуальности программ", "#1677ff"),
    ("meeting", "Организация встречи с представителями вуза", "#13c2c2"),
    ("document_exchange", "Обмен пакетом документов для подписания", "#2f54eb"),
    ("document_revision", "Корректировка документов перед подписанием", "#722ed1"),
    ("document_signing", "Подписание документов", "#eb2f96"),
    ("materials_transfer", "Передача материалов, лицензии и документации", "#f5222d"),
    ("implementation", "Сопровождение внедрения ИТ-продуктов", "#fa8c16"),
    ("teacher_training", "Обучение преподавателей", "#faad14"),
    ("program_update", "Актуализация учебной программы", "#a0d911"),
    ("classes", "Ведение занятий", "#52c41a"),
    ("documentation_update", "Актуализация документации по продукту", "#389e0d"),
    ("qualification_upgrade", "Повышение квалификации преподавателей", "#237804"),
    ("stage_control", "Контроль за исполнением каждого этапа", "#08979c"),
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

DEMO_USERS: list[tuple[str, str, str, UserRole]] = [
    ("admin@rtk.ru", "Администратор РТК", "admin123", UserRole.ADMIN),
    ("manager@rtk.ru", "Менеджер РТК", "manager123", UserRole.MANAGER),
    ("kam@rtk.ru", "КАМ РТК", "kam123", UserRole.USER),
]



async def seed_reference(session: AsyncSession) -> bool:
    """Заполняет только справочники (этапы, пользователи, направления, продукты).

    Идемпотентна: существующие данные пропускаются. Используется при старте
    на Render, где демо-карточки не нужны.
    """
    created_any = False
    created_any |= await _seed_stages(session)
    created_any |= await _seed_users(session)
    created_any |= await _seed_directories(session)
    if created_any:
        await session.commit()
    return created_any


async def seed_demo(session: AsyncSession) -> bool:
    """Заполняет пустую базу целиком. Возвращает True, если что-то создано."""
    created_any = await seed_reference(session)
    if await _seed_demo_interactions(session):
        await session.commit()
        created_any = True
    return created_any


async def _seed_stages(session: AsyncSession) -> bool:
    """Дозаполняет отсутствующие этапы, не трогая уже созданные.

    Сравнение по (scope, код): базу, созданную в 13-этапной версии, можно
    дополнить недостающими этапами. Порядок существующих этапов не меняется,
    чтобы не ломать уже расставленные карточки. B2B-набор — 14 этапов ТЗ,
    B2C-набор — упрощённая воронка (заявка → оплата → обучение → завершено).
    """
    created = False
    existing = {
        (row.scope, row.code)
        for row in await session.scalars(select(WorkflowStageRef))
    }

    for scope, stage_set in (
        (WorkflowScope.B2B, WORKFLOW_STAGES),
        (WorkflowScope.B2C, B2C_STAGES),
    ):
        max_order = await session.scalar(
            select(func.max(WorkflowStageRef.order)).where(
                WorkflowStageRef.scope == scope
            )
        ) or 0
        for order_in_set, (code, name, color) in enumerate(stage_set, start=1):
            if (scope, code) in existing:
                continue
            # Сохраняем исходную нумерацию набора, если порядок свободен,
            # иначе продолжаем с максимального (защита от unique-конфликта).
            order = order_in_set if order_in_set > max_order else max_order + 1
            max_order = max(max_order, order)
            session.add(
                WorkflowStageRef(
                    code=code, name=name, order=order, color=color, scope=scope
                )
            )
            created = True
    return created


async def _seed_users(session: AsyncSession) -> bool:
    existing = await session.scalar(
        select(func.count(User.id)).where(User.email == DEMO_USERS[0][0])
    )
    if existing:
        return False
    for email, full_name, password, role in DEMO_USERS:
        session.add(
            User(
                email=email,
                full_name=full_name,
                role=role,
                # Флаг is_admin оставлен синхронно с ролью: часть проверок
                # в коде опирается на него.
                is_admin=role == UserRole.ADMIN,
                hashed_password=hash_password(password),
            )
        )

    return True


async def _seed_directories(session: AsyncSession) -> bool:
    """Дозаполняет направления и продукты независимо друг от друга.

    Справочники сидятся раздельно: база может содержать направления без
    продуктов (прерванный сид, ручное удаление продуктов). Привязка к первому
    направлению в этом случае заблокировала бы создание продуктов.
    """
    created = False

    existing_directions = set(await session.scalars(select(ITDirection.name)))
    for name in DIRECTIONS:
        if name not in existing_directions:
            session.add(ITDirection(name=name))
            created = True
    if created:
        await session.flush()

    directions = {
        d.name: d.id
        for d in await session.scalars(select(ITDirection))
    }

    existing_products = set(await session.scalars(select(ITProduct.name)))
    for name, direction_name in PRODUCTS:
        if name in existing_products:
            continue
        session.add(
            ITProduct(name=name, direction_id=directions.get(direction_name))
        )
        created = True
    return created


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
    # Ответственный КАМ назначается демо-пользователем с ролью user,
    # чтобы на доске было видно эффект фильтрации по роли.
    kam = await session.scalar(select(User).where(User.role == UserRole.USER))


    # карточки: (индекс вуза, индекс продукта, код этапа, номер договора)

    demo_cards: list[tuple[int, int | None, str, str | None]] = [
        (0, 0, "contact_search", None),
        (1, 1, "meeting", None),
        (2, 2, "document_signing", "РТК-2026-001"),
        (3, 3, "materials_transfer", "РТК-2026-002"),
        (4, 4, "implementation", "РТК-2026-003"),
        (0, 2, "teacher_training", "РТК-2026-004"),
        (1, 3, "stage_control", "РТК-2025-114"),
    ]
    for university_idx, product_idx, stage_code, contract in demo_cards:
        # Индексы зашиты в демо-карточках: при неполном справочнике продукт
        # может отсутствовать, поэтому берём его безопасно, а не по индексу.
        product = (
            products[product_idx]
            if product_idx is not None and 0 <= product_idx < len(products)
            else None
        )
        session.add(
            Interaction(
                university_id=universities[university_idx].id,
                product_id=product.id if product else None,
                stage_id=stages[stage_code].id,
                contract_number=contract,
                university_specialist=universities[university_idx].contact_person,
                assigned_kam_id=kam.id if kam else None,

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
