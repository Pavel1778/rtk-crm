"""Проверяет вёрстку презентации: переполнение, наложения, мелкий шрифт.

Скрипт конвертирует `docs/presentation/RTK-CRM-LCT2026.pptx` в PDF через
LibreOffice и анализирует фактический рендер: текст за границей слайда,
наложение текстовых блоков и кегль меньше порога. Отдельно проверяется, что
обязательные слайды ЛЦТ несут шрифт не мельче 14pt.

Если LibreOffice или pymupdf недоступны, скрипт сообщает об этом и
завершается успешно, чтобы не ломать CI на окружении без офисного пакета.

Запуск: python scripts/check_presentation_layout.py
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PPTX = ROOT / "docs" / "presentation" / "RTK-CRM-LCT2026.pptx"
# Допуск в пунктах: тонкие различия в метриках шрифтов не считаем дефектом.
TOL = 2.0
# Минимальный кегль для обязательных слайдов ЛЦТ (7-11).
MIN_FONT_PT = 14.0
# Номера слайдов-заглушек шаблона: их текст не является содержимым ответа.
TEMPLATE_STUB_PT = 12.0
# Обязательные слайды ЛЦТ 2026 по правилам организаторов.
MANDATORY_SLIDES = (7, 8, 9, 10, 11)


def render_pdf(workdir: Path) -> Path | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("LibreOffice не найден — проверка вёрстки пропущена.")
        return None
    pdf = workdir / (PPTX.stem + ".pdf")
    base_env = dict(os.environ)
    # На части сборок soffice.bin не находит libreglo.so без явного пути.
    program_dir = Path(soffice).resolve().parent
    attempts = [
        base_env,
        {**base_env, "LD_LIBRARY_PATH": str(program_dir)},
    ]
    for env in attempts:
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
            env=env,
        )
        if proc.returncode == 0 and pdf.exists():
            return pdf
    print("Не удалось конвертировать презентацию:", proc.stderr.strip())
    return None


def _spans(page):
    """Текстовые фрагменты страницы: (кегль, текст, bbox)."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if span["text"].strip():
                    out.append((span["size"], span["text"].strip(), span["bbox"]))
    return out


def _overlaps(blocks):
    """Пары текстовых блоков, чьи прямоугольники заметно пересекаются."""
    found = []
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            a, b = blocks[i], blocks[j]
            dx = min(a[2], b[2]) - max(a[0], b[0])
            dy = min(a[3], b[3]) - max(a[1], b[1])
            if dx > TOL and dy > TOL:
                found.append((a[4].strip(), b[4].strip()))
    return found


def analyze(pdf: Path, *, strict_font: bool = True) -> int:
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
        blocks = [b for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()]
        spans = _spans(page)

        for x0, y0, x1, y1, text, *_ in blocks:
            if x0 < -TOL or y0 < -TOL or x1 > width + TOL or y1 > height + TOL:
                print(
                    f"  Слайд {number}: текст за границей "
                    f"[{x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}] {text.strip()[:50]!r}"
                )
                problems += 1

        for a, b in _overlaps(blocks):
            print(f"  Слайд {number}: наложение {a[:30]!r} / {b[:30]!r}")
            problems += 1

        # Номера шагов шаблона («01»…«03») стоят в узкой рамке у правого края.
        # Фирменный Montserrat шире шаблонного Arial, и при переносе двухзначный
        # маркер разваливался на «0» и «2». Ловим такие случаи как дефект.
        for block in blocks:
            text = block[4].strip()
            parts = text.split("\n")
            if (
                len(parts) == 2
                and all(p.isdigit() and len(p) == 1 for p in parts)
                and block[0] > 880
            ):
                print(
                    f"  Слайд {number}: номер шага разбит на две строки "
                    f"{text!r}"
                )
                problems += 1

        # Мелкий шрифт. Номера слайдов шаблона — служебный декор, их не считаем.
        small = [
            s for s in spans
            if s[0] < MIN_FONT_PT - 0.01 and not _is_stub(s)
        ]
        if small and number in MANDATORY_SLIDES and strict_font:
            for size, text, _ in small[:5]:
                print(f"  Слайд {number}: кегль {size:.1f}pt < {MIN_FONT_PT:.0f}pt "
                      f"{text[:40]!r}")
            problems += 1
        elif small:
            print(
                f"  Слайд {number}: мелкий текст {min(s[0] for s in small):.1f}pt "
                f"({len(small)} фрагм.), вне обязательных слайдов"
            )

        print(
            f"  Слайд {number}: блоков текста {len(blocks)}, "
            f"размер {width:.0f}x{height:.0f}"
        )

    print(f"Итого дефектов вёрстки: {problems}")
    return 1 if problems else 0


def _is_stub(span) -> bool:
    """Служебный номерок шаблона в правом нижнем углу (12pt, одна цифра)."""
    size, text, bbox = span
    return (
        abs(size - TEMPLATE_STUB_PT) < 0.01
        and text.strip().isdigit()
        and bbox[0] > 800
    )


