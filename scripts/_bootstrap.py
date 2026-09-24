"""Делает пакет `app` импортируемым при запуске скриптов из корня репозитория.

Приложение в контейнере живёт как пакет `app` (см. `backend/Dockerfile`),
а в репозитории исходники лежат в `backend/`. Скрипты запускаются из корня,
поэтому создаём временный каталог-алиас `app -> backend` и добавляем его в
`sys.path`. Тот же приём использует `conftest.py` для тестов.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"


def ensure_app_importable() -> None:
    """Добавляет в `sys.path` каталог с ссылкой `app -> backend`."""
    alias_dir = Path(tempfile.mkdtemp(prefix="rtk-app-alias-"))
    alias_path = alias_dir / "app"
    if not alias_path.exists():
        alias_path.symlink_to(BACKEND_DIR, target_is_directory=True)
    sys.path.insert(0, str(alias_dir))
