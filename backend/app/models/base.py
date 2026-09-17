"""Базовый класс SQLAlchemy 2.0."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Общий DeclarativeBase для всех моделей."""
    pass
