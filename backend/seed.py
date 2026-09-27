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
    # Продукты вендоров из каталога кейсодержателя идут отдельным
    # направлением: это партнёрские решения, а не продукты РТК.
    "Партнёрские продукты вендоров",
]

PRODUCTS: list[tuple[str, str | None]] = [
    ("RUBOTYAKA", "Информационная безопасность"),
    ("RUBTSC", "Информационная безопасность"),
    ("Skill Portal", "Разработка ПО"),
    ("Cyber Range", "Информационная безопасность"),
    ("AI Studio", "Искусственный интеллект"),
]

# Продукты из «Вендоры.xlsx» (каталог кейсодержателя). Контакты вендоров в
# справочник не переносятся: ИТ-продукт хранит только название и направление,
# а телефоны и почты вендоров в демо-данных не нужны.
VENDOR_PRODUCTS: list[str] = [
    "Базис Dynamix",
    "RT.DataLake",
    "RT.Warehouse",
    "RT.DataVision",
    "AKOLA",
    "Яга",
    "Web3Gate",
    "Аврора SDK",
    "Нейрошлюз",
]

VENDOR_DIRECTION = "Партнёрские продукты вендоров"

UNIVERSITIES: list[tuple[str, str, str]] = [
    ("МГТУ им. Н. Э. Баумана", "Москва", "Иванов И. И."),
    ("ИТМО", "Санкт-Петербург", "Петров П. П."),
    ("Университет ИТЭГ", "Казань", "Сидоров С. С."),
    ("МГУ им. М. В. Ломоносова", "Москва", "Кузнецова А. А."),
    ("НГУ", "Новосибирск", "Смирнова Е. В."),
]

# Курсы B2C из «Данные оплат.json» (выгрузка заявок кейсодержателя).
# Переносятся только названия курсов и этапы воронки: ФИО, телефоны и адреса
# почты заявителей в демо-данные не попадают, вместо них — синтетические
# записи «Физлицо N». Так демонстрируется B2C-воронка без персональных данных.
B2C_COURSES: list[tuple[str, str]] = [
    ("Анализ данных без программирования", "b2c_request"),
    ("Инженер-тестировщик", "b2c_request"),
    (
        "Управление ИТ-проектами на базе программного продукта "
        "ПАО «Ростелеком»",
        "b2c_payment",
    ),
    ("Промпт-инжиниринг", "b2c_training"),
    ("Python-разработчик с использованием инструментов ИИ", "b2c_completed"),
]

# Демо-карточки B2B: (вуз, продукт, код этапа, номер договора). Ссылки по
# именам, а не по индексам, чтобы сид переживал частичное заполнение базы.
# По 2 карточки на вуз — это предел правила «не более 2 активных
# взаимодействий на вуз»; 10 разных этапов из 14 заняты.
B2B_CARDS: list[tuple[str, str, str, str | None]] = [
    ("МГТУ им. Н. Э. Баумана", "RUBOTYAKA", "contact_search", None),
    ("МГТУ им. Н. Э. Баумана", "Cyber Range", "communication", None),
    ("ИТМО", "RUBTSC", "meeting", None),
    ("ИТМО", "Skill Portal", "document_exchange", "РТК-2026-001"),
    ("Университет ИТЭГ", "AI Studio", "document_signing", "РТК-2026-002"),
    ("Университет ИТЭГ", "Базис Dynamix", "materials_transfer", "РТК-2026-003"),
    ("МГУ им. М. В. Ломоносова", "RT.DataLake", "implementation", "РТК-2026-004"),
    ("МГУ им. М. В. Ломоносова", "AKOLA", "teacher_training", "РТК-2026-005"),
    ("НГУ", "Яга", "program_update", None),
    ("НГУ", "Web3Gate", "stage_control", None),
]

