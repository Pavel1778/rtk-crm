"""Модель взаимодействия."""

from datetime import date
from sqlalchemy import String, Integer, Date, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base


class Interaction(Base):
    """Взаимодействие с ВУЗом."""

    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    university_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("universities.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("it_products.id"), nullable=False
    )
    direction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("it_directions.id"), nullable=False
    )
    contract_number: Mapped[str] = mapped_column(String(100), nullable=True)
    license_sign_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    license_expiry_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_stage_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflow_stages.id"), nullable=False
    )
    assigned_kam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    university_responsible: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    # Связи
    university = relationship("University", back_populates="interactions")
    product = relationship("ITProduct", back_populates="interactions")
    direction = relationship("ITDirection", back_populates="interactions")
    current_stage = relationship("WorkflowStage", back_populates="interactions")
    assigned_kam = relationship("User", back_populates="assigned_interactions")
    history = relationship(
        "InteractionHistory", back_populates="interaction", cascade="all, delete-orphan"
    )
    files = relationship(
        "AttachedFile", back_populates="interaction", cascade="all, delete-orphan"
    )
    comments = relationship(
        "Comment", back_populates="interaction", cascade="all, delete-orphan"
    )
