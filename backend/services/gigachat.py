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
from typing import Any

import httpx
from app.core.config import get_settings

SYSTEM_PROMPT = (
    "Ты помощник менеджера по работе с вузами. По данным карточки "
    "взаимодействия составь короткую сводку на русском языке: текущий статус, "
    "что уже сделано, что требует внимания и какой следующий шаг. "
    "Не выдумывай факты, которых нет в данных. Не более 150 слов."
)


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
    settings = get_settings()
    kwargs: dict[str, Any] = {"timeout": settings.gigachat_timeout_seconds}
    if settings.gigachat_ca_bundle:
        kwargs["verify"] = settings.gigachat_ca_bundle
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
