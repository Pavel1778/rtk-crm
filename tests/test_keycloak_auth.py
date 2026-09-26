"""Аутентификация через Keycloak: проверка токенов по JWKS и RBAC.

Keycloak как внешний сервис в тестах не поднимается. Вместо этого
генерируется настоящая пара RSA-ключей, публичная часть отдаётся через
подменённый JWKS-эндпоинт, а токены подписываются приватным ключом. Так
проверяется реальный путь проверки подписи (RS256, kid, iss, exp), а не
заглушка самого валидатора.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import pytest
import pytest_asyncio
from app.auth import keycloak as kc
from app.auth.security import create_access_token, hash_password
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.entities import User
from app.models.enums import UserRole
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from jose import jwt

REALM = "rtk-crm"
KID = "test-key-1"
ISSUER = f"http://keycloak.test/realms/{REALM}"


def _generate_keypair() -> tuple[str, dict[str, Any]]:
    """Создаёт RSA-ключ и его публичную часть в формате JWK."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_numbers = private_key.public_key().public_numbers()

    def b64(value: int, length: int) -> str:
        import base64

        return base64.urlsafe_b64encode(
            value.to_bytes(length, "big")
        ).rstrip(b"=").decode()

    jwk = {
        "kty": "RSA",
        "kid": KID,
        "use": "sig",
        "alg": "RS256",
        "n": b64(public_numbers.n, 256),
        "e": b64(public_numbers.e, 3),
    }
    return private_pem, jwk


@pytest.fixture(scope="module")
def rsa_keys() -> tuple[str, dict[str, Any]]:
    return _generate_keypair()


def jwks_response(url: str, jwk: dict[str, Any]) -> httpx.Response:
    """Ответ JWKS с привязанным request: без него падает raise_for_status."""
    return httpx.Response(
        200, json={"keys": [jwk]}, request=httpx.Request("GET", url)
    )


@pytest.fixture(autouse=True)
def _keycloak_env(monkeypatch: pytest.MonkeyPatch, rsa_keys):
    """Переводит приложение в режим keycloak и подменяет JWKS-эндпоинт."""
    private_pem, jwk = rsa_keys
    monkeypatch.setenv("AUTH_MODE", "keycloak")
    monkeypatch.setenv("KEYCLOAK_URL", "http://keycloak.test")
    monkeypatch.setenv("KEYCLOAK_REALM", REALM)
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "rtk-crm-frontend")
    monkeypatch.setenv("KEYCLOAK_AUDIENCE", "rtk-crm-frontend")
    get_settings.cache_clear()
    kc.reset_cache()

    def fake_get(url: str, **kwargs: Any) -> httpx.Response:
        if url == f"{ISSUER}/protocol/openid-connect/certs":
            return jwks_response(url, jwk)
        raise AssertionError(f"Неожиданный запрос к Keycloak: {url}")

    monkeypatch.setattr(kc.httpx, "get", fake_get)
    yield private_pem
    get_settings.cache_clear()
    kc.reset_cache()


