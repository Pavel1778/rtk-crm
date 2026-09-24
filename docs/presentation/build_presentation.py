"""Сборка презентации RTK CRM по шаблону ЛЦТ 2026.

Оформление повторяет шаблон: 16:9, палитра ЛЦТ, шрифт Montserrat.
Для каждого участника — место под аватар и QR-код на Telegram.
"""

from __future__ import annotations

import io
from pathlib import Path

import qrcode
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

OUT = Path("/workspace/project/docs/presentation/RTK-CRM-LCT2026.pptx")
IMG_DIR = Path("/workspace/project/docs/images")

# Палитра шаблона ЛЦТ.
PINK = RGBColor(0xFF, 0x00, 0x53)
PINK_SOFT = RGBColor(0xFF, 0xD6, 0xE4)
LILAC = RGBColor(0x8A, 0x83, 0xD1)
VIOLET = RGBColor(0x52, 0x09, 0x78)
PURPLE = RGBColor(0x31, 0x0F, 0x53)
DARK = RGBColor(0x1C, 0x1D, 0x22)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY = RGBColor(0x6B, 0x6B, 0x72)
FONT = "Montserrat"

TEAM = [
    {
        "name": "ФИО капитана",
        "role": "Капитан, backend и инфраструктура",
        "tg": "ник в Telegram",
        "tg_url": None,
    },
    {
        "name": "ФИО участника",
        "role": "Frontend и дизайн-система",
        "tg": "ник в Telegram",
        "tg_url": None,
    },
    {
        "name": "ФИО участника",
        "role": "Backend, API и интеграции",
        "tg": "ник в Telegram",
        "tg_url": None,
    },
    {
        "name": "ФИО участника",
        "role": "Продукт и бизнес-аналитика",
        "tg": "ник в Telegram",
        "tg_url": None,
    },
    {
        "name": "ФИО участника",
        "role": "QA, тестирование и безопасность",
        "tg": "ник в Telegram",
        "tg_url": None,
    },
]

TEAM_NAME = "RTK CRM"
CITY = "город и регион"
TEAM_CONTACT = "team@rtk-crm.ru"


def blank(prs: Presentation):
    return prs.slides.add_slide(prs.slide_layouts[6])


def rect(slide, x, y, w, h, fill, *, line=None, shape=MSO_SHAPE.RECTANGLE):
    shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = False
    return shp


