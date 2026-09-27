"""Сборка презентации RTK CRM строго по официальному шаблону ЛЦТ 2026.

Основа — `template-lct2026.pptx` (файл организаторов). Скрипт:
1. удаляет из шаблона слайды-инструкции, библиотеку иконок и неиспользуемые
   дизайн-макеты, оставляя обязательные блоки (слайды 7-11) и нужные макеты
   презентации решения (12-29);
2. заполняет текстовые блоки реальным содержимым проекта, сохраняя
   оформление шаблона (Montserrat, палитра #FF0053 / #520977 / #310F53).

Скрипт идемпотентен: повторный запуск пересобирает файл из шаблона.
"""

from __future__ import annotations

import io
from pathlib import Path

import qrcode
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

BASE = Path(__file__).resolve().parent
TEMPLATE = BASE / "template-lct2026.pptx"
OUT = BASE / "RTK-CRM-LCT2026.pptx"
IMG_DIR = BASE.parent / "images"

# ---------------------------------------------------------------------------
# Палитра и типографика шаблона ЛЦТ.
# ---------------------------------------------------------------------------
PINK = RGBColor(0xFF, 0x00, 0x53)      # акцент
VIOLET = RGBColor(0x52, 0x09, 0x78)    # тёмный заголовочный блок
INK = RGBColor(0x1C, 0x1D, 0x22)       # основной текст
BODY = RGBColor(0x3C, 0x1B, 0x50)      # подзаголовки
MUTED = RGBColor(0x6B, 0x5B, 0x78)     # второстепенный текст
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SOFT = RGBColor(0xF7, 0xF4, 0xFA)      # светлая подложка карточек
FONT = "Montserrat"

# ---------------------------------------------------------------------------
# Данные команды (предоставлены капитаном).
# ---------------------------------------------------------------------------
TEAM_NAME = "RTK CRM"
CITY = "Москва"
CONTACT = "sabadaspaha@gmail.com"
REPO = "github.com/Pavel1778/rtk-crm"
DEMO = "Yandex Cloud (ВМ с nginx)"
API = "https://<домен>/api"

TEAM = [
    {"name": "Сабадаш Павел", "role": "Капитан, backend и инфраструктура", "tg": "Pasha1778"},
    {"name": "Тимофей Кобзев", "role": "Frontend и дизайн-система", "tg": "T1mka_Z"},
    {"name": "Сазонов Александр", "role": "Backend, API и интеграции", "tg": "saneik_me"},
    {"name": "Иван Мельников", "role": "Данные, отчёты и экспорт", "tg": "GooolZZ"},
    {"name": "Никита Предков", "role": "QA, документация и питч", "tg": "pretuan"},
]

# Слайды шаблона, которые остаются в презентации (1-based), в нужном порядке.
KEEP = [7, 8, 9, 10, 11, 13, 17, 19, 20, 16, 27]


def keep_only(prs: Presentation, keep: list[int]) -> None:
    """Оставить только указанные слайды шаблона и задать их порядок."""
    sld_id_lst = prs.slides._sldIdLst
    ids = list(sld_id_lst)
    keep_set = set(keep)
    rel_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

    remaining = {}
    for idx, el in enumerate(ids, start=1):
        if idx in keep_set:
            remaining[idx] = el
        else:
            prs.part.drop_rel(el.get(rel_ns))
            sld_id_lst.remove(el)
    for el in list(sld_id_lst):
        sld_id_lst.remove(el)
    for idx in keep:
        sld_id_lst.append(remaining[idx])


def fill_text(shape, lines, *, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT,
              font=FONT, line_spacing=1.12, space_after=4):
    """Перезаписать текстовый блок, сохранив оформление первого абзаца."""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.clear()
    for i, spec in enumerate(lines):
        if isinstance(spec, str):
            spec = {"text": spec}
        par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        par.alignment = spec.get("align", align)
        par.line_spacing = spec.get("line_spacing", line_spacing)
        par.space_after = Pt(spec.get("space_after", space_after))
        run = par.add_run()
        run.text = spec["text"]
        run.font.name = spec.get("font", font)
        run.font.size = Pt(spec.get("size", size))
        run.font.bold = spec.get("bold", bold)
        run.font.color.rgb = spec.get("color", color)


def add_text(slide, x, y, w, h, lines, **kw):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    fill_text(box, lines, **kw)
    return box


