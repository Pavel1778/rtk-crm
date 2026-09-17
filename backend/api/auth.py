from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import (
    get_current_user,
    hash_password,
    require_admin,
    create_access_token,
    verify_password,
)
from backend.db.session import get_db
from backend.models.entities import User
from backend.schemas.entities import (
    LoginRequest,
    Token,
    UserCreate,
    UserRead,
    UserUpdate,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> Token:
    """Вход по email/паролю. Возвращает Bearer-токен и данные пользователя."""
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись отключена",
        )
    return Token(access_token=create_access_token(user), user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    """Создание пользователя (только администратор)."""
    exists = await db.scalar(select(User.id).where(User.email == payload.email))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует",
        )
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        is_admin=payload.is_admin,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[User]:
    result = await db.scalars(select(User).order_by(User.full_name))
    return list(result)


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        password = data.pop("password")
        if password:
            user.hashed_password = hash_password(password)
    if "email" in data and data["email"] != user.email:
        clash = await db.scalar(
            select(User.id).where(User.email == data["email"], User.id != user_id)
        )
        if clash:
            raise HTTPException(
                status_code=409, detail="Пользователь с таким email уже существует"
            )
    for field, value in data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_admin),
) -> None:
    """Удаление пользователя. Нельзя удалить собственную учётную запись."""
    if user_id == current.id:
        raise HTTPException(
            status_code=400, detail="Нельзя удалить собственную учётную запись"
        )
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    await db.delete(user)
    await db.commit()
