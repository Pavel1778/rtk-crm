import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.database import Base
from app.models.university import University
from app.models.workflow import WorkflowStage

DATABASE_URL = "postgresql+asyncpg://rtk_user:rtk_password@localhost:5432/rtk_crm"

WORKFLOW_STAGES = [
    "1. Поиск контактов ответственного в вузе",
    "2. Коммуникация и уточнение актуальности программ",
    "3. Организация встречи с представителями вуза",
    "4. Обмен необходимым пакетом документов для подписания",
    "5. Корректировка документов перед подписанием",
    "6. Подписание документов",
    "7. Передача обучающих материалов, лицензии и документации",
    "8. Сопровождение внедрения ИТ-продуктов в вузе",
    "9. Обучение преподавателей",
    "10. Актуализация учебной программы",
    "11. Ведение занятий",
    "12. Актуализация документации по продукту и материалам",
    "13. Повышение квалификации преподавателей",
    "14. Контроль за исполнением каждого этапа",
]

UNIVERSITIES = [
    ("МГУ им. М.В. Ломоносова", "Ростелеком", "DevOps", "РТК-2026-001", True, 2027, "Внедрение", "Иванов И.И.", "Петров П.П.", "Договор на согласовании"),
    ("СПбГУ", "Ростелеком", "Python", "РТК-2026-002", True, 2026, "Обучение", "Сидоров С.С.", "Смирнова А.А.", "Преподаватели обучены"),
    ("МФТИ", "Ростелеком", "QA Engineering", "РТК-2026-003", False, 2027, "Поиск контактов", "Иванов И.И.", "Кузнецов В.В.", "Ждем ответа"),
    ("НИУ ВШЭ", "Ростелеком", "Data Science", "РТК-2026-004", True, 2026, "Подписание", "Петрова А.А.", "Волков Д.Д.", "Финальная версия"),
    ("ИТМО", "Ростелеком", "Cybersecurity", "РТК-2026-005", True, 2028, "Ведение занятий", "Сидоров С.С.", "Зайцев Е.Е.", "Группа набрана"),
]


async def seed():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        for order, name in enumerate(WORKFLOW_STAGES, 1):
            stage = WorkflowStage(name=name, order=order, is_active=True, description=f"Этап {order}")
            session.add(stage)
        await session.commit()
        result = await session.execute(select(WorkflowStage))
        stages = result.scalars().all()
        for data in UNIVERSITIES:
            uni = University(
                name=data[0], vendor=data[1], product=data[2], contract_number=data[3],
                license_signed=data[4], license_expiry_year=data[5], status=data[6],
                manager_name=data[7], university_responsible=data[8], comment=data[9],
                current_workflow_stage_id=stages[data[5] % 14].id if stages else None,
            )
            session.add(uni)
        await session.commit()
        print(f"✅ Добавлено {len(WORKFLOW_STAGES)} этапов и {len(UNIVERSITIES)} вузов")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