def add_card(slide, x, y, w, h, *, fill=WHITE, line=None, radius=0.06):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                                 Inches(w), Inches(h))
    shp.adjustments[0] = radius
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = False
    return shp


def add_pill(slide, x, y, w, h, text, *, fill=PINK, size=13):
    """Заголовочный блок раздела в стиле шаблона ЛЦТ."""
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                                 Inches(w), Inches(h))
    shp.adjustments[0] = 0.5
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    shp.shadow.inherit = False
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.14)
    tf.margin_right = Inches(0.14)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    par = tf.paragraphs[0]
    par.alignment = PP_ALIGN.LEFT
    run = par.add_run()
    run.text = text
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = WHITE
    return shp


def qr_stream(url: str):
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def add_picture_contained(slide, path: Path, x, y, w, h):
    """Вписать изображение в рамку с сохранением пропорций и центрированием."""
    from PIL import Image

    if not path.exists():
        return None
    with Image.open(path) as im:
        iw, ih = im.size
    scale = min(w / iw, h / ih)
    nw, nh = iw * scale, ih * scale
    left = x + (w - nw) / 2
    top = y + (h - nh) / 2
    pic = slide.shapes.add_picture(str(path), Inches(left), Inches(top),
                                   Inches(nw), Inches(nh))
    return pic


def unify_font(prs: Presentation) -> None:
    """Привести оставшиеся шаблонные раны (номера шагов) к фирменному шрифту."""
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for par in shape.text_frame.paragraphs:
                for run in par.runs:
                    run.font.name = FONT


def set_page_numbers(prs: Presentation) -> None:
    """Проставить номера страниц в служебном блоке шаблона.

    В шаблоне номер лежит в правом нижнем углу (≈12.6in, 7.0in) и может быть
    как плейсхолдером, так и обычным текстовым блоком.
    """
    bottom = Inches(6.8)
    right = Inches(12.3)
    for i, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            t = shape.text_frame.text.strip()
            if not t.isdigit():
                continue
            if shape.left < right or shape.top < bottom:
                continue
            if shape.width > Inches(1.0) or shape.height > Inches(0.6):
                continue
            tf = shape.text_frame
            tf.clear()
            run = tf.paragraphs[0].add_run()
            run.text = str(i)
            run.font.name = FONT
            run.font.size = Pt(12)
            run.font.color.rgb = RGBColor(0x52, 0x09, 0x78)


def pick(slide, prefix, *, count=None):
    """Найти текстовые блоки по началу текста, отсортированные слева направо."""
    found = []
    for sh in slide.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip().startswith(prefix):
            found.append(sh)
    found.sort(key=lambda sh: sh.left)
    if count is not None:
        assert len(found) == count, (prefix, len(found))
    return found


# ---------------------------------------------------------------------------
# Слайды.
# ---------------------------------------------------------------------------


def slide_title(s):
    add_text(s, 0.83, 1.55, 11.6, 1.5, [
        {"text": TEAM_NAME, "size": 66, "bold": True, "color": WHITE, "space_after": 0}])
    add_text(s, 0.9, 3.05, 10.5, 0.9, [
        {"text": "Система контроля взаимодействия ИТ Школы Ростелекома с вузами",
         "size": 21, "bold": True, "color": WHITE, "space_after": 0}])
    add_text(s, 0.9, 3.75, 10.5, 0.7, [
        {"text": "Лидеры цифровой трансформации 2026 · кейс №6",
         "size": 15, "color": RGBColor(0xF3, 0xC9, 0xE4), "space_after": 0}])
    add_pill(s, 0.9, 4.62, 3.5, 0.52, "Команда из 5 человек", size=13)
    add_text(s, 0.9, 5.42, 11.0, 0.5, [
        {"text": f"{CITY} · {REPO}", "size": 13,
         "color": RGBColor(0xE6, 0xD2, 0xEF), "space_after": 0}])


