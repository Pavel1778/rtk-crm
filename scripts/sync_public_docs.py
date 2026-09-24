"""Собирает статические копии документации для вкладки «Помощь».

Запуск из корня репозитория:

    python scripts/sync_public_docs.py

Вкладка «Помощь» отдаёт Markdown как статику из `frontend/public/docs/`,
поэтому копии нужно держать в актуальном состоянии относительно `docs/`.
Скрипт пересобирает зеркало детерминированно: копирует исходники, сохраняя
относительную структуру, и переписывает ссылки на картинки и внутренние
Markdown-ссылки в абсолютные (`/docs/...`). Страница рендерится по маршруту
`/help`, поэтому относительные пути оттуда не разрешаются.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import ROOT  # noqa: E402

DOCS_SOURCE = ROOT / "docs"
DOCS_OUTPUT = ROOT / "frontend" / "public" / "docs"

# Markdown-документы, попадающие в зеркало (путь от корня `docs/`).
MARKDOWN_FILES = [
    "USER_GUIDE.md",
    "ADMIN_GUIDE.md",
    "SECURITY.md",
    "STACK.md",
    "architecture/ARCHITECTURE.md",
    "architecture/README.md",
    "architecture/c4-context.md",
    "architecture/c4-components.md",
    "architecture/functional.md",
    "architecture/er-model.md",
    "architecture/deployment-current.md",
    "architecture/deployment-yandex-cloud.md",
    "security/SAST-SCA.md",
]

ASSET_DIRS = ["images"]

# Дополнительная копия в корне зеркала: HelpPage грузит `/docs/ARCHITECTURE.md`.
ROOT_ARCHITECTURE = "architecture/ARCHITECTURE.md"

# `[текст](цель)` без абсолютных URL, якорей и mailto.
_LINK = re.compile(r"\]\((?!https?:|/|#|mailto:)([^)]+)\)")


def _resolve(source_rel: str, target: str) -> str | None:
    """Абсолютный путь `/docs/...` для относительной ссылки внутри зеркала."""
    candidate = (Path(source_rel).parent / target).as_posix()
    parts: list[str] = []
    for part in candidate.split("/"):
        if part == "..":
            if not parts:
                return None
            parts.pop()
        elif part not in ("", "."):
            parts.append(part)
    return "/docs/" + "/".join(parts)


def _rewrite(markdown: str, source_rel: str) -> str:
    def repl(match: re.Match[str]) -> str:
        resolved = _resolve(source_rel, match.group(1))
        return f"]({resolved})" if resolved else match.group(0)

    return _LINK.sub(repl, markdown)


def main() -> int:
    if not DOCS_SOURCE.is_dir():
        print(f"Нет каталога {DOCS_SOURCE}")
        return 1

    for name in MARKDOWN_FILES:
        source = DOCS_SOURCE / name
        if not source.exists():
            print(f"Пропуск: нет файла {source}")
            return 1
        target = DOCS_OUTPUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        body = source.read_text(encoding="utf-8")
        target.write_text(_rewrite(body, name), encoding="utf-8")

    root_target = DOCS_OUTPUT / "ARCHITECTURE.md"
    root_target.write_text(
        _rewrite((DOCS_SOURCE / ROOT_ARCHITECTURE).read_text(encoding="utf-8"), ROOT_ARCHITECTURE),
        encoding="utf-8",
    )

    for name in ASSET_DIRS:
        target = DOCS_OUTPUT / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(DOCS_SOURCE / name, target)

    print(f"Синхронизировано {len(MARKDOWN_FILES)} файлов + корневой ARCHITECTURE.md")
    print(f"Статика: {', '.join(ASSET_DIRS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
