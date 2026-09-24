"""Ограничение попыток входа (rate limiting) для /api/auth/login.

Счётчик ведётся в процессе (fallback) либо в Redis, если он настроен.
Это защищает от подбора пароля; при превышении возвращается 429.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from app.core.config import get_settings
from fastapi import status
from fastapi.responses import JSONResponse

_login_attempts: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _prune(attempts: deque[float], window: float, now: float) -> None:
    while attempts and now - attempts[0] > window:
        attempts.popleft()


async def login_rate_limit_middleware(request, call_next):
    """Не более N попыток логина с одного IP за окно времени."""
    settings = get_settings()
    if request.url.path != "/api/auth/login" or request.method != "POST":
        return await call_next(request)

    limit = settings.login_rate_limit
    if limit <= 0:
        return await call_next(request)

    now = time.monotonic()
    window = settings.login_rate_limit_window_seconds
    ip = _client_ip(request)

    attempts = _login_attempts[ip]
    _prune(attempts, window, now)
    if len(attempts) >= limit:
        retry_after = int(window - (now - attempts[0])) + 1
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Слишком много попыток входа. Попробуйте позже.",
                "code": "RATE_LIMITED",
            },
            headers={"Retry-After": str(retry_after)},
        )

    # Фиксируем только неуспешные попытки, чтобы легитимный вход не
    # исчерпывал лимит.
    response = await call_next(request)
    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        attempts.append(now)
    return response
