"""Дублирует конфиг колонок отчёта внутрь backend/.

Канонический источник — `config/report_columns.json` в корне репозитория (его
же отдаёт фронтенду `/api/reports/columns`). Но backend собирается с build
context `backend/` (Dockerfile, Render), поэтому корневой `config/` в образ не
попадает, и при импорте `app.services.report_columns` падал с
`FileNotFoundError` на `/config/report_columns.json`.

Чтобы конфиг был доступен в любом окружении, файл копируется в
`backend/config/report_columns.json`. Запуск из корня репозитория:

    python scripts/sync_report_columns.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import ROOT  # noqa: E402

SOURCE = ROOT / "config" / "report_columns.json"
DEST = ROOT / "backend" / "config" / "report_columns.json"


def main() -> int:
    if not SOURCE.is_file():
        print(f"Нет источника {SOURCE}")
        return 1

    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.is_file() and DEST.read_bytes() == SOURCE.read_bytes():
        print(f"Уже синхронизировано: {DEST.relative_to(ROOT)}")
        return 0

    shutil.copyfile(SOURCE, DEST)
    print(f"Скопировано: {SOURCE.relative_to(ROOT)} -> {DEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
