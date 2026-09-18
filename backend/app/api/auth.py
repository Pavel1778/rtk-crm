"""
API роутеры для аутентификации.
"""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.config import settings
from app.core.security import (
    authenticate_user_mock,
    create_access_token,
    get_current_user,
    CurrentUser,
)
from app.models.user import User
from app.schemas.auth import TokenResponse, MeResponse
from app.services.email_service import send_email


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Аутентификация пользователя и получение JWT токена.
    
    В режиме MOCK_MODE=true использует mock-аутентификацию.
    """
    user = await authenticate_user_mock(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    
    logger.info(f"Пользователь {user.username} ({user.role.value}) успешно вошёл в систему")
    
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Получение информации о текущем пользователе."""
    return MeResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        email=current_user.email,
    )


@router.post("/logout")
async def logout():
    """
    Выход из системы.
    
    В stateless JWT реализации logout выполняется на клиенте (удаление токена).
    Этот эндпоинт нужен для совместимости с фронтендом.
    """
    return {"message": "Выход выполнен успешно"}


async def send_welcome_email(user: User, db: AsyncSession):
    """Отправка приветственного письма новому пользователю."""
    if not settings.email_enabled:
        return
    
    html_body = f"""
    <html>
    <body>
        <h2>Добро пожаловать в RTK CRM!</h2>
        <p>Уважаемый {user.username},</p>
        <p>Ваша учётная запись создана. Роль: {user.role.value}.</p>
        <p>Для входа используйте систему RTK CRM.</p>
    </body>
    </html>
    """
    
    try:
        await send_email(
            to=user.email or "",
            subject="Добро пожаловать в RTK CRM",
            html_body=html_body,
        )
    except Exception as e:
        logger.error(f"Ошибка отправки приветственного письма: {e}")
