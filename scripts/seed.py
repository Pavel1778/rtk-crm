"""Заполнение справочников и демо-данных из командной строки.

Обёртка над `backend.seed`, чтобы запускать seed из скриптов и CI без
поднятия веб-сервера:

    python scripts/seed.py            # справочники + демо-карточки
    python scripts/seed.py --reference  # только справочники

Скрипт идемпотентен: повторный запуск не создаёт дубликатов. Демо-данные
обезличены (публичные вузы, вымышленные контактные лица и учётные записи
`admin@rtk.ru` / `manager@rtk.ru` / `kam@rtk.ru`).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import ensure_app_importable  # noqa: E402

ensure_app_importable()

from app.db.session import SessionLocal, create_tables  # noqa: E402
from app.seed import seed_demo, seed_reference  # noqa: E402
from loguru import logger  # noqa: E402


async def _run(reference_only: bool) -> None:
    await create_tables()
    async with SessionLocal() as session:
        created = (
            await seed_reference(session)
            if reference_only
            else await seed_demo(session)
        )
    logger.info(
        "Seed завершён: {}",
        "данные созданы" if created else "данные уже присутствуют",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed RTK CRM")
    parser.add_argument(
        "--reference",
        action="store_true",
        help="заполнить только справочники, без демо-карточек",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.reference))


if __name__ == "__main__":
    main()