# Слайды блока решения: карточки рисуем сами, поэтому проверяем, что текст
# остаётся внутри своей карточки и ничего не выезжает за её рамку.
SOLUTION_SLIDES = (1, 2, 3, 4, 5, 6)


def check_text_in_cards(pdf: Path) -> int:
    """Текст не должен пересекать рамку карточки: либо внутри, либо вне.

    Ранее проверялись только наложения текстовых блоков, поэтому текст,
    вылезавший за пределы карточки (но не пересекавший другой текст), дефектом
    не считался. Здесь сверяем каждый текстовый блок с прямоугольниками карточек.
    """
    try:
        import pymupdf
    except ImportError:
        return 0

    doc = pymupdf.open(str(pdf))
    problems = 0
    for index in SOLUTION_SLIDES:
        if index > len(doc):
            continue
        page = doc[index - 1]
        cards = []
        for drawing in page.get_drawings():
            rect = drawing["rect"]
            # Крупные заливки-подложки карточек; фон слайда и полосы не считаем.
            if rect.width > 144 and rect.height > 60 and not (
                rect.width > 900 and rect.height > 520
            ):
                cards.append(rect)
        for block in page.get_text("blocks"):
            if block[6] != 0 or not block[4].strip():
                continue
            box = pymupdf.Rect(block[:4])
            for card in cards:
                inter = box & card
                if inter.is_empty:
                    continue
                if box in card:
                    break
                covered = (inter.width * inter.height) / max(
                    1.0, box.width * box.height
                )
                if covered < 0.999 and (box.height - inter.height) > TOL:
                    print(
                        f"  Слайд {index}: текст выходит за карточку "
                        f"({covered * 100:.0f}% внутри) {block[4].strip()[:45]!r}"
                    )
                    problems += 1
                    break
    print(f"Текст внутри карточек: дефектов {problems}")
    return problems


def check_template_fidelity() -> int:
    """Сверить сетку обязательных слайдов 7-11 с исходным шаблоном ЛЦТ.

    Организаторы требуют, чтобы слайды 7-11 сохранили исходный дизайн и
    структуру: заполняем плейсхолдеры текстом, но не двигаем блоки. Проверяем
    по геометрии (текст меняется при заполнении, поэтому сверять по строкам
    нельзя). На слайде состава команды допускается удаление неиспользуемых
    карточек, поэтому там геометрия ответа должна быть подмножеством шаблона.
    Титульный слайд (позиция 7) в шаблоне — только фон, текст добавляется.
    """
    from pptx import Presentation
    from pptx.util import Emu

    template = ROOT / "docs" / "presentation" / "template-lct2026.pptx"
    if not template.exists() or not PPTX.exists():
        print("Шаблон или презентация не найдены — сверка сетки пропущена.")
        return 0

    tpl = Presentation(str(template))
    final = Presentation(str(PPTX))
    problems = 0

    def boxes(slide):
        out = []
        for sh in slide.shapes:
            if not sh.has_text_frame or sh.left is None:
                continue
            text = sh.text_frame.text.strip()
            if not text or text.isdigit():
                continue
            out.append((Emu(sh.left).inches, Emu(sh.top).inches,
                        Emu(sh.width).inches, Emu(sh.height).inches))
        return out

    def match(pool, geo, used):
        """Индекс ближайшего блока шаблона, совпадающего с geo по геометрии."""
        for i, cand in enumerate(pool):
            if i in used:
                continue
            if _same_geometry(cand, geo):
                return i
        return None

    pairs = zip(range(7, 12), (7, 8, 9, 10, 11), strict=True)
    for pos, tpl_no in pairs:
        if pos == 7:
            continue  # титул: в шаблоне только подложка, блоки добавляются
        tpl_geo = boxes(tpl.slides[tpl_no - 1])
        fin_geo = boxes(final.slides[pos - 1])
        used: set[int] = set()
        for geo in fin_geo:
            idx = match(tpl_geo, geo, used)
            if idx is None:
                print(
                    f"  Слайд {pos}: блок вне сетки шаблона "
                    f"{_fmt(geo)}"
                )
                problems += 1
            else:
                used.add(idx)

    print(f"Сверка сетки обязательных слайдов: дефектов {problems}")
    return problems


def _same_geometry(a, b, tol=0.02) -> bool:
    return len(a) == len(b) and all(
        abs(x - y) <= tol for x, y in zip(a, b, strict=True))


def _fmt(geo) -> str:
    return "{:.2f},{:.2f} {:.2f}x{:.2f}".format(*geo)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-font-check",
        action="store_true",
        help="не требовать кегль >=14pt на обязательных слайдах",
    )
    args = parser.parse_args()

    if not PPTX.exists():
        print(f"Нет файла презентации: {PPTX}")
        return 1

    problems = check_template_fidelity()

    with tempfile.TemporaryDirectory() as tmp:
        pdf = render_pdf(Path(tmp))
        if pdf is None:
            return 1 if problems else 0
        problems += analyze(pdf, strict_font=not args.no_font_check)
        problems += check_text_in_cards(pdf)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

