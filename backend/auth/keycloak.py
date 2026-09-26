"""Проверка токенов Keycloak по публичным ключам realm (JWKS).

Модуль не делает запрос к Keycloak на каждый HTTP-запрос: набор ключей
кэшируется на `KEYCLOAK_JWKS_TTL_SECONDS`. Если в токене встретился
неизвестный `kid`, кэш сбрасывается и ключи запрашиваются заново — так
обрабатывается плановая ротация ключей в realm без перезапуска сервиса.

Сетевые ошибки при обновлении ключей не считаются ошибкой аутентификации
пользователя: они поднимаются как `KeycloakUnavailable`, чтобы вызывающий
код вернул 503, а не 401, и было видно, что проблема на стороне Keycloak.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from app.core.config import get_settings
from jose import jwt
from jose.exceptions import JWTError


class KeycloakUnavailable(RuntimeError):
    """Keycloak недоступен: не удалось получить JWKS."""


class TokenValidationError(ValueError):
    """Токен не прошёл проверку подписи, срока или обязательных claims."""


@dataclass
class _JwksCache:
    keys: dict[str, dict[str, Any]] = field(default_factory=dict)
    fetched_at: float = 0.0

    def is_fresh(self, ttl: int) -> bool:
        return bool(self.keys) and (time.monotonic() - self.fetched_at) < ttl


_cache = _JwksCache()


def _issuer() -> str:
    settings = get_settings()
    return f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}"


def _fetch_jwks() -> dict[str, dict[str, Any]]:
    """Загружает набор ключей realm и раскладывает его по `kid`."""
    settings = get_settings()
    url = f"{_issuer()}/protocol/openid-connect/certs"
    try:
        response = httpx.get(url, timeout=settings.keycloak_jwks_timeout_seconds)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise KeycloakUnavailable(f"JWKS недоступен: {exc}") from exc

    keys: dict[str, dict[str, Any]] = {}
    for key in payload.get("keys", []):
        kid = key.get("kid")
        # Ключи без kid использовать нельзя: сопоставить токен с ключом
        # можно только по идентификатору из заголовка.
        if kid and key.get("kty") == "RSA":
            keys[kid] = key
    if not keys:
        raise KeycloakUnavailable("В JWKS нет пригодных RSA-ключей")
    return keys


def get_signing_key(token: str, *, force_refresh: bool = False) -> dict[str, Any]:
    """Возвращает публичный ключ, которым подписан токен."""
    settings = get_settings()
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except JWTError as exc:
        raise TokenValidationError(f"Некорректный заголовок токена: {exc}") from exc
    except Exception as exc:
        # Повреждённый base64 в токене даёт binascii.Error, а не JWTError.
        # Любой нечитаемый токен — это ошибка аутентификации, а не 500.
        raise TokenValidationError(f"Токен нечитаем: {exc}") from exc
    if not kid:
        raise TokenValidationError("В токене отсутствует kid")

    if force_refresh or not _cache.is_fresh(settings.keycloak_jwks_ttl_seconds):
        _cache.keys = _fetch_jwks()
        _cache.fetched_at = time.monotonic()

    key = _cache.keys.get(kid)
    if key is None and not force_refresh:
        # Неизвестный kid — вероятно, ключи в realm обновились.
        _cache.keys = _fetch_jwks()
        _cache.fetched_at = time.monotonic()
        key = _cache.keys.get(kid)
    if key is None:
        raise TokenValidationError(f"Ключ {kid} не найден в JWKS")
    return key


def decode_token(token: str) -> dict[str, Any]:
    """Проверяет подпись и claims токена, возвращает его полезную нагрузку."""
    settings = get_settings()
    options = {"verify_aud": bool(settings.keycloak_audience)}
    try:
        return jwt.decode(
            token,
            get_signing_key(token),
            algorithms=["RS256"],
            issuer=_issuer(),
            audience=settings.keycloak_audience or None,
            options=options,
        )
    except JWTError as exc:
        raise TokenValidationError(f"Токен не прошёл проверку: {exc}") from exc


def reset_cache() -> None:
    """Сбрасывает кэш ключей. Нужен тестам и ручному обновлению."""
    _cache.keys = {}
    _cache.fetched_at = 0.0


def roles_from_claims(claims: dict[str, Any]) -> list[str]:
    """Собирает роли пользователя из realm- и client-областей токена.

    Keycloak различает роли realm (`realm_access`) и роли клиента
    (`resource_access.<client_id>`). В RBAC системы участвуют обе группы.
    """
    settings = get_settings()
    roles = list(claims.get("realm_access", {}).get("roles", []))
    client_roles = (
        claims.get("resource_access", {})
        .get(settings.keycloak_client_id, {})
        .get("roles", [])
    )
    roles.extend(client_roles)
    return roles
