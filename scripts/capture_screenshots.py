"""Снимает скриншоты страниц RTK CRM в светлой и тёмной теме.

Запуск (backend и frontend уже подняты локально):

    python scripts/capture_screenshots.py [--theme light|dark|both] [--mobile]

Изображения кладутся в `docs/images/` (светлая) и `docs/images/dark/`
(тёмная), мобильные виды — в `docs/images/mobile/`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "http://localhost:5173"
ADMIN = ("admin@rtk.ru", "admin123")

DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}


def apply_theme(page: Page, theme: str) -> None:
    """themeStore читает тему из storage при инициализации, поэтому после
    записи нужна полная перезагрузка, а не SPA-переход."""
    page.evaluate(
        """(theme) => {
            localStorage.setItem('rtk-theme-mode', theme);
            document.documentElement.setAttribute('data-theme', theme);
            document.documentElement.style.colorScheme = theme;
        }""",
        theme,
    )


def login(page: Page, url: str) -> None:
    page.goto(f"{url}/login", wait_until="networkidle")
    page.fill("#login-email", ADMIN[0])
    page.fill("#login-password", ADMIN[1])
    page.click('button[type="submit"]')
    page.wait_for_url(lambda target: "/login" not in target, timeout=20000)
    page.wait_for_load_state("networkidle")
    dismiss_cookie_banner(page)


def dismiss_cookie_banner(page: Page) -> None:
    """Баннер согласия перекрывает нижнюю часть экрана и ломает снимки."""
    accept = page.locator(".cookie-banner button", has_text="Принять")
    if accept.count():
        accept.first.click()
        page.wait_for_timeout(300)


def shoot(page: Page, target: Path, name: str) -> None:
    page.wait_for_timeout(1100)
    page.screenshot(path=str(target / f"{name}.png"))
    print("saved", name)


def capture_desktop(page: Page, theme: str, target: Path) -> None:
    apply_theme(page, theme)

    page.goto("http://localhost:5173/", wait_until="networkidle")
    dismiss_cookie_banner(page)
    shoot(page, target, "02-kanban-board")

    # Панель фильтров: открываем поиск и подсказку по продукту.
    page.goto("http://localhost:5173/", wait_until="networkidle")
    search = page.locator("#board-search, input[placeholder*='Поиск']").first
    if search.count():
        search.click()
        page.wait_for_timeout(400)
    product = page.locator("#board-product-filter")
    if product.count():
        product.click()
        page.wait_for_timeout(500)
        page.keyboard.press("Escape")
    shoot(page, target, "04-board-filters")

    # Карточка взаимодействия: открываем первую карточку доски.
    page.goto("http://localhost:5173/", wait_until="networkidle")
    card = page.locator(".kanban-board .ant-card").first
    if card.count():
        card.click()
        page.wait_for_timeout(1200)
    shoot(page, target, "03-interaction-card")

    page.goto("http://localhost:5173/directories", wait_until="networkidle")
    shoot(page, target, "05-directories")

    page.goto("http://localhost:5173/directories", wait_until="networkidle")
    import_button = page.locator("button", has_text="Импорт").first
    if import_button.count():
        import_button.click()
        page.wait_for_timeout(900)
    shoot(page, target, "06-import-xlsx-mapping")

    # Конструктор этапов и список пользователей — две вкладки одной страницы
    # «Настройки». Без переключения вкладки снимки 08 и 09 совпадали.
    page.goto("http://localhost:5173/settings", wait_until="networkidle")
    workflow_tab = page.locator(".ant-tabs-tab", has_text="Этапы воркфлоу").first
    if workflow_tab.count():
        workflow_tab.click()
        page.wait_for_timeout(700)
    shoot(page, target, "08-workflow-constructor")

    page.goto("http://localhost:5173/settings", wait_until="networkidle")
    users_tab = page.locator(".ant-tabs-tab", has_text="Пользователи").first
    if users_tab.count():
        users_tab.click()
        page.wait_for_timeout(700)
    shoot(page, target, "09-settings")

    for name, path in [
        ("07-reports", "/reports"),
        ("10-help-docs", "/help"),
    ]:
        page.goto(f"http://localhost:5173{path}", wait_until="networkidle")
        shoot(page, target, name)


def capture_login(theme: str, target: Path, viewport: dict) -> None:
    """Экран входа снимаем в чистом контексте: после логина он недоступен."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=viewport, locale="ru-RU")
        page = context.new_page()
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        apply_theme(page, theme)
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(900)
        page.screenshot(path=str(target / "01-login.png"))
        print("saved 01-login")
        context.close()
        browser.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", choices=["light", "dark", "both"], default="both")
    parser.add_argument("--mobile", action="store_true")
    args = parser.parse_args()

    themes = ["light", "dark"] if args.theme == "both" else [args.theme]
    viewport = MOBILE if args.mobile else DESKTOP

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in themes:
            target = ROOT / "docs" / "images"
            if args.mobile:
                target = target / "mobile"
            elif theme == "dark":
                target = target / "dark"
            target.mkdir(parents=True, exist_ok=True)

            context = browser.new_context(viewport=viewport, locale="ru-RU")
            page = context.new_page()
            login(page, BASE_URL)
            if args.mobile:
                page.goto(f"{BASE_URL}/", wait_until="networkidle")
                apply_theme(page, theme)
                page.reload(wait_until="networkidle")
                dismiss_cookie_banner(page)
                shoot(page, target, "02-kanban-board")
                # На телефоне этапы переключаются чипами: снимаем выбранный этап.
                chip = page.locator(".stage-chip").nth(1)
                if chip.count():
                    chip.click()
                    page.wait_for_timeout(700)
                shoot(page, target, "04-board-filters")
                page.goto(f"{BASE_URL}/reports", wait_until="networkidle")
                shoot(page, target, "07-reports")
                page.goto(f"{BASE_URL}/help", wait_until="networkidle")
                shoot(page, target, "10-help-docs")
            else:
                capture_desktop(page, theme, target)
            context.close()

        browser.close()

    for theme in themes:
        target = ROOT / "docs" / "images"
        if args.mobile:
            target = target / "mobile"
        elif theme == "dark":
            target = target / "dark"
        target.mkdir(parents=True, exist_ok=True)
        capture_login(theme, target, viewport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
