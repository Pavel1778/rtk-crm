"""Модель истории взаимодействия."""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base


class InteractionHistory(Base):
    """История изменений взаимодействия."""

    __tablename__ = "interaction_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    interaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interactions.id"), nullable=False
    )
    from_stage_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("workflow_stages.id"), nullable=True
    )
    to_stage_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflow_stages.id"), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Связи
    interaction = relationship("Interaction", back_populates="history")
    from_stage = relationship(
        "WorkflowStage", foreign_keys=[from_stage_id], backref="history_from"
    )
    to_stage = relationship(
        "WorkflowStage", foreign_keys=[to_stage_id], backref="history_to"
    )
    user = relationship("User", backref="history_changes")