def slide_about(s):
    team_box, solution_box, unique_box = (
        pick(s, "О команде", count=1)[0],
        pick(s, "Краткое описание решения", count=1)[0],
        pick(s, "Уникальность решения", count=1)[0],
    )
    fill_text(team_box, [
        {"text": "О команде", "size": 20, "bold": True, "color": VIOLET, "space_after": 8},
        {"text": "Капитан: Сабадаш Павел, backend и инфраструктура", "size": 12},
        {"text": "Кол-во участников: 5 человек", "size": 12},
        {"text": "Краткое описание: команда собралась на хакатоне ЛЦТ 2026 вокруг задачи ИТ Школы — связать коммуникации с вузами в один управляемый процесс.", "size": 11, "color": MUTED},
        {"text": "Город и регион: Москва", "size": 12}])
    fill_text(solution_box, [
        {"text": "Краткое описание решения", "size": 20, "bold": True,
         "color": VIOLET, "space_after": 8},
        {"text": "CRM, которая ведёт взаимодействие с вузом от первого контакта до результата: Kanban по этапам workflow, карточка взаимодействия, задачи, комментарии, файлы и отчёты с экспортом.", "size": 12}])
    fill_text(unique_box, [
        {"text": "Уникальность решения", "size": 20, "bold": True,
         "color": VIOLET, "space_after": 8},
        {"text": "Настраиваемый workflow: этапы, порядок и цвета меняет администратор без доработки кода. Отдельные воронки B2B (14 этапов) и B2C (4 этапа) с корректной фильтрацией в UI, API и отчётах.", "size": 12}])


def slide_team(s):
    name_boxes = pick(s, "Имя Фамилия", count=5)
    role_boxes = pick(s, "Роль в команде", count=5)
    slots = [sh.left for sh in name_boxes]
    for member, nx_emu, nb, rb in zip(TEAM, slots, name_boxes, role_boxes):
        nx = nx_emu / 914400
        initials = "".join(p[0] for p in member["name"].split()[:2]).upper()
        circ = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(nx), Inches(2.25),
                                  Inches(1.45), Inches(1.45))
        circ.fill.solid()
        circ.fill.fore_color.rgb = PINK
        circ.line.color.rgb = WHITE
        circ.line.width = Pt(2)
        circ.shadow.inherit = False
        tf = circ.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        par = tf.paragraphs[0]
        par.alignment = PP_ALIGN.CENTER
        run = par.add_run()
        run.text = initials
        run.font.name = FONT
        run.font.size = Pt(26)
        run.font.bold = True
        run.font.color.rgb = WHITE

        fill_text(nb, [{"text": member["name"], "size": 14, "bold": True,
                        "color": INK, "space_after": 0}])
        fill_text(rb, [
            {"text": member["role"], "size": 10, "color": BODY, "space_after": 2},
            {"text": f"Telegram: @{member['tg']}", "size": 10, "color": MUTED,
             "space_after": 0}])

        url = f"https://t.me/{member['tg']}"
        s.shapes.add_picture(qr_stream(url), Inches(nx + 0.42), Inches(5.55),
                             Inches(0.78), Inches(0.78))
    add_text(s, 0.65, 6.60, 5.0, 0.4, [
        {"text": "QR-код ведёт на профиль участника в Telegram",
         "size": 9, "color": MUTED, "space_after": 0}])


def widen(shape, *, left=None, top=None, width=None, height=None):
    if left is not None:
        shape.left = Inches(left)
    if top is not None:
        shape.top = Inches(top)
    if width is not None:
        shape.width = Inches(width)
    if height is not None:
        shape.height = Inches(height)


def slide_history(s):
    hbox = pick(s, "Краткая история команды", count=1)[0]
    wbox = pick(s, "Почему вы выбрали", count=1)[0]
    cbox = pick(s, "С какими основными", count=1)[0]
    for box, top in ((hbox, 1.34), (wbox, 3.12), (cbox, 4.96)):
        widen(box, left=0.95, width=11.4, top=top, height=1.5)
    fill_text(hbox, [
        {"text": "Краткая история команды", "size": 15, "bold": True,
         "color": VIOLET, "space_after": 5},
        {"text": "Команда сложилась на хакатоне ЛЦТ 2026: backend, frontend, аналитика, отчёты и QA. Роли распределили по сильным сторонам, работали итерациями с ежедневной синхронизацией.", "size": 11.5}])
    fill_text(wbox, [
        {"text": "Почему выбрали эту задачу", "size": 15, "bold": True,
         "color": VIOLET, "space_after": 5},
        {"text": "Задача ИТ Школы — про реальный процесс, а не учебный кейс: взаимодействие с вузами живёт в таблицах и чатах. Хотелось собрать это в один прозрачный контур.", "size": 11.5}])
    fill_text(cbox, [
        {"text": "Сложности и вызовы", "size": 15, "bold": True,
         "color": VIOLET, "space_after": 5},
        {"text": "Свести две разные воронки — B2B (14 этапов) и B2C (4 этапа) — так, чтобы фильтры, создание заявок и отчёты не путали их между собой. Отдельно занимались версткой PDF-отчётов и контрастом тёмной темы.", "size": 11.5}])


