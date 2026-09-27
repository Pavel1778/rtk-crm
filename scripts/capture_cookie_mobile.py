"""Снимает cookie-баннер и модалку настроек на мобильных экранах.

Запуск (статическая сборка frontend уже отдаётся, например `vite preview`):

    python scripts/capture_cookie_mobile.py --url http://localhost:5173 --label after

Изображения кладутся в `docs/images/mobile/`:
`cookie-<label>-<устройство>-banner.png`, `...-modal.png` и
`policy-<label>-<устройство>-<страница>.png` для политик cookie/privacy.

Скрипт заодно проверяет, что баннер не занимает экран целиком, кнопки
помещаются в вьюпорт, модалка влезает по высоте, а сохранение выбора
пишет в localStorage ключ rtk_cookie_consent версии 1.0. Для страниц
политик дополнительно контролирует отсутствие горизонтальной прокрутки
и минимальный размер шрифта текста.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images" / "mobile"

# Мобильные размеры из задания + планшет и десктоп для контроля.
VIEWPORTS = {
    "iphone-se": {"width": 375, "height": 667},
    "iphone-14-pro-max": {"width": 430, "height": 932},
    "galaxy-s20": {"width": 360, "height": 800},
    "ipad": {"width": 820, "height": 1180},
    "desktop": {"width": 1440, "height": 900},
}

# Страницы политик, на которые ссылается баннер и форма входа.
POLICY_PAGES = {"cookie-policy": "/cookie-policy", "privacy": "/privacy"}


# Модалка настроек: в текущей сборке у неё есть rootClassName, в старой — нет.
# Берём видимый .ant-modal и оставляем селектор параметром, чтобы снимать
# «до» и «после» одним скриптом.
MODAL_SELECTOR = ".ant-modal:visible"
MODAL_METRICS = """() => {
    const m = document.querySelector('.ant-modal');
    const r = m.getBoundingClientRect();
    const footer = [...m.querySelectorAll('.ant-modal-footer .ant-btn')]
        .map(e => e.getBoundingClientRect().bottom);
    return {left: r.left, right: r.right, bottom: r.bottom,
            vh: window.innerHeight, footerBottom: footer};
}"""
FOOTER_OK = ".ant-modal .ant-modal-footer .ant-btn"



def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--label", default="after", choices=["before", "after"])
    parser.add_argument("--page", default="/cookie-policy")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, viewport in VIEWPORTS.items():
            mobile = viewport["width"] <= 430
            ctx = browser.new_context(
                viewport=viewport,
                device_scale_factor=2,
                is_mobile=mobile,
                has_touch=mobile,
            )
            page = ctx.new_page()
            page.goto(f"{args.url}{args.page}", wait_until="networkidle")
            page.evaluate("localStorage.clear()")
            page.reload(wait_until="networkidle")
            page.wait_for_selector(".cookie-banner", timeout=10000)

            box = page.evaluate(
                """() => {
                    const b = document.querySelector('.cookie-banner');
                    const r = b.getBoundingClientRect();
                    return {height: r.height, vh: window.innerHeight};
                }"""
            )
            ratio = box["height"] / box["vh"]
            if ratio > 0.65:
                problems.append(f"{name}: баннер занимает {ratio:.0%} экрана")

            buttons = page.locator(".cookie-banner__actions .ant-btn")
            if buttons.count() != 3:
                problems.append(f"{name}: кнопок {buttons.count()}, ожидалось 3")
            for i in range(buttons.count()):
                bb = buttons.nth(i).bounding_box()
                if bb is None:
                    problems.append(f"{name}: кнопка {i} не отрисована")
                    continue
                if (
                    bb["x"] < 0
                    or bb["x"] + bb["width"] > viewport["width"] + 1
                    or bb["y"] + bb["height"] > viewport["height"] + 1
                ):
                    problems.append(f"{name}: кнопка {i} выходит за экран {bb}")
                if bb["width"] < 60 or bb["height"] < 24:
                    problems.append(f"{name}: кнопка {i} слишком мелкая {bb}")

            page.screenshot(path=str(OUT / f"cookie-{args.label}-{name}-banner.png"))

            buttons.nth(1).click()
            try:
                page.wait_for_selector(MODAL_SELECTOR, timeout=5000)
                page.wait_for_timeout(900)
            except Exception:
                problems.append(f"{name}: модалка настроек не открылась")
                ctx.close()
                continue

            page.screenshot(path=str(OUT / f"cookie-{args.label}-{name}-modal.png"))

            modal = page.evaluate(
                MODAL_METRICS
            )
            if modal["left"] < -1 or modal["right"] > viewport["width"] + 1:
                problems.append(f"{name}: модалка выходит за экран {modal}")
            if modal["bottom"] > modal["vh"] + 1:
                problems.append(f"{name}: модалка выше экрана {modal}")
            for bottom in modal["footerBottom"]:
                if bottom > modal["vh"] + 1:
                    problems.append(f"{name}: кнопка модалки скрыта {bottom}")

            save = page.locator(FOOTER_OK).last
            try:
                save.click(timeout=5000)
            except Exception:
                # В старой сборке баннер с z-index 1100 перекрывает футер модалки.
                problems.append(f"{name}: кнопку сохранения модалки перекрывает другой элемент")
                ctx.close()
                continue
            page.wait_for_timeout(400)
            stored = page.evaluate("() => localStorage.getItem('rtk_cookie_consent')")
            if not stored or '"version":"1.0"' not in stored:
                problems.append(f"{name}: localStorage без версии 1.0: {stored}")
            if page.locator(".cookie-banner").count() != 0:
                problems.append(f"{name}: баннер не скрылся после сохранения")

            # Текст политик должен читаться без зума: 14px+, без прокрутки вбок.
            for slug, path in POLICY_PAGES.items():
                page.goto(f"{args.url}{path}", wait_until="networkidle")
                try:
                    page.wait_for_selector(".policy-card", timeout=8000)
                except Exception:
                    # Старая сборка: класса .policy-card ещё нет (см. git diff),
                    # поэтому берём карточку по тексту заголовка.
                    if page.locator(".ant-card").count() == 0:
                        problems.append(f"{name} {slug}: карточка политики не найдена")
                        continue
                page.evaluate("window.scrollTo(0, 0)")
                text = page.evaluate(
                    """() => {
                        const card = document.querySelector('.policy-card')
                            || document.querySelector('.ant-card');
                        // antd вешает .ant-typography на сами теги, а Paragraph —
                        // это div; листовые узлы дают реальный размер текста.
                        const items = [...card.querySelectorAll(
                            'p, li, td, th, .ant-typography'
                        )].filter(e => e.textContent.trim() && !e.children.length);
                        const sizes = items.map(e => parseFloat(getComputedStyle(e).fontSize));
                        return {min: sizes.length ? Math.min(...sizes) : 0,
                                hScroll: document.documentElement.scrollWidth - window.innerWidth};
                    }"""
                )
                if text["min"] and text["min"] < 13.5:
                    problems.append(f"{name} {slug}: шрифт {text['min']}px мельче 14px")
                if text["hScroll"] > 1:
                    problems.append(f"{name} {slug}: горизонтальная прокрутка +{text['hScroll']}px")
                page.screenshot(path=str(OUT / f"policy-{args.label}-{name}-{slug}.png"))

            ctx.close()
        browser.close()

    for problem in problems:
        print("ПРОБЛЕМА:", problem)
    print(f"Скриншоты: {OUT} (метка {args.label})")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
