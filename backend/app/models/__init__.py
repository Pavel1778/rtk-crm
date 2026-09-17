"""Экспорт всех моделей для Alembic и SQLAlchemy."""
from app.models.base import Base
from app.models.user import User, UserRole
from app.models.university import University
from app.models.it_product import ITProduct
from app.models.it_direction import ITDirection
from app.models.workflow_stage import WorkflowStage
from app.models.interaction import Interaction
from app.models.interaction_history import InteractionHistory
from app.models.action_log import ActionLog
from app.models.attached_file import AttachedFile
from app.models.comment import Comment

__all__ = [
    "Base",
    "User", "UserRole",
    "University",
    "ITProduct",
    "ITDirection",
    "WorkflowStage",
    "Interaction",
    "InteractionHistory",
    "ActionLog",
    "AttachedFile",
    "Comment",
]
