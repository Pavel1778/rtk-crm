"""Рендер руководств (Markdown) в PDF для встроенной справки.

Документация должна быть читаема внутри платформы и выгружаема файлом
(ТЗ НФТ-5). Отдельная библиотека markdown не нужна: поддерживаемого
подмножества — заголовки, абзацы, списки, изображения, **жирный** и
`код` — достаточно для наших руководств.
"""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from app.services.excel_export import _resolve_pdf_fonts
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

_MARGIN = 20 * mm
_MAX_IMAGE_WIDTH = 150 * mm

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_CODE_RE = re.compile(r"`([^`]+)`")
_IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)\s*$")
_BULLET_RE = re.compile(r"^[-*]\s+(?P<text>.+)$")
_ORDERED_RE = re.compile(r"^(?P<number>\d+)[.)]\s+(?P<text>.+)$")
_HEADING_RE = re.compile(r"^(?P<level>#{1,6})\s+(?P<text>.+)$")


def _inline(text: str, regular: str) -> str:
    """Экранирует текст и превращает разметку в теги reportlab.

    Инлайновый код выделяем цветом: моноширинный Courier не знает
    кириллицу, а DejaVu с другим цветом читается как код и не ломает
    русские фрагменты.
    """
    escaped = escape(text)
    escaped = _BOLD_RE.sub(r"<b>\1</b>", escaped)
    escaped = _CODE_RE.sub(r'<font color="#6E41F2">\1</font>', escaped)
    return escaped


def _styles() -> dict[str, ParagraphStyle]:
    regular, bold = _resolve_pdf_fonts()
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "GuideTitle",
            parent=base["Title"],
            fontName=bold,
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#6E41F2"),
            spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "GuideH2",
            parent=base["Heading2"],
            fontName=bold,
            fontSize=14,
            leading=18,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "GuideH3",
            parent=base["Heading3"],
            fontName=bold,
            fontSize=12,
            leading=16,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "GuideBody",
            parent=base["Normal"],
            fontName=regular,
            fontSize=10.5,
            leading=15,
            spaceAfter=6,
        ),
        "caption": ParagraphStyle(
            "GuideCaption",
            parent=base["Normal"],
            fontName=regular,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#6B6B72"),
            alignment=1,
            spaceAfter=12,
        ),
        "regular": regular,
        "code_font": regular,
    }


def _image_flowable(source: str, base_dir: Path) -> list:
    path = Path(source)
    if not path.is_absolute():
        path = base_dir / source.lstrip("/")
    if not path.exists():
        return []
    image = Image(str(path))
    scale = min(_MAX_IMAGE_WIDTH / image.imageWidth, 1.0)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    image.hAlign = "CENTER"
    return [Spacer(1, 6), image]


def _flush_paragraph(buffer: list[str], story: list, styles: dict) -> None:
    if not buffer:
        return
    text = " ".join(part.strip() for part in buffer).strip()
    buffer.clear()
    if text:
        story.append(Paragraph(_inline(text, styles["code_font"]), styles["body"]))


def markdown_to_story(markdown: str, base_dir: Path) -> list:
    """Превращает Markdown в последовательность flowable-объектов."""
    styles = _styles()
    story: list = []
    paragraph: list[str] = []
    items: list[str] = []
    ordered = False

    def flush_list() -> None:
        nonlocal ordered
        if not items:
            return
        story.append(
            ListFlowable(
                [
                    ListItem(
                        Paragraph(_inline(item, styles["code_font"]), styles["body"]),
                        leftIndent=16,
                    )
                    for item in items
                ],
                bulletType="1" if ordered else "bullet",
                start="1",
                leftIndent=16,
            )
        )
        items.clear()
        ordered = False

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        image_match = _IMAGE_RE.match(line.strip())
        if image_match:
            _flush_paragraph(paragraph, story, styles)
            flush_list()
            story.extend(_image_flowable(image_match.group("src"), base_dir))
            caption = image_match.group("alt").strip()
            if caption:
                story.append(Paragraph(escape(caption), styles["caption"]))
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            _flush_paragraph(paragraph, story, styles)
            flush_list()
            level = len(heading_match.group("level"))
            text = heading_match.group("text").strip()
            if level == 1:
                story.append(Paragraph(_inline(text, styles["code_font"]), styles["title"]))
            elif level == 2:
                story.append(Paragraph(_inline(text, styles["code_font"]), styles["h2"]))
            else:
                story.append(Paragraph(_inline(text, styles["code_font"]), styles["h3"]))
            continue

        bullet_match = _BULLET_RE.match(line.strip())
        ordered_match = _ORDERED_RE.match(line.strip())
        if bullet_match or ordered_match:
            _flush_paragraph(paragraph, story, styles)
            if ordered_match:
                if items and not ordered:
                    flush_list()
                ordered = True
                items.append(ordered_match.group("text").strip())
            elif bullet_match is not None:
                if items and ordered:
                    flush_list()
                items.append(bullet_match.group("text").strip())
            continue

        if not line.strip():
            _flush_paragraph(paragraph, story, styles)
            flush_list()
            continue

        if line.strip() in {"---", "***", "___"}:
            _flush_paragraph(paragraph, story, styles)
            flush_list()
            story.append(Spacer(1, 8))
            continue

        flush_list()
        paragraph.append(line)

    _flush_paragraph(paragraph, story, styles)
    flush_list()
    return story


def render_guide_pdf(
    markdown: str, title: str, base_dir: Path, author: str = "Команда RTK CRM"
) -> BytesIO:
    """Собирает PDF-руководство и возвращает поток с его содержимым."""
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN,
        bottomMargin=_MARGIN,
        title=title,
        author=author,
        creator="RTK CRM",
    )
    doc.build(markdown_to_story(markdown, base_dir))
    output.seek(0)
    return output