def slide_short(s):
    tbox = pick(s, "Техническая суть решения", count=1)[0]
    mbox = pick(s, "Маркетинговая суть решения", count=1)[0]
    fill_text(tbox, [
        {"text": "Техническая суть решения", "size": 15, "bold": True,
         "color": VIOLET, "space_after": 6},
        {"text": "React 18 + TypeScript + Ant Design на клиенте; FastAPI, SQLAlchemy 2 (async), PostgreSQL и JWT на сервере. Вход через Keycloak (Code Flow + PKCE) или локальный JWT. Ролевой доступ и audit log для изменяющих операций.", "size": 11.5}])
    fill_text(mbox, [
        {"text": "Маркетинговая суть решения", "size": 15, "bold": True,
         "color": VIOLET, "space_after": 6},
        {"text": "Продукт закрывает потребность ИТ Школы в управляемом взаимодействии с вузами и переносится на другие подразделения с похожим процессом: продажи, партнёрства, работа с филиалами.", "size": 11.5}])


def slide_detail(s):
    add_card(s, 0.36, 1.43, 12.62, 5.52, fill=WHITE)
    add_pill(s, 0.62, 1.66, 4.4, 0.52, "01 · Подробное описание решения")
    cols = [
        ("Kanban-доска взаимодействий", [
            "Перемещение карточек между этапами (drag-and-drop)",
            "Поиск по вузу и фильтр по ИТ-продукту",
            "Отдельный выбор этапа на мобильной версии"]),
        ("Карточка взаимодействия", [
            "Вуз, продукт, направление и договор",
            "Задачи со сроками и ответственными",
            "Комментарии, файлы и история изменений"]),
        ("Управляемость и отчётность", [
            "Настройка этапов workflow администратором",
            "Интеграция с LMS и CMS: dry-run и импорт",
            "Экспорт отчётов в XLSX, XLS, PDF и JSON"]),
    ]
    x = 0.75
    for title, items in cols:
        add_card(s, x, 2.45, 3.75, 4.05, fill=SOFT)
        add_text(s, x + 0.24, 2.68, 3.3, 0.75, [
            {"text": title, "size": 13, "bold": True, "color": VIOLET, "space_after": 0}])
        add_text(s, x + 0.24, 3.42, 3.3, 2.9, [
            {"text": "•  " + it, "size": 11, "space_after": 8} for it in items])
        x += 3.94


def slide_tech(s):
    add_pill(s, 0.68, 0.95, 4.6, 0.52, "04 · Техническая проработка")
    cards = [
        ("Frontend", ["React 18 и TypeScript", "Vite, Ant Design 5, Zustand",
                      "Recharts и @dnd-kit"]),
        ("Backend", ["Python 3.11, FastAPI", "SQLAlchemy 2 async, asyncpg",
                     "Pydantic v2, JWT и bcrypt"]),
        ("Данные и инфраструктура", ["PostgreSQL (Managed или контейнер)",
                                     "Yandex Object Storage для файлов",
                                     "KeyDB для кэша, Docker Compose, Nginx"]),
        ("Интеграции и защита", ["Keycloak: Code Flow + PKCE, RS256",
                                 "LMS и CMS: контракт обмена, dry-run",
                                 "GigaChat: сводка по взаимодействию"]),
    ]
    positions = [
        (0.68, 1.75, 5.9), (6.75, 1.75, 5.9),
        (0.68, 4.0, 5.9), (6.75, 4.0, 5.9),
    ]
    for (title, items), (x, y, w) in zip(cards, positions):
        add_text(s, x + 0.22, y, w - 0.44, 0.5, [
            {"text": title, "size": 15, "bold": True, "color": VIOLET, "space_after": 0}])
        add_text(s, x + 0.22, y + 0.6, w - 0.44, 1.5, [
            {"text": "•  " + it, "size": 11.5, "space_after": 10} for it in items])


