"""Локальный запуск backend с автоперезагрузкой.

Приложение живёт как пакет `app` (в контейнере — `/app`, в репозитории —
`backend/`), поэтому `uvicorn backend.main:app` из корня не работает:
`backend/main.py` импортирует `app.*`. Скрипт делает `app` импортируемым тем
же приёмом, что `conftest.py` и `scripts/_bootstrap.py`, и поднимает uvicorn.

    python scripts/run_dev.py [--port 8000]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import ensure_app_importable  # noqa: E402

ensure_app_importable()

import uvicorn  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Запуск RTK CRM backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
    )


if __name__ == "__main__":
    main()
