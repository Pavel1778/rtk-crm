from datetime import UTC, datetime, timedelta
from typing import Any

from app.auth.keycloak import (
    KeycloakUnavailable,
    TokenValidationError,
    decode_token,
    roles_from_claims,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import UserRole
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10,
)
bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Некорректные учётные данные",
    headers={"WWW-Authenticate": "Bearer"},
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user: User) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user.id), "email": user.email, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Извлекает пользователя из Bearer-токена.

    В режиме `AUTH_MODE=keycloak` подпись и claims проверяет Keycloak через
    JWKS, но возвращается всё равно локальная запись `User`: она нужна для
    связей в БД (автор комментария, исполнитель) и для RBAC по `role`.
    Связь между аккаунтами — по email из токена (`preferred_username` или
    `email`), поэтому учётную запись достаточно завести один раз.
    """
    if credentials is None:
        raise CREDENTIALS_ERROR from None

    settings = get_settings()
    if settings.auth_mode.lower() == "keycloak":
        user = await _user_from_keycloak_token(
            credentials.credentials, request, db
        )
    else:
        user = await _user_from_local_token(credentials.credentials, request, db)

    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    request.state.user = user
    return user


async def _user_from_local_token(
    token: str, request: Request, db: AsyncSession
) -> User | None:
    """Путь JWT: HS256-подпись локальным секретом, `sub` — id пользователя."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError, TypeError):
        raise CREDENTIALS_ERROR from None

    return await db.scalar(select(User).where(User.id == user_id))


async def _user_from_keycloak_token(
    token: str, request: Request, db: AsyncSession
) -> User | None:
    """Путь Keycloak: RS256 по JWKS, затем поиск локальной учётной записи."""
    try:
        claims = decode_token(token)
    except KeycloakUnavailable as exc:
        # 503, а не 401: токен может быть корректным, проблема в Keycloak.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис аутентификации недоступен",
        ) from exc
    except TokenValidationError:
        raise CREDENTIALS_ERROR from None

    email = claims.get("email") or claims.get("preferred_username")
    if not email:
        raise CREDENTIALS_ERROR from None

    user = await db.scalar(select(User).where(User.email == email))
    if user is not None:
        # Роли в токене — источник истины для RBAC. Локальная роль
        # синхронизируется, потому что часть проверок (например, доступ КАМ
        # к своим карточкам) читает поле role напрямую.
        role = _role_from_keycloak_claims(claims)
        if user.role is not role or user.is_admin is not (role is UserRole.ADMIN):
            user.role = role
            user.is_admin = role is UserRole.ADMIN
            await db.commit()
        request.state.keycloak_roles = roles_from_claims(claims)
        return user

    # Аккаунт в Keycloak есть, а в CRM ещё нет: заводим по данным токена,
    # иначе пользователь не сможет войти без ручного создания учётки.
    role = _role_from_keycloak_claims(claims)
    user = User(
        email=email,
        full_name=claims.get("name") or email,
        hashed_password="!keycloak",  # локальный вход паролем запрещён
        role=role,
        is_admin=role is UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    request.state.keycloak_roles = roles_from_claims(claims)
    return user


def _role_from_keycloak_claims(claims: dict[str, Any]) -> UserRole:
    """Сопоставляет роли Keycloak роли CRM.

    Приоритет: admin > manager > user (КАМ). Неизвестные роли Keycloak
    игнорируются — наименьшие привилегии по умолчанию.
    """
    roles = {r.lower() for r in roles_from_claims(claims)}
    if "admin" in roles:
        return UserRole.ADMIN
    if "manager" in roles:
        return UserRole.MANAGER
    return UserRole.USER



def _effective_roles(request: Request, user: User) -> set[str]:
    """Роли пользователя для проверки доступа.

    В режиме keycloak источник истины — роли из токена
    (`request.state.keycloak_roles`). В режиме jwt используется роль из БД.
    """
    token_roles = getattr(request.state, "keycloak_roles", None)
    if token_roles is not None:
        return {r.lower() for r in token_roles}
    return {user.role.value}


async def require_admin(
    request: Request,
    user: User = Depends(get_current_user),
) -> User:
    """Доступ только для администратора (роль admin)."""
    roles = _effective_roles(request, user)
    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора",
        )
    return user


async def require_manager_or_admin(
    request: Request,
    user: User = Depends(get_current_user),
) -> User:
    """Доступ к справочникам только менеджеру или администратору."""
    roles = _effective_roles(request, user)
    if not roles & {"manager", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль менеджера или администратора",
        )
    return user