def slide_marketing(s):
    add_pill(s, 0.38, 0.35, 4.6, 0.52, "02 · Маркетинговая часть")
    add_card(s, 0.38, 1.11, 12.45, 2.22, fill=WHITE)
    add_text(s, 0.66, 1.34, 5.6, 1.8, [
        {"text": "Потребность", "size": 13, "bold": True, "color": VIOLET, "space_after": 6},
        {"text": "ИТ Школа ведёт десятки вузов-партнёров. Статус взаимодействия и договорённости разбросаны по таблицам и чатам, из-за чего теряются сроки и история.", "size": 11.5}])
    add_text(s, 6.6, 1.34, 6.0, 1.8, [
        {"text": "Продвижение и развитие", "size": 13, "bold": True,
         "color": VIOLET, "space_after": 6},
        {"text": "Продукт внедряется внутри Ростелекома как готовый контур, а затем тиражируется на подразделения с похожим процессом: продажи, партнёрства, работа с филиалами.", "size": 11.5}])


def slide_business(s):
    add_pill(s, 0.38, 0.35, 4.6, 0.52, "03 · Бизнес-составляющая")
    add_card(s, 0.38, 1.49, 5.89, 5.29, fill=WHITE)
    add_text(s, 0.66, 1.78, 5.3, 4.7, [
        {"text": "Эффект для ИТ Школы", "size": 15, "bold": True,
         "color": VIOLET, "space_after": 10},
        {"text": "•  Единый контур вместо таблиц и чатов", "size": 12, "space_after": 8},
        {"text": "•  Прозрачные этапы и ответственные", "size": 12, "space_after": 8},
        {"text": "•  Отчёт руководителю за секунды, а не за день", "size": 12, "space_after": 8},
        {"text": "•  Сохранённая история взаимодействий", "size": 12, "space_after": 8},
        {"text": "•  Ограничение: не более 2 активных взаимодействий на вуз",
         "size": 11, "color": MUTED, "space_after": 0}])
    add_text(s, 6.51, 1.49, 6.46, 0.5, [
        {"text": "Показатели", "size": 13, "bold": True, "color": VIOLET, "space_after": 0}])
    rows = [("14 этапов", "воронка B2B"), ("4 этапа", "воронка B2C"),
            ("4 формата", "XLSX · XLS · PDF · JSON"),
            ("2 роли", "менеджер и администратор"),
            ("0 ошибок", "на нагрузочном прогоне")]
    y = 2.02
    for big, small in rows:
        add_card(s, 6.51, y, 6.46, 0.82, fill=SOFT)
        add_text(s, 6.75, y + 0.13, 2.6, 0.55, [
            {"text": big, "size": 15, "bold": True, "color": PINK, "space_after": 0}])
        add_text(s, 9.35, y + 0.20, 3.4, 0.5, [
            {"text": small, "size": 11, "color": MUTED, "space_after": 0}])
        y += 1.06


def slide_unique(s):
    add_pill(s, 0.38, 0.35, 4.0, 0.52, "05 · Уникальность решения")
    add_text(s, 0.75, 2.05, 11.8, 4.3, [
        {"text": "Настраиваемый workflow без доработки кода", "size": 20,
         "bold": True, "color": VIOLET, "space_after": 10},
        {"text": "Администратор сам добавляет и переименовывает этапы, задаёт цвет колонки, порядок и включение — процесс меняется вместе с бизнесом, а не вслед за релизом.", "size": 13, "space_after": 14},
        {"text": "Две воронки в одном продукте", "size": 20, "bold": True,
         "color": VIOLET, "space_after": 10},
        {"text": "B2B строится на 14 этапах, B2C — на 4. Фильтры доски, создание заявок и отчёты учитывают scope, поэтому воронки не смешиваются ни в UI, ни в API.", "size": 13, "space_after": 0}])
    # Ближайшие шаги — коротко, чтобы раздел развития не терялся при сжатии
    # презентации до 11 слайдов.
    add_card(s, 0.75, 6.15, 11.8, 0.95, fill=SOFT)
    add_text(s, 1.0, 6.28, 11.3, 0.75, [
        {"text": "Планы по развитию", "size": 12, "bold": True,
         "color": VIOLET, "space_after": 3},
        {"text": "Браузерный smoke-тест сценариев · нагрузка Locust на стенде · резервное восстановление в CI · подтверждение контура хранения данных в РФ · перенос production после согласования.", "size": 10.5, "color": MUTED, "space_after": 0}])


