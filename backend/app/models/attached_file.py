"""Модель прикреплённого файла."""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base


class AttachedFile(Base):
    """Прикреплённый файл к взаимодействию."""

    __tablename__ = "attached_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    interaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interactions.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Связи
    interaction = relationship("Interaction", back_populates="files")
    uploader = relationship("User", backref="uploaded_files")
