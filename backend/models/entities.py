from app.db.base import Base, TimestampMixin
from app.models.enums import (
    USER_ROLE_VALUES,
    WORKFLOW_SCOPE_VALUES,
    UserRole,
    WorkflowScope,
)
from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(Base, TimestampMixin):
    """Пользователь системы (роль: admin — администратор, manager — менеджер, user — КАМ)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    # native_enum=False: роль хранится как VARCHAR + CHECK, а не как
    # Postgres-ENUM. Так снимается конфликт с устаревшим типом userrole,
    # который продолжает кэшировать внешний пулер после DROP TYPE,
    # и упрощается миграция между локальным Postgres и managed-кластером.
    # values_callable нужен, чтобы в БД попадали значения (admin), а не
    # имена членов перечисления (ADMIN).
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role_v2",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: USER_ROLE_VALUES,
        ),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )
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
    """Этап воркфлоу (набор этапов зависит от scope: b2b или b2c)."""

    __tablename__ = "workflow_stages"
    __table_args__ = (
        UniqueConstraint("scope", "code", name="uq_workflow_stages_scope_code"),
        UniqueConstraint("scope", "order", name="uq_workflow_stages_scope_order"),
        Index("ix_workflow_stages_scope_order", "scope", "order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Код уникален в пределах scope: b2b-набор содержит 14 этапов ТЗ,
    # b2c-набор — упрощённую воронку. Уникальность по (scope, code) и
    # (scope, order) задаётся в миграции/создаётся через create_all.
    code: Mapped[str] = mapped_column(String(50))
    scope: Mapped[WorkflowScope] = mapped_column(
        Enum(
            WorkflowScope,
            name="workflow_scope",
            native_enum=False,
            length=10,
            values_callable=lambda enum_cls: WORKFLOW_SCOPE_VALUES,
        ),
        default=WorkflowScope.B2B,
        server_default=WorkflowScope.B2B.value,
    )
    name: Mapped[str] = mapped_column(String(255))
    order: Mapped[int] = mapped_column(Integer)
    color: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="stage"
    )


class Interaction(Base, TimestampMixin):
    """Взаимодействие: пара [вуз + продукт], движется по этапам воркфлоу."""

    __tablename__ = "interactions"
    __table_args__ = (
        Index(
            "ix_interactions_stage_active",
            "stage_id",
            postgresql_where=text("is_active = true"),
        ),
        Index("ix_interactions_created_at", "created_at"),
        Index("ix_interactions_product", "product_id"),
        Index("ix_interactions_assigned_kam", "assigned_kam_id"),
        Index("ix_interactions_stage_created", "stage_id", "created_at"),
    )

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
    # Скоуп должен совпадать со scope этапа: карточка B2C не может стоять
    # в колонке B2B-воронки. Проверяется в API при создании/перемещении.
    scope: Mapped[WorkflowScope] = mapped_column(
        Enum(
            WorkflowScope,
            name="workflow_scope",
            native_enum=False,
            length=10,
            values_callable=lambda enum_cls: WORKFLOW_SCOPE_VALUES,
        ),
        default=WorkflowScope.B2B,
        server_default=WorkflowScope.B2B.value,
        index=True,
    )
    contract_number: Mapped[str | None] = mapped_column(String(100))
    contract_date: Mapped[str | None] = mapped_column(String(30))
    assigned_kam_id: Mapped[int | None] = mapped_column(
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
    assigned_kam: Mapped["User | None"] = relationship()
    actions: Mapped[list["Action"]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan"
    )
    files: Mapped[list["AttachedFile"]] = relationship(
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


class AttachedFile(Base, TimestampMixin):
    """Прикреплённый файл к взаимодействию."""

    __tablename__ = "attached_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interaction_id: Mapped[int] = mapped_column(
        ForeignKey("interactions.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    # nullable: FK объявлен с ondelete="SET NULL", значит при удалении
    # пользователя ссылка обнуляется. NOT NULL здесь ломает удаление.
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    interaction: Mapped["Interaction"] = relationship(back_populates="files")
    uploader: Mapped["User | None"] = relationship()


class ActionLog(Base, TimestampMixin):
    """Лог действий для 152-ФЗ (аудит)."""

    __tablename__ = "action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(50))  # CREATE, UPDATE, DELETE
    entity_type: Mapped[str] = mapped_column(String(50))  # Interaction, University, etc.
    entity_id: Mapped[int] = mapped_column(Integer)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(50))

    user: Mapped["User | None"] = relationship()
