"""Модель комментария."""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base


class Comment(Base):
    """Комментарий к взаимодействию."""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    interaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interactions.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Связи
    interaction = relationship("Interaction", back_populates="comments")
    author = relationship("User", backref="comments")
