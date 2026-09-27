"""Суммаризация коммуникаций с вузом через GigaChat (ФТ-6).

ТЗ допускает использование ИИ для автоматизации работы с данными о вузах.
Здесь это сводка по карточке взаимодействия: этап, задачи, комментарии и
последние изменения. Сводка помогает КАМ быстро восстановить контекст перед
звонком, не перечитывая всю переписку.

Устройство:

- авторизация двухшаговая: `Authorization: Basic <ключ>` даёт токен доступа
  на 30 минут, сам запрос к модели идёт с `Authorization: Bearer <токен>`;
- токен кэшируется в памяти процесса до истечения срока, поэтому лишних
  обращений к OAuth не происходит;
- без `GIGACHAT_CREDENTIALS` функция отключена: вызывающий код получает
  `GigaChatDisabled` и возвращает 503, интерфейс скрывает кнопку;
- ошибки внешнего сервиса не пробрасываются как 500: наружу уходит
  `GigaChatUnavailable`, чтобы было видно, что проблема на стороне GigaChat.

Персональные данные в промпт не попадают: передаются только тексты
комментариев, названия задач, название вуза и продукта. СНИЛС, паспортные
данные, адреса и телефоны в карточке не хранятся — они отбрасываются ещё
на этапе импорта.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from app.core.config import get_settings

SYSTEM_PROMPT = (
    "Ты помощник менеджера по работе с вузами. По данным карточки "
    "взаимодействия составь короткую сводку на русском языке: текущий статус, "
    "что уже сделано, что требует внимания и какой следующий шаг. "
    "Не выдумывай факты, которых нет в данных. Не более 150 слов."
)

# Корневой сертификат НУЦ Минцифры. Нужен потому, что токен GigaChat выдаётся
# с сертификатом этого УЦ, которого нет в стандартном наборе доверенных корней
# Python и большинства Linux-образов. В контейнере лежит в `/certs` (монтируется
# из `certs/` репозитория), при локальном запуске берётся из `certs/` рядом с
# исходниками.
CA_FILENAME = "russian_trusted_root_ca.pem"
BUNDLED_CA_PATH = Path("/certs") / CA_FILENAME
_BACKEND_DIR = Path(__file__).resolve().parent.parent
CA_SEARCH_PATHS = (
    BUNDLED_CA_PATH,
    _BACKEND_DIR / "certs" / CA_FILENAME,
    _BACKEND_DIR.parent / "certs" / CA_FILENAME,
)

# Значение поля «Модель» для текста, собранного из данных карточки без
# обращения к GigaChat. Отдельная строка нужна, чтобы демо-сводку нельзя было
# принять за ответ модели: интерфейс показывает это поле рядом с текстом.
FALLBACK_MODEL = "демо-сводка (GigaChat не вызывался)"


class GigaChatDisabled(RuntimeError):
    """Ключ доступа не задан: функция выключена."""


class GigaChatUnavailable(RuntimeError):
    """GigaChat недоступен или вернул ошибку."""


@dataclass
class _TokenCache:
    value: str = ""
    expires_at: float = 0.0

    def is_valid(self) -> bool:
        return bool(self.value) and time.monotonic() < self.expires_at


_token_cache = _TokenCache()


def _client_kwargs() -> dict[str, Any]:
    """Параметры httpx с доверенным корнем для TLS GigaChat.

    Порядок: явный `GIGACHAT_CA_BUNDLE` → вшитый в образ сертификат НУЦ
    Минцифры → отключение проверки только если это задано явно. Отключение
    оставлено как крайняя мера для отладки: по умолчанию проверка включена.
    """
    settings = get_settings()
    kwargs: dict[str, Any] = {"timeout": settings.gigachat_timeout_seconds}
    bundle = settings.gigachat_ca_bundle
    if not bundle:
        for candidate in CA_SEARCH_PATHS:
            if candidate.is_file():
                bundle = str(candidate)
                break
    if bundle:
        kwargs["verify"] = bundle
    elif not settings.gigachat_verify_ssl:
        kwargs["verify"] = False
    return kwargs


def _get_access_token() -> str:
    """Возвращает токен доступа, при необходимости обновляя его.

    Токен живёт 30 минут. Обновление выполняется заранее
    (`GIGACHAT_TOKEN_TTL_SECONDS`), чтобы запрос не упал на границе срока.
    """
    settings = get_settings()
    if not settings.gigachat_enabled:
        raise GigaChatDisabled("GIGACHAT_CREDENTIALS не задан")
    if _token_cache.is_valid():
        return _token_cache.value

    try:
        response = httpx.post(
            settings.gigachat_auth_url,
            headers={
                "Authorization": f"Basic {settings.gigachat_credentials}",
                # RqUID обязателен: без него OAuth отвечает 400.
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"scope": settings.gigachat_scope},
            **_client_kwargs(),
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GigaChatUnavailable(f"Не удалось получить токен: {exc}") from exc

    token = payload.get("access_token")
    if not token:
        raise GigaChatUnavailable("OAuth не вернул access_token")

    _token_cache.value = token
    _token_cache.expires_at = time.monotonic() + settings.gigachat_token_ttl_seconds
    return token


def reset_token_cache() -> None:
    """Сбрасывает кэш токена. Нужен тестам."""
    _token_cache.value = ""
    _token_cache.expires_at = 0.0


def build_prompt(context: dict[str, Any]) -> str:
    """Собирает промпт из данных карточки взаимодействия."""
    lines = [
        f"Вуз: {context.get('university_name') or 'не указан'}",
        f"Продукт: {context.get('product_name') or 'не указан'}",
        f"Этап: {context.get('stage_name') or 'не указан'}",
        f"Скоуп: {context.get('scope') or 'не указан'}",
        f"Ответственный: {context.get('assigned_kam_name') or 'не назначен'}",
    ]
    if context.get("created_at"):
        lines.append(f"Создано: {context['created_at']}")

    actions = context.get("actions") or []
    if actions:
        lines.append("\nЗадачи:")
        for action in actions:
            status = "выполнена" if action.get("is_completed") else "в работе"
            due = f", срок {action['due_date']}" if action.get("due_date") else ""
            lines.append(f"- {action.get('title')} ({status}{due})")

    comments = context.get("comments") or []
    if comments:
        lines.append("\nКомментарии:")
        for comment in comments:
            lines.append(f"- {comment.get('text')}")

    return "\n".join(lines)


def summarize(context: dict[str, Any]) -> str:
    """Возвращает текстовую сводку по карточке взаимодействия."""
    settings = get_settings()
    token = _get_access_token()
    prompt = build_prompt(context)

    try:
        response = httpx.post(
            f"{settings.gigachat_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "model": settings.gigachat_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 500,
            },
            **_client_kwargs(),
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GigaChatUnavailable(f"GigaChat недоступен: {exc}") from exc

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GigaChatUnavailable("Неожиданный формат ответа GigaChat") from exc

    return str(content).strip()


def build_fallback_summary(context: dict[str, Any]) -> str:
    """Сводка из данных карточки без обращения к модели.

    Используется, когда внешний сервис недоступен, а функция включена в режиме
    демонстрации (`GIGACHAT_FALLBACK_ENABLED=true`). Текст собирается только из
    полей карточки, поэтому он детерминирован и не может содержать
    сгенерированных утверждений. Модель в ответе помечается `FALLBACK_MODEL`,
    чтобы демо-текст нельзя было принять за ответ GigaChat.
    """
    university = context.get("university_name") or "вуз не указан"
    stage = context.get("stage_name") or "этап не указан"
    product = context.get("product_name")
    scope = context.get("scope")
    kam = context.get("assigned_kam_name")

    lines = [f"Демо-сводка по взаимодействию: {university}."]
    if product:
        lines.append(f"Продукт: {product}.")
    lines.append(f"Текущий этап: {stage}.")
    if scope:
        lines.append(f"Направление: {scope}.")
    if kam:
        lines.append(f"Ответственный: {kam}.")

    actions = context.get("actions") or []
    if actions:
        done = sum(1 for a in actions if a.get("is_completed"))
        lines.append(f"Задачи: {len(actions)}, выполнено {done}.")
        pending = [a.get("title") for a in actions if not a.get("is_completed")]
        if pending:
            lines.append("В работе: " + ", ".join(str(t) for t in pending) + ".")

    comments = context.get("comments") or []
    if comments:
        last = comments[-1].get("text")
        if last:
            lines.append(f"Последний комментарий: {last}")

    return "\n".join(lines)
