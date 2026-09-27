"""Проверяет вёрстку презентации по фактическому рендеру.

Скрипт конвертирует `docs/presentation/RTK-CRM-LCT2026.pptx` в PDF через
LibreOffice, затем ищет реальные дефекты вёрстки: текст за границей слайда и
наложение текстовых блоков друг на друга. Если LibreOffice или pymupdf
недоступны, скрипт сообщает об этом и завершается успешно, чтобы не ломать CI
на окружении без офисного пакета.

Запуск: python scripts/check_presentation_layout.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PPTX = ROOT / "docs" / "presentation" / "RTK-CRM-LCT2026.pptx"
# Допуск в пунктах: тонкие различия в метриках шрифтов не считаем дефектом.
TOL = 2.0


def render_pdf(workdir: Path) -> Path | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("LibreOffice не найден — проверка вёрстки пропущена.")
        return None
    proc = subprocess.run(
        [
            soffice,
            "--headless",
            "--norestore",
            f"-env:UserInstallation=file://{workdir / 'profile'}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(workdir),
            str(PPTX),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    pdf = workdir / (PPTX.stem + ".pdf")
    if proc.returncode != 0 or not pdf.exists():
        print("Не удалось конвертировать презентацию:", proc.stderr.strip())
        return None
    return pdf


def analyze(pdf: Path) -> int:
    try:
        import pymupdf
    except ImportError:
        print("pymupdf не установлен — проверка вёрстки пропущена.")
        return 0

    doc = pymupdf.open(str(pdf))
    problems = 0
    print(f"Слайдов: {len(doc)}")
    for index in range(len(doc)):
        page = doc[index]
        number = index + 1
        width, height = page.rect.width, page.rect.height
        blocks = [
            b for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()
        ]
        for x0, y0, x1, y1, text, *_ in blocks:
            if x0 < -TOL or y0 < -TOL or x1 > width + TOL or y1 > height + TOL:
                print(
                    f"  Слайд {number}: текст за границей "
                    f"[{x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}] {text.strip()[:50]!r}"
                )
                problems += 1
        for i in range(len(blocks)):
            for j in range(i + 1, len(blocks)):
                a, b = blocks[i], blocks[j]
                overlap_x = min(a[2], b[2]) - max(a[0], b[0])
                overlap_y = min(a[3], b[3]) - max(a[1], b[1])
                if overlap_x > TOL and overlap_y > TOL:
                    print(
                        f"  Слайд {number}: наложение "
                        f"{a[4].strip()[:30]!r} / {b[4].strip()[:30]!r}"
                    )
                    problems += 1
        print(
            f"  Слайд {number}: блоков текста {len(blocks)}, "
            f"размер {width:.0f}x{height:.0f}"
        )
    print(f"Итого дефектов вёрстки: {problems}")
    return 1 if problems else 0


def main() -> int:
    if not PPTX.exists():
        print(f"Нет файла презентации: {PPTX}")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        pdf = render_pdf(Path(tmp))
        if pdf is None:
            return 0
        return analyze(pdf)


if __name__ == "__main__":
    sys.exit(main())