def drop_text(slide, prefixes=(), exact=()):
    """Удалить текстовые блоки шаблона, не несущие смысла в готовом слайде."""
    for sh in list(slide.shapes):
        if not sh.has_text_frame:
            continue
        t = sh.text_frame.text.strip()
        if t in exact or any(t.startswith(p) for p in prefixes):
            sh._element.getparent().remove(sh._element)


def slide_demo(s):
    # Заголовки-заглушки макетов браузера из шаблона.
    drop_text(s, exact={"www.lider.com"})
    add_pill(s, 0.38, 0.35, 5.4, 0.52, "Демонстрация и результаты")
    # В экраны браузерных макетов шаблона подставляем реальные скриншоты.
    add_picture_contained(s, IMG_DIR / "02-kanban-board.png", 1.33, 1.62, 4.53, 2.41)
    add_picture_contained(s, IMG_DIR / "11-integration.png", 7.50, 1.62, 4.53, 2.41)
    add_text(s, 1.30, 4.16, 4.8, 1.6, [
        {"text": "Kanban-доска", "size": 13, "bold": True, "color": VIOLET, "space_after": 4},
        {"text": "Портфель взаимодействий с фильтрами по вузу и продукту, переключением B2B/B2C и перемещением карточек по этапам.", "size": 10.5, "space_after": 3},
        {"text": "Демо: " + DEMO, "size": 10.5, "bold": True, "color": PINK, "space_after": 0}])
    add_text(s, 7.47, 4.16, 4.8, 1.6, [
        {"text": "Интеграция с LMS и CMS", "size": 13, "bold": True, "color": VIOLET, "space_after": 4},
        {"text": "Контракт обмена, предпросмотр пакета без записи (dry-run) и идемпотентный импорт по номеру договора. Отчёты выгружаются в XLSX, XLS, PDF и JSON.", "size": 10.5, "space_after": 3},
        {"text": "API: " + API, "size": 10.5, "bold": True, "color": PINK, "space_after": 0}])

    # Результаты нагрузочного прогона — короткой строкой под скриншотами.
    add_card(s, 0.38, 5.72, 9.9, 1.25, fill=SOFT)
    add_text(s, 0.62, 5.87, 9.4, 1.0, [
        {"text": "Нагрузочный прогон (локально)", "size": 12, "bold": True,
         "color": VIOLET, "space_after": 3},
        {"text": "50 пользователей / 60 с: 1613 запросов, 0 ошибок, p95 — 93 мс. Смешанный read/write: 4673 запроса, 0 ошибок; экспорт PDF — 210 мс. Не является SLA production.", "size": 10, "color": MUTED, "space_after": 0}])

    # Контакты и QR на репозиторий — в правом нижнем углу.
    add_text(s, 10.45, 5.62, 2.5, 0.32, [
        {"text": "Репозиторий", "size": 10, "bold": True, "color": VIOLET,
         "align": PP_ALIGN.CENTER, "space_after": 0}])
    s.shapes.add_picture(qr_stream("https://" + REPO), Inches(10.92), Inches(5.92),
                         Inches(1.45), Inches(1.45))
    add_text(s, 0.38, 7.05, 9.9, 0.3, [
        {"text": f"{CITY} · {CONTACT}", "size": 9, "color": MUTED, "space_after": 0}])


BUILDERS = [slide_title, slide_about, slide_team, slide_history, slide_short,
            slide_detail, slide_tech, slide_marketing, slide_business,
            slide_unique, slide_demo]


def set_metadata(prs: Presentation) -> None:
    """Прописать автора документа явно, без следов инструментов генерации."""
    props = prs.core_properties
    props.author = TEAM[0]["name"]
    props.last_modified_by = TEAM[0]["name"]
    props.title = f"{TEAM_NAME} — ЛЦТ 2026, кейс №6"
    props.subject = "Система контроля взаимодействия ИТ Школы Ростелекома с вузами"
    props.comments = ""
    props.category = ""
    props.keywords = ""


def build() -> Path:
    prs = Presentation(str(TEMPLATE))
    keep_only(prs, KEEP)
    assert len(prs.slides) == len(BUILDERS), (len(prs.slides), len(BUILDERS))
    for slide, fn in zip(prs.slides, BUILDERS):
        fn(slide)
    unify_font(prs)
    set_page_numbers(prs)
    set_metadata(prs)
    prs.save(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"saved: {path} {path.stat().st_size} bytes")
