"""Рендер руководств в PDF: текст, кириллица, картинки и оглавление.

Вкладка «Помощь» отдаёт те же руководства, что лежат в `docs/`:
Markdown для чтения в браузере и PDF для выгрузки. Тесты следят за тем,
чтобы конвертер не терял разделы и не превращал кириллицу в мусор.
"""

from __future__ import annotations

from pathlib import Path

from app.services.guide_pdf import markdown_to_story, render_guide_pdf
from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"

SAMPLE = """# Руководство

Вводный абзац с **важным** словом и `кодом`.

## 1. Раздел

- пункт списка;
- второй пункт.

1. шаг первый;
2. шаг второй.
"""


def _pdf_text(markdown: str, title: str = "Тест") -> str:
    stream = render_guide_pdf(markdown, title=title, base_dir=REPO_ROOT)
    reader = PdfReader(stream)
    return "".join(page.extract_text() or "" for page in reader.pages)


def test_pdf_keeps_all_sections_from_real_guides() -> None:
    for guide in ("USER_GUIDE.md", "ADMIN_GUIDE.md"):
        markdown = (DOCS_DIR / guide).read_text(encoding="utf-8")
        text = _pdf_text(markdown)

        headings = [
            line[3:].strip() for line in markdown.splitlines() if line.startswith("## ")
        ]
        assert headings, guide
        for heading in headings:
            # Номер и текст раздела могут разойтись по строкам при переносе,
            # поэтому сверяем смысловую часть заголовка.
            words = [word for word in heading.split() if word[0].isalpha()]
            needle = words[0] if words else heading
            assert needle in text, f"{guide}: потерян раздел «{heading}»"


def test_pdf_renders_cyrillic_and_inline_markup() -> None:
    text = _pdf_text(SAMPLE)

    assert "Руководство" in text
    assert "важным" in text
    assert "кодом" in text
    # Отступы и переносы могут разорвать фразу — проверяем ключевые слова.
    for word in ("Раздел", "пункт", "шаг"):
        assert word in text


def test_pdf_embeds_screenshots_without_text_loss() -> None:
    markdown = (DOCS_DIR / "USER_GUIDE.md").read_text(encoding="utf-8")
    stream = render_guide_pdf(markdown, title="Пользователь", base_dir=DOCS_DIR)

    # В PDF картинки лежат как XObject подтипа /Image.
    assert b"/Subtype /Image" in stream.getvalue()
    assert "Kanban" in _pdf_text(markdown)


def test_sections_produce_flowables() -> None:
    story = markdown_to_story(SAMPLE, base_dir=REPO_ROOT)

    assert story, "Markdown без разметки не должен давать пустой документ"
    assert all(flowable is not None for flowable in story)


def test_missing_image_is_skipped_not_fatal() -> None:
    markdown = "# Т\n\n![нет картинки](images/does-not-exist.png)\n\nТекст."
    text = _pdf_text(markdown)

    assert "Текст" in text
