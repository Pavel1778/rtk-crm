"""Извлекает Mermaid-исходник ER-диаграммы из `er-model.md`.

Держит `er.mmd` в синхроне с документом, чтобы диаграмма рендерилась в
PDF/PNG одной командой без ручного копирования.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import ROOT  # noqa: E402

ARCH = ROOT / "docs" / "architecture"
SOURCE = ARCH / "er-model.md"
TARGET = ARCH / "er.mmd"

_BLOCK = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def main() -> int:
    match = _BLOCK.search(SOURCE.read_text(encoding="utf-8"))
    if match is None:
        print(f"Нет Mermaid-блока в {SOURCE}")
        return 1
    body = match.group(1)
    if not body.endswith("\n"):
        body += "\n"
    TARGET.write_text(body, encoding="utf-8")
    print(f"Записано {TARGET.relative_to(ROOT)}: строк {body.count(chr(10))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