# Задачи для демо-карточек: (код этапа карточки, текст, выполнена).
DEMO_ACTIONS: list[tuple[str, str, bool]] = [
    ("contact_search", "Уточнить контакт ответственного за ИТ-программы", False),
    ("communication", "Согласовать дату встречи с представителями вуза", False),
    ("document_exchange", "Отправить пакет документов на согласование", False),
    ("implementation", "Запланировать обучение преподавателей", False),
    ("meeting", "Зафиксировать протокол встречи", True),
    ("document_signing", "Загрузить подписанный договор", True),
    ("teacher_training", "Подтвердить состав группы преподавателей", True),
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

    # Продукты вендоров из каталога кейсодержателя. Направление
    # фиксированное, поэтому отдельного сопоставления не требуется.
    for name in VENDOR_PRODUCTS:
        if name in existing_products:
            continue
        session.add(
            ITProduct(name=name, direction_id=directions.get(VENDOR_DIRECTION))
        )
        created = True
    return created


async def _seed_demo_interactions(session: AsyncSession) -> bool:
    """Демо-взаимодействия, задачи и комментарии.

    Дозаполняет карточки, которых ещё нет: сравнение идёт по (вуз, продукт).
    Раньше функция выходила сразу при наличии хотя бы одной карточки,
    поэтому база, засеянная до появления B2C-воронки, навсегда оставалась без
    B2C-карточек. Теперь оба набора досоздаются независимо.
    """
    universities = {u.name: u for u in await session.scalars(select(University))}
    for name, city, contact in UNIVERSITIES:
        if name not in universities:
            universities[name] = University(
                name=name, city=city, contact_person=contact
            )
            session.add(universities[name])
    await session.flush()

    products = {p.name: p for p in await session.scalars(select(ITProduct))}
    # Ответственный КАМ назначается демо-пользователем с ролью user,
    # чтобы на доске было видно эффект фильтрации по роли.
    kam = await session.scalar(select(User).where(User.role == UserRole.USER))
    stages = {s.code: s for s in await session.scalars(select(WorkflowStageRef))}

    # Карточка опознаётся парой (вуз, продукт): этап не входит в ключ, иначе
    # после перетаскивания карточки на другой этап рестарт создавал бы дубль.
    existing: set[tuple[str, str | None]] = {
        (university_name, product_name)
        for university_name, product_name in await session.execute(
            select(University.name, ITProduct.name)
            .select_from(Interaction)
            .join(University, Interaction.university_id == University.id)
            .join(
                ITProduct,
                Interaction.product_id == ITProduct.id,
                isouter=True,
            )
        )
    }

    created = False

    def _add(
        university_name: str,
        product_name: str | None,
        stage_code: str,
        *,
        scope: WorkflowScope = WorkflowScope.B2B,
        contract: str | None = None,
        notes: str | None = None,
    ) -> Interaction | None:
        nonlocal created
        if stage_code not in stages:
            return None
        key = (university_name, product_name)
        if key in existing:
            return None
        university = universities[university_name]
        product = products.get(product_name) if product_name else None
        interaction = Interaction(
            university_id=university.id,
            product_id=product.id if product else None,
            stage_id=stages[stage_code].id,
            scope=scope,
            contract_number=contract,
            notes=notes,
            university_specialist=university.contact_person,
            assigned_kam_id=kam.id if kam else None,
        )
        session.add(interaction)
        existing.add(key)
        created = True
        return interaction

    for university_name, product_name, stage_code, contract in B2B_CARDS:
        _add(university_name, product_name, stage_code, contract=contract)

    # B2C-воронка: заявки физлиц на курсы. Заявитель хранится как «Физлицо N»
    # (без ФИО, телефона и почты), название курса — в заметке карточки.
    # Так на доске видно обе воронки, но персональные данные не попадают в базу.
    for index, (course, stage_code) in enumerate(B2C_COURSES, start=1):
        client_name = f"Физлицо {index}"
        if client_name not in universities:
            universities[client_name] = University(
                name=client_name, city=None, contact_person=None
            )
            session.add(universities[client_name])
            await session.flush()
        _add(
            client_name,
            None,
            stage_code,
            scope=WorkflowScope.B2C,
            notes=f"Курс: {course}",
        )

    await session.flush()

    # Задачи и комментарии добавляем карточкам, у которых их ещё нет.
    cards = list(
        await session.scalars(
            select(Interaction).order_by(Interaction.id)
        )
    )
    if not cards:
        return False
    code_by_id = {stage.id: code for code, stage in stages.items()}
    busy_ids = set(await session.scalars(select(Action.interaction_id)))
    cards_by_stage: dict[str, list[Interaction]] = {}
    for card in cards:
        cards_by_stage.setdefault(code_by_id[card.stage_id], []).append(card)
    for stage_code, title, completed in DEMO_ACTIONS:
        card = next(
            (
                c
                for c in cards_by_stage.get(stage_code, [])
                if c.id not in busy_ids
            ),
            None,
        )
        if card is None:
            continue
        busy_ids.add(card.id)
        session.add(
            Action(
                interaction_id=card.id,
                title=title,
                due_date="2026-10-15",
                is_completed=completed,
            )
        )
        created = True
    first = cards[0]
    has_comment = await session.scalar(
        select(func.count(Comment.id)).where(Comment.interaction_id == first.id)
    )
    if not has_comment:
        session.add(
            Comment(
                interaction_id=first.id,
                text="Первый контакт установлен, ждём обратную связь от проректора.",
            )
        )
        created = True
    return created
