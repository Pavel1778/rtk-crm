"""Общая настройка pytest.

Приложение импортируется как пакет `app` (см. backend/Dockerfile), тогда как
тесты лежат в репозитории рядом с каталогом `backend`. Чтобы оба варианта
импорта работали, создаём временный каталог с ссылкой `app -> backend` и
добавляем его в sys.path.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"

# Тесты работают на локальном SQLite: не требуем Supabase/Postgres.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SEED_DEMO_DATA", "false")

# Загруженные в тестах файлы не должны попадать в рабочее дерево.
os.environ.setdefault(
    "UPLOAD_DIR", tempfile.mkdtemp(prefix="rtk-test-uploads-")
)

_alias_dir = Path(tempfile.mkdtemp(prefix="rtk-app-alias-"))
_alias_path = _alias_dir / "app"
if not _alias_path.exists():
    _alias_path.symlink_to(BACKEND_DIR, target_is_directory=True)

if str(_alias_dir) not in sys.path:
    sys.path.insert(0, str(_alias_dir))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
