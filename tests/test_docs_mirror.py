"""Зеркало документации для вкладки «Помощь» не должно расходиться с `docs/`.

HelpPage отдаёт Markdown как статику из `frontend/public/docs/`, поэтому
файлы там обязаны совпадать с источниками из `docs/` (с учётом переписанных
ссылок). Тесты ловят дрейф: забытый `scripts/sync_public_docs.py` после
правки исходного документа, битые внутренние ссылки и отсутствующие картинки.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
MIRROR = REPO_ROOT / "frontend" / "public" / "docs"

_LINK = re.compile(r"\]\((?!https?:|/|#|mailto:)([^)]+)\)")


def _resolve(source_rel: str, target: str) -> str | None:
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


def test_sync_script_reproduces_mirror() -> None:
    """Повторный прогон синхронизации не меняет рабочее дерево."""
    before = {
        path: path.read_bytes() for path in MIRROR.rglob("*") if path.is_file()
    }
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "sync_public_docs.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    after = {
        path: path.read_bytes() for path in MIRROR.rglob("*") if path.is_file()
    }
    assert before == after, "Зеркало рассинхронизировано: запустите sync_public_docs.py"


def test_all_mirror_links_resolve() -> None:
    for page in MIRROR.rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        for match in re.finditer(r"\]\((/docs/[^)#]+)", text):
            target = MIRROR / match.group(1).removeprefix("/docs/")
            assert target.exists(), f"{page.name}: битая ссылка {match.group(1)}"


def test_mirror_markdown_has_no_relative_links() -> None:
    for page in MIRROR.rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        relative = _LINK.findall(text)
        assert not relative, f"{page.name}: остались относительные ссылки {relative}"


def test_help_pages_exist_in_mirror() -> None:
    for name in ("USER_GUIDE.md", "ADMIN_GUIDE.md", "SECURITY.md", "ARCHITECTURE.md"):
        assert (MIRROR / name).exists(), f"нет {name} для вкладки «Помощь»"


def test_images_referenced_by_guides_exist() -> None:
    for page in (MIRROR / "USER_GUIDE.md", MIRROR / "ADMIN_GUIDE.md"):
        text = page.read_text(encoding="utf-8")
        for match in re.finditer(r"\(/docs/images/([^)]+)\)", text):
            assert (MIRROR / "images" / match.group(1)).exists(), match.group(1)


def test_source_resolution_matches_script() -> None:
    assert _resolve("architecture/ARCHITECTURE.md", "../STACK.md") == "/docs/STACK.md"
    assert _resolve("USER_GUIDE.md", "images/01-login.png") == "/docs/images/01-login.png"
    assert _resolve("SECURITY.md", "security/SAST-SCA.md") == "/docs/security/SAST-SCA.md"
