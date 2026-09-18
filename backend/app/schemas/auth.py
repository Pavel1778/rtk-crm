"""
Схемы Pydantic для аутентификации.
"""
from pydantic import BaseModel


class TokenResponse(BaseModel):
    """Ответ с JWT токеном."""
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    """Информация о текущем пользователе."""
    id: int
    username: str
    role: str
    email: str | None = None


class LoginRequest(BaseModel):
    """Запрос на вход."""
    username: str
    password: str
