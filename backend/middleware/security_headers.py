"""Заголовки безопасности ответа.

Браузерные защиты, не требующие правки каждого обработчика: запрет MIME-sniffing,
embedding во фрейм, утечки Referer и (для HTTPS) понижения до HTTP.
Документация и метрики открываются теми же заголовками, но CSP для них
намеренно не ставится: Swagger UI и /metrics содержат инлайновые скрипты.
"""

from __future__ import annotations

from app.core.config import get_settings

# Пути, которым CSP мешает (инлайновые скрипты в Swagger UI).
_CSP_EXEMPT_PREFIXES = ("/docs", "/redoc", "/openapi.json")


async def security_headers_middleware(request, call_next):
    response = await call_next(request)

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
    )

    if get_settings().is_production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )

    if not request.url.path.startswith(_CSP_EXEMPT_PREFIXES):
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )

    return response