def make_token(
    private_pem: str,
    *,
    email: str = "kam@t.ru",
    roles: list[str] | None = None,
    expires_in: int = 300,
    issuer: str = ISSUER,
    audience: str = "rtk-crm-frontend",
    kid: str = KID,
    include_email: bool = True,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": "kc-user-1",
        "iss": issuer,
        "aud": audience,
        "exp": now + expires_in,
        "iat": now,
        "preferred_username": email,
        "realm_access": {"roles": roles if roles is not None else ["kam"]},
    }
    if include_email:
        claims["email"] = email
        claims["name"] = "Тестовый Пользователь"
    return jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": kid})


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add(
            User(
                email="kam@t.ru",
                full_name="КАМ Существующий",
                role=UserRole.USER,
                is_admin=False,
                hashed_password=hash_password("pass"),
            )
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_valid_token_authenticates_existing_user(
    client: AsyncClient, _keycloak_env: str
) -> None:
    token = make_token(_keycloak_env)
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "kam@t.ru"


async def test_unknown_keycloak_user_is_provisioned(
    client: AsyncClient, _keycloak_env: str
) -> None:
    """Пользователь есть в Keycloak, но не в CRM: учётка создаётся."""
    token = make_token(_keycloak_env, email="new@t.ru", roles=["manager"])
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "new@t.ru"

    async with SessionLocal() as session:
        from sqlalchemy import select

        user = await session.scalar(select(User).where(User.email == "new@t.ru"))
    assert user is not None
    assert user.role is UserRole.MANAGER
    # Локальный вход паролем для Keycloak-пользователя невозможен.
    assert user.hashed_password == "!keycloak"


async def test_expired_token_rejected(
    client: AsyncClient, _keycloak_env: str
) -> None:
    token = make_token(_keycloak_env, expires_in=-60)
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


async def test_wrong_issuer_rejected(
    client: AsyncClient, _keycloak_env: str
) -> None:
    token = make_token(_keycloak_env, issuer="http://evil.test/realms/rtk-crm")
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


async def test_wrong_audience_rejected(
    client: AsyncClient, _keycloak_env: str
) -> None:
    token = make_token(_keycloak_env, audience="other-client")
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


async def test_token_signed_by_foreign_key_rejected(
    client: AsyncClient, _keycloak_env: str
) -> None:
    """Токен подписан другим ключом, но с верным kid: подпись не сходится."""
    foreign_pem, _ = _generate_keypair()
    token = make_token(foreign_pem)
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


async def test_unknown_kid_triggers_refresh_and_rejects(
    client: AsyncClient, _keycloak_env: str
) -> None:
    token = make_token(_keycloak_env, kid="nonexistent-kid")
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


async def test_keycloak_unavailable_returns_503(
    client: AsyncClient, _keycloak_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Сбой Keycloak — это 503, а не 401: токен может быть корректным."""
    kc.reset_cache()

    def failing_get(url: str, **kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(kc.httpx, "get", failing_get)
    token = make_token(_keycloak_env)
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 503


async def test_admin_route_denied_for_kam_role(
    client: AsyncClient, _keycloak_env: str
) -> None:
    token = make_token(_keycloak_env, roles=["kam"])
    response = await client.get(
        "/api/auth/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


async def test_admin_route_allowed_for_admin_role(
    client: AsyncClient, _keycloak_env: str
) -> None:
    """Роль из токена даёт доступ, даже если локальная роль — user."""
    token = make_token(_keycloak_env, roles=["admin"])
    response = await client.get(
        "/api/auth/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


async def test_client_roles_are_honored(
    client: AsyncClient, _keycloak_env: str
) -> None:
    """Роли клиента (resource_access) участвуют в RBAC наравне с realm."""
    token = jwt.encode(
        {
            "sub": "kc-user-1",
            "iss": ISSUER,
            "aud": "rtk-crm-frontend",
            "exp": int(time.time()) + 300,
            "iat": int(time.time()),
            "email": "kam@t.ru",
            "preferred_username": "kam@t.ru",
            "realm_access": {"roles": []},
            "resource_access": {"rtk-crm-frontend": {"roles": ["manager"]}},
        },
        _keycloak_env,
        algorithm="RS256",
        headers={"kid": KID},
    )
    response = await client.get(
        "/api/auth/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


async def test_preferred_username_is_used_when_email_absent(
    client: AsyncClient, _keycloak_env: str
) -> None:
    """Без claim email логин берётся из preferred_username."""
    token = make_token(_keycloak_env, include_email=False)
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "kam@t.ru"


async def test_token_without_any_identity_claim_rejected(
    client: AsyncClient, _keycloak_env: str
) -> None:
    """Нет ни email, ни preferred_username — сопоставить учётку нечем."""
    token = jwt.encode(
        {
            "sub": "kc-user-1",
            "iss": ISSUER,
            "aud": "rtk-crm-frontend",
            "exp": int(time.time()) + 300,
            "iat": int(time.time()),
            "realm_access": {"roles": ["kam"]},
        },
        _keycloak_env,
        algorithm="RS256",
        headers={"kid": KID},
    )
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


async def test_jwt_mode_still_works(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Переключение на jwt возвращает локальный вход без Keycloak."""
    monkeypatch.setenv("AUTH_MODE", "jwt")
    get_settings.cache_clear()
    try:
        async with SessionLocal() as session:
            from sqlalchemy import select

            user = await session.scalar(select(User).where(User.email == "kam@t.ru"))
            assert user is not None
            token = create_access_token(user)
        response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == "kam@t.ru"
    finally:
        get_settings.cache_clear()


async def test_jwks_is_cached_between_requests(
    client: AsyncClient, _keycloak_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Повторные запросы не ходят в Keycloak: ключи берутся из кэша."""
    calls = {"n": 0}
    _, jwk = _generate_keypair()

    def counting_get(url: str, **kwargs: Any) -> httpx.Response:
        calls["n"] += 1
        return jwks_response(url, jwk)

    kc.reset_cache()
    monkeypatch.setattr(kc.httpx, "get", counting_get)
    token = make_token(_keycloak_env)

    for _ in range(3):
        response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401  # подпись не сходится: ключ другой

    # Три запроса — одно обращение к JWKS, дальше работает кэш.
    assert calls["n"] == 1


async def test_roles_from_claims_merges_both_scopes() -> None:
    claims = {
        "realm_access": {"roles": ["kam"]},
        "resource_access": {"rtk-crm-frontend": {"roles": ["manager"]}},
    }
    assert set(kc.roles_from_claims(claims)) == {"kam", "manager"}


async def test_decode_rejects_token_without_kid(
    _keycloak_env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    kc.reset_cache()
    token = jwt.encode(
        {"sub": "x", "iss": ISSUER, "aud": "rtk-crm-frontend", "exp": 9999999999},
        _keycloak_env,
        algorithm="RS256",
    )
    with pytest.raises(kc.TokenValidationError):
        kc.decode_token(token)


async def test_jwks_without_usable_keys_raises_unavailable(
    monkeypatch: pytest.MonkeyPatch, rsa_keys
) -> None:
    """Realm отдал JWKS без RSA-ключей: это недоступность, а не 401."""
    private_pem, _ = rsa_keys
    kc.reset_cache()

    def empty_jwks(url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(
            200, json={"keys": []}, request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(kc.httpx, "get", empty_jwks)
    token = make_token(private_pem)
    with pytest.raises(kc.KeycloakUnavailable):
        kc.get_signing_key(token, force_refresh=True)


async def test_alg_none_token_rejected(
    client: AsyncClient, _keycloak_env: str
) -> None:
    """Токен с alg=none не принимается: подпись обязательна."""
    import base64

    def b64(obj: dict[str, Any]) -> str:
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    forged = f"{b64({'alg': 'none', 'kid': KID})}.{b64({'sub': 'x'})}."
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {forged}"}
    )
    assert response.status_code == 401


def test_realm_export_is_valid_json() -> None:
    """Realm-файл должен импортироваться в Keycloak: проверяем структуру."""
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "keycloak" / "realm-export.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["realm"] == "rtk-crm"
    role_names = {r["name"] for r in data["roles"]["realm"]}
    assert role_names == {"admin", "manager", "kam"}

    client = data["clients"][0]
    assert client["clientId"] == "rtk-crm-frontend"
    assert client["publicClient"] is True
    # PKCE обязателен для публичного клиента.
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"

    users = {u["username"]: u for u in data["users"]}
    assert users["admin@rtk-crm.local"]["realmRoles"] == ["admin"]
