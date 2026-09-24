"""Проверка локального запуска backend.

Приложение импортируется как пакет `app` (в репозитории — через алиас
`app -> backend`), поэтому `uvicorn backend.main:app` из корня не работает.
Тест фиксирует, что `scripts/run_dev.py` делает `app` импортируемым.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_DEV = REPO_ROOT / "scripts" / "run_dev.py"


def test_run_dev_script_exists() -> None:
    assert RUN_DEV.is_file(), "должен быть скрипт локального запуска"


def test_run_dev_makes_app_importable() -> None:
    """`app.main` импортируется после bootstrap-алиаса."""
    code = (
        "import sys;"
        f"sys.path.insert(0, {str(REPO_ROOT / 'scripts')!r});"
        "from _bootstrap import ensure_app_importable;"
        "ensure_app_importable();"
        "import app.main;"
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_start_sh_imports_app_package() -> None:
    """`start.sh` не должен использовать несуществующий пакет `backend.*`."""
    script = (REPO_ROOT / "backend" / "start.sh").read_text(encoding="utf-8")
    assert "backend.main" not in script
    assert "from backend." not in script
    assert "app.main:app" in script
    assert "app.db.session" in script


def test_start_sh_resolves_app_alias() -> None:
    """`start.sh` делает `app` импортируемым через ссылку на backend/."""
    script = (REPO_ROOT / "backend" / "start.sh").read_text(encoding="utf-8")
    assert "ln -sfn" in script and "app" in script
    assert "PYTHONPATH" in script
