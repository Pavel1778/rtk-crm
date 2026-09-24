"""Собирает PDF-версии руководств для вкладки «Помощь».

Запуск из корня репозитория:

    python scripts/render_guide_pdfs.py

Скрипт читает Markdown из `docs/`, подставляет картинки из `docs/images/`
и кладёт готовые файлы в `frontend/public/docs/`, откуда их отдаёт
статический сервер вместе с самими `.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import ROOT, ensure_app_importable  # noqa: E402

ensure_app_importable()

from app.services.guide_pdf import render_guide_pdf  # noqa: E402

DOCS_SOURCE = ROOT / "docs"
DOCS_OUTPUT = ROOT / "frontend" / "public" / "docs"

GUIDES = {
    "USER_GUIDE.md": ("RTK CRM — руководство пользователя", "user-guide.pdf"),
    "ADMIN_GUIDE.md": ("RTK CRM — руководство администратора", "admin-guide.pdf"),
}


def main() -> int:
    DOCS_OUTPUT.mkdir(parents=True, exist_ok=True)
    for source_name, (title, target_name) in GUIDES.items():
        source = DOCS_SOURCE / source_name
        if not source.exists():
            print(f"Пропуск: нет файла {source}")
            return 1
        stream = render_guide_pdf(
            source.read_text(encoding="utf-8"),
            title=title,
            base_dir=DOCS_SOURCE,
        )
        target = DOCS_OUTPUT / target_name
        target.write_bytes(stream.getvalue())
        print(f"{source_name} -> {target.relative_to(ROOT)} ({target.stat().st_size} Б)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