def text(
    slide,
    x,
    y,
    w,
    h,
    runs,
    *,
    size=16,
    color=DARK,
    bold=False,
    align=PP_ALIGN.LEFT,
    space_after=6,
    line_spacing=1.05,
):
    """runs: список строк или список (str, dict) для смешанного формата."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.word_wrap = True
    first = True
    for item in runs:
        para = frame.paragraphs[0] if first else frame.add_paragraph()
        first = False
        para.alignment = align
        para.space_after = Pt(space_after)
        para.line_spacing = line_spacing
        chunks = [(item, {})] if isinstance(item, str) else [item]
        for chunk_text, opts in chunks:
            run = para.add_run()
            run.text = chunk_text
            run.font.name = FONT
            run.font.size = Pt(opts.get("size", size))
            run.font.bold = opts.get("bold", bold)
            run.font.color.rgb = opts.get("color", color)
    return box


def page_number(slide, number):
    text(
        slide,
        12.4,
        6.95,
        0.6,
        0.35,
        [str(number)],
        size=11,
        color=GREY,
        align=PP_ALIGN.RIGHT,
    )


def header(slide, title, number):
    rect(slide, 0.55, 0.35, 0.14, 0.42, PINK)
    text(slide, 0.85, 0.32, 10.5, 0.5, [title], size=26, bold=True, color=PURPLE)
    page_number(slide, number)


def qr_png(url: str) -> io.BytesIO:
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def avatar_placeholder(slide, x, y, d, index):
    circle = rect(slide, x, y, d, d, PINK_SOFT, shape=MSO_SHAPE.OVAL)
    frame = circle.text_frame
    frame.word_wrap = False
    para = frame.paragraphs[0]
    para.alignment = PP_ALIGN.CENTER
    run = para.add_run()
    run.text = str(index)
    run.font.name = FONT
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = VIOLET
    return circle


def qr_placeholder(slide, x, y, d):
    """Рамка под QR-код: заполняется ссылкой на профиль участника."""
    box = rect(slide, x, y, d, d, WHITE, line=LILAC)
    frame = box.text_frame
    frame.word_wrap = True
    para = frame.paragraphs[0]
    para.alignment = PP_ALIGN.CENTER
    run = para.add_run()
    run.text = "QR"
    run.font.name = FONT
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = LILAC
    return box


def build() -> Path:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # ─── 1. Титульный ───
    s = blank(prs)
    rect(s, 0, 0, 13.333, 7.5, PURPLE)
    rect(s, 0, 0, 13.333, 0.22, PINK)
    text(s, 1.0, 1.5, 4.9, 0.5, ["ЛЦТ 2026 · Кейс №6"], size=18, color=PINK_SOFT, bold=True)
    text(s, 1.0, 2.05, 11.0, 1.2, [TEAM_NAME], size=64, color=WHITE, bold=True)
    text(
        s,
        1.0,
        3.3,
        11.0,
        0.9,
        ["CRM для взаимодействия ИТ Школы Ростелекома с вузами"],
        size=24,
        color=PINK_SOFT,
    )
    text(
        s,
        1.0,
        4.25,
        11.0,
        0.4,
        ["От первого контакта до контроля результата"],
        size=16,
        color=LILAC,
    )
    rect(s, 1.0, 5.35, 3.2, 0.06, PINK)
    text(s, 1.0, 5.6, 11.0, 0.4, [f"Команда {TEAM_NAME} · {CITY}"], size=14, color=WHITE)
    rect(s, 9.4, 1.5, 3.0, 1.1, RGBColor(0x3D, 0x1B, 0x63), line=LILAC)
    text(
        s,
        9.4,
        1.9,
        3.0,
        0.5,
        ["Место для логотипов", "постановщика задачи"],
        size=11,
        color=LILAC,
        align=PP_ALIGN.CENTER,
    )
    page_number(s, 1)

    # ─── 2. Проблема ───
    s = blank(prs)
    header(s, "Проблема", 2)
    text(
        s,
        0.85,
        1.45,
        6.4,
        5.2,
        [
            "Данные распределены по таблицам и чатам",
            "Статус взаимодействия зависит от ручных обновлений",
            "Руководителю сложно видеть узкие места",
            "Отчёты собираются долго",
            "Риск потери истории и контрольных сроков",
        ],
        size=17,
        space_after=16,
    )
    rect(s, 7.6, 1.45, 5.0, 4.9, RGBColor(0xF7, 0xF2, 0xFB))
    text(s, 8.0, 1.75, 4.2, 0.5, ["Суть"], size=15, bold=True, color=PINK)
    text(
        s,
        8.0,
        2.25,
        4.2,
        3.8,
        [
            "Проблема не в отсутствии данных, а в отсутствии единого рабочего "
            "контекста и понятного следующего действия.",
            "КАМ ведёт портфель вузов в разных источниках, поэтому результат "
            "коммуникации теряется, а руководитель видит картину с задержкой.",
        ],
        size=14,
        color=DARK,
        space_after=12,
    )

    # ─── 3. Решение ───
    s = blank(prs)
    header(s, "Решение", 3)
    text(
        s,
        0.85,
        1.45,
        6.4,
        5.2,
        [
            "Kanban по 14 этапам workflow и отдельная воронка B2C",
            "Карточка взаимодействия: вуз + продукт + договор",
            "Задачи, комментарии, файлы и история",
            "Отчёты и экспорт XLSX / XLS / PDF / JSON",
            "RBAC для КАМ, руководителей и администраторов",
        ],
        size=17,
        space_after=16,
    )
    rect(s, 7.6, 1.45, 5.0, 4.9, RGBColor(0xF7, 0xF2, 0xFB))
    text(s, 8.0, 1.75, 4.2, 0.5, ["Уникальность"], size=15, bold=True, color=PINK)
    text(
        s,
        8.0,
        2.25,
        4.2,
        3.8,
        [
            "Видит состояние портфеля на одном экране и сразу обновляет этап "
            "или фиксирует результат коммуникации.",
            "Одна модель данных покрывает и B2B-взаимодействия с вузами, и "
            "клиентскую воронку B2C — с раздельными наборами этапов и без "
            "дублирования справочников.",
        ],
        size=14,
        color=DARK,
        space_after=12,
    )

    # ─── 4. Демонстрация ───
    s = blank(prs)
    header(s, "Демонстрация", 4)
    text(
        s,
        0.85,
        1.35,
        5.6,
        5.3,
        [
            "Вход и дашборд с KPI",
            "Перемещение карточки между этапами",
            "Добавление задачи и комментария",
            "Настройка этапа администратором",
            "Графики и скачивание отчёта",
            "Импорт справочников из XLSX",
        ],
        size=16,
        space_after=14,
    )
    shots = [
        "02-kanban-board.png",
        "03-interaction-card.png",
        "07-reports.png",
        "08-workflow-constructor.png",
    ]
    for name, (x, y) in zip(shots, [(6.75, 1.35), (9.95, 1.35), (6.75, 3.95), (9.95, 3.95)]):
        path = IMG_DIR / name
        if path.exists():
            s.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(3.05))
        else:
            rect(s, x, y, 3.05, 1.9, RGBColor(0xEE, 0xEA, 0xF5))

    # ─── 5. Архитектура ───
    s = blank(prs)
    header(s, "Архитектура", 5)
    layers = [
        ("Frontend", "React · Vite · Ant Design · Recharts · dnd-kit", PINK_SOFT, VIOLET),
        ("API", "FastAPI · Pydantic v2 · SQLAlchemy Async · JWT, RBAC, audit", RGBColor(0xED, 0xE7, 0xF9), PURPLE),
        ("Данные", "PostgreSQL в Supabase · Alembic · Redis-кэш отчётов", RGBColor(0xE3, 0xFB, 0xEC), RGBColor(0x0B, 0x6B, 0x3A)),
        ("Контур", "Render (backend) · Vercel (frontend) · Docker Compose + Nginx", RGBColor(0xE7, 0xF0, 0xFE), RGBColor(0x1D, 0x4E, 0xD8)),
    ]
    y = 1.5
    for title_, body, fill, fg in layers:
        rect(s, 0.85, y, 11.6, 1.05, fill)
        text(s, 1.15, y + 0.12, 2.6, 0.4, [title_], size=16, bold=True, color=fg)
        text(s, 3.6, y + 0.16, 8.6, 0.7, [body], size=13, color=DARK)
        y += 1.25

    # ─── 6. Технологии и качество ───
    s = blank(prs)
    header(s, "Технологии и качество", 6)
    cols = [
        ("Единый конфиг колонок", "Отчёты, таблицы UI и выгрузки XLSX/XLS/PDF собираются из одного JSON-описания."),
        ("Коды ошибок", "Стабильные коды НФТ-3: фронтенд показывает понятное сообщение по коду."),
        ("Заголовки безопасности", "CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy и HSTS."),
        ("Кэш отчётов", "Сводка кэшируется по полному набору фильтров, включая воронку B2B/B2C."),
    ]
    x = 0.85
    for title_, body in cols:
        rect(s, x, 1.5, 2.85, 4.6, RGBColor(0xF7, 0xF2, 0xFB))
        rect(s, x, 1.5, 2.85, 0.1, PINK)
        text(s, x + 0.22, 1.85, 2.4, 0.9, [title_], size=14, bold=True, color=PURPLE)
        text(s, x + 0.22, 2.75, 2.4, 3.1, [body], size=12, color=DARK)
        x += 3.0

    # ─── 7. 152-ФЗ и безопасность ───
    s = blank(prs)
    header(s, "152-ФЗ и безопасность", 7)
    text(
        s,
        0.85,
        1.45,
        6.5,
        5.2,
        [
            "HTTPS и credentialed CORS",
            "JWT и ролевой контроль доступа (RBAC)",
            "Audit log для изменяющих операций",
            "Cookie consent и privacy policy",
            "Секреты только через переменные окружения",
            "Подготовлена миграция БД в Yandex Cloud",
        ],
        size=17,
        space_after=16,
    )
    rect(s, 7.7, 1.45, 4.9, 3.1, RGBColor(0xF7, 0xF2, 0xFB))
    text(s, 8.0, 1.7, 4.3, 0.4, ["Нагрузка (Locust)"], size=15, bold=True, color=PINK)
    text(
        s,
        8.0,
        2.15,
        4.3,
        2.2,
        [
            "Цель: 50 пользователей, 60 секунд",
            "Целевой p95 — менее 1000 мс",
            "Локальный прогон: 1460 запросов, 0 % ошибок",
            "Точка оптимизации — login под нагрузкой",
        ],
        size=13,
        color=DARK,
        space_after=10,
    )
    rect(s, 7.7, 4.75, 4.9, 1.7, PINK_SOFT)
    text(
        s,
        8.0,
        5.0,
        4.3,
        1.2,
        [
            "Контролы отражены в коде, документации и инфраструктурном плане, "
            "а не только декларируются."
        ],
        size=13,
        color=VIOLET,
    )

    # ─── 8. Планы по развитию ───
    s = blank(prs)
    header(s, "Планы по развитию", 8)
    steps = [
        ("Сейчас", "Production-контур работает: B2B/B2C, отчёты, RBAC"),
        ("Далее", "Browser smoke test и нагрузочное измерение на стенде"),
        ("Дальше", "Резервное восстановление в CI"),
        ("Перспектива", "Подтверждение контура хранения в РФ и перенос production"),
    ]
    y = 1.5
    for label, body in steps:
        rect(s, 0.85, y, 11.6, 1.0, RGBColor(0xF7, 0xF2, 0xFB))
        rect(s, 0.85, y, 0.12, 1.0, PINK)
        text(s, 1.25, y + 0.28, 2.2, 0.4, [label], size=15, bold=True, color=PURPLE)
        text(s, 3.5, y + 0.3, 8.7, 0.5, [body], size=14, color=DARK)
        y += 1.2

    # ─── 9. Команда ───
    s = blank(prs)
    header(s, "Команда", 9)
    text(
        s,
        0.85,
        1.15,
        11.6,
        0.4,
        [f"{TEAM_NAME} · {CITY} · состав заполняется перед защитой"],
        size=14,
        color=GREY,
    )
    x = 0.85
    for index, member in enumerate(TEAM, start=1):
        rect(s, x, 1.75, 2.28, 4.3, RGBColor(0xF7, 0xF2, 0xFB))
        avatar_placeholder(s, x + 0.74, 2.0, 0.8, index)
        text(s, x + 0.16, 2.95, 1.96, 0.5, [member["name"]], size=13, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)
        text(s, x + 0.16, 3.45, 1.96, 0.9, [member["role"]], size=11, color=DARK, align=PP_ALIGN.CENTER)
        if member["tg_url"]:
            qr = s.shapes.add_picture(
                qr_png(member["tg_url"]), Inches(x + 0.74), Inches(4.35), width=Inches(0.8)
            )
            qr.name = f"qr-{member['tg']}"
        else:
            qr_placeholder(s, x + 0.74, 4.35, 0.8)
        text(s, x + 0.1, 5.25, 2.08, 0.4, [member["tg"]], size=11, color=PINK, align=PP_ALIGN.CENTER)
        x += 2.4

    # ─── 10. Контакты ───
    s = blank(prs)
    rect(s, 0, 0, 13.333, 7.5, PURPLE)
    rect(s, 0, 0, 13.333, 0.22, PINK)
    text(s, 1.0, 1.4, 11.0, 0.8, ["Спасибо за внимание"], size=44, color=WHITE, bold=True)
    text(
        s,
        1.0,
        2.5,
        11.0,
        3.2,
        [
            "RTK CRM — ИТ Школа Ростелекома",
            "ЛЦТ 2026, кейс №6",
            "Репозиторий: github.com/Pavel1778/rtk-crm",
            "Демо: rtk-crm-nx4r.vercel.app",
            "API: rtk-crm-backend.onrender.com",
            f"Контакт команды: {TEAM_CONTACT}",
        ],
        size=17,
        color=PINK_SOFT,
        space_after=14,
    )
    text(
        s,
        1.0,
        6.1,
        11.0,
        0.4,
        ["Готовы показать путь от карточки взаимодействия до управленческого отчёта."],
        size=14,
        color=LILAC,
    )
    page_number(s, 10)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build()
    print("saved:", path, path.stat().st_size)