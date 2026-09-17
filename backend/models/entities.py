from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Пользователь системы (роль: admin — администратор, manager — пользователь)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    actions: Mapped[list["Action"]] = relationship(back_populates="author")
    comments: Mapped[list["Comment"]] = relationship(back_populates="author")


class University(Base, TimestampMixin):
    """Учебное заведение — партнёр."""

    __tablename__ = "universities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(500), index=True)
    city: Mapped[str | None] = mapped_column(String(255))
    contact_person: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(255))

    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="university"
    )


class ITDirection(Base, TimestampMixin):
    """Направление ИТ (справочник)."""

    __tablename__ = "it_directions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    products: Mapped[list["ITProduct"]] = relationship(back_populates="direction")


class ITProduct(Base, TimestampMixin):
    """Продукт / платформа (справочник)."""

    __tablename__ = "it_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    direction_id: Mapped[int | None] = mapped_column(
        ForeignKey("it_directions.id", ondelete="SET NULL")
    )

    direction: Mapped["ITDirection | None"] = relationship(
        back_populates="products"
    )
    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="product"
    )


class WorkflowStageRef(Base, TimestampMixin):
    """Этап воркфлоу (справочник из 13 этапов, настраивается пользователем)."""

    __tablename__ = "workflow_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    order: Mapped[int] = mapped_column(Integer, unique=True)
    color: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="stage"
    )


class Interaction(Base, TimestampMixin):
    """Взаимодействие: пара [вуз + продукт], движется по этапам воркфлоу."""

    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    university_id: Mapped[int] = mapped_column(
        ForeignKey("universities.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("it_products.id", ondelete="SET NULL")
    )
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_stages.id", ondelete="RESTRICT"), index=True
    )
    contract_number: Mapped[str | None] = mapped_column(String(100))
    contract_date: Mapped[str | None] = mapped_column(String(30))
    rkn_specialist_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    university_specialist: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    university: Mapped["University"] = relationship(back_populates="interactions")
    product: Mapped["ITProduct | None"] = relationship(
        back_populates="interactions"
    )
    stage: Mapped["WorkflowStageRef"] = relationship(back_populates="interactions")
    rkn_specialist: Mapped["User | None"] = relationship()
    actions: Mapped[list["Action"]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan"
    )


class Action(Base, TimestampMixin):
    """Действие/задача по взаимодействию."""

    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interaction_id: Mapped[int] = mapped_column(
        ForeignKey("interactions.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[str | None] = mapped_column(String(30))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    interaction: Mapped["Interaction"] = relationship(back_populates="actions")
    author: Mapped["User | None"] = relationship(back_populates="actions")


class Comment(Base, TimestampMixin):
    """Комментарий к взаимодействию."""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interaction_id: Mapped[int] = mapped_column(
        ForeignKey("interactions.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    interaction: Mapped["Interaction"] = relationship(back_populates="comments")
    author: Mapped["User | None"] = relationship(back_populates="comments")
