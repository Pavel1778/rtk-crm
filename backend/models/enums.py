import enum


class WorkflowStage(str, enum.Enum):
    """Этапы воркфлоу взаимодействия с вузом (13 этапов)."""

    LEAD = "lead"
    MEETING = "meeting"
    COMMERCIAL_PROPOSAL = "commercial_proposal"
    CONTRACT = "contract"
    LICENSE = "license"
    IMPLEMENTATION = "implementation"
    ACADEMY = "academy"
    EXAMS = "exams"
    RANKING = "ranking"
    GRANTS = "grants"
    CONFERENCE = "conference"
    EXTENSION = "extension"
    DONE = "done"

    def __str__(self) -> str:  # значение в БД, а не "WorkflowStage.LEAD"
        return self.value


STAGE_ORDER: list[WorkflowStage] = list(WorkflowStage)


def next_stage(stage: WorkflowStage) -> WorkflowStage | None:
    """Следующий этап или None, если процесс завершён."""
    idx = STAGE_ORDER.index(stage)
    return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else None


def prev_stage(stage: WorkflowStage) -> WorkflowStage | None:
    """Предыдущий этап или None, если это первый этап."""
    idx = STAGE_ORDER.index(stage)
    return STAGE_ORDER[idx - 1] if idx > 0 else None
