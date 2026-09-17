"""Модели SQLAlchemy: справочники, взаимодействия, задачи, комментарии."""

from backend.db.base import Base
from backend.models.entities import (
    Action,
    Comment,
    Interaction,
    ITDirection,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from backend.models.enums import (
    STAGE_ORDER,
    WorkflowStage,
    next_stage,
    prev_stage,
)

__all__ = [
    "Base",
    "User",
    "University",
    "ITDirection",
    "ITProduct",
    "WorkflowStageRef",
    "Interaction",
    "Action",
    "Comment",
    "WorkflowStage",
    "STAGE_ORDER",
    "next_stage",
    "prev_stage",
]
