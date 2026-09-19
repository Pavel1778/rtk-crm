import enum


class WorkflowStage(str, enum.Enum):
    """Этапы воркфлоу взаимодействия с вузом (14 этапов по ТЗ).

    Порядок перечисления = порядок этапов 1..14.
    """

    CONTACT_SEARCH = "contact_search"
    COMMUNICATION = "communication"
    MEETING = "meeting"
    DOCUMENT_EXCHANGE = "document_exchange"
    DOCUMENT_REVISION = "document_revision"
    DOCUMENT_SIGNING = "document_signing"
    MATERIALS_TRANSFER = "materials_transfer"
    IMPLEMENTATION = "implementation"
    TEACHER_TRAINING = "teacher_training"
    PROGRAM_UPDATE = "program_update"
    CLASSES = "classes"
    DOCUMENTATION_UPDATE = "documentation_update"
    QUALIFICATION_UPGRADE = "qualification_upgrade"
    STAGE_CONTROL = "stage_control"

    def __str__(self) -> str:  # значение в БД, а не "WorkflowStage.LEAD"
        return self.value


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


STAGE_ORDER: list[WorkflowStage] = list(WorkflowStage)

# Название этапа для справочника (совпадает с формулировками ТЗ)
STAGE_TITLES: dict[WorkflowStage, str] = {
    WorkflowStage.CONTACT_SEARCH: "Поиск контактов ответственного в вузе",
    WorkflowStage.COMMUNICATION: "Коммуникация и уточнение актуальности программ",
    WorkflowStage.MEETING: "Организация встречи с представителями вуза",
    WorkflowStage.DOCUMENT_EXCHANGE: "Обмен пакетом документов для подписания",
    WorkflowStage.DOCUMENT_REVISION: "Корректировка документов перед подписанием",
    WorkflowStage.DOCUMENT_SIGNING: "Подписание документов",
    WorkflowStage.MATERIALS_TRANSFER: "Передача материалов, лицензии и документации",
    WorkflowStage.IMPLEMENTATION: "Сопровождение внедрения ИТ-продуктов",
    WorkflowStage.TEACHER_TRAINING: "Обучение преподавателей",
    WorkflowStage.PROGRAM_UPDATE: "Актуализация учебной программы",
    WorkflowStage.CLASSES: "Ведение занятий",
    WorkflowStage.DOCUMENTATION_UPDATE: "Актуализация документации по продукту",
    WorkflowStage.QUALIFICATION_UPGRADE: "Повышение квалификации преподавателей",
    WorkflowStage.STAGE_CONTROL: "Контроль за исполнением каждого этапа",
}

# Цвет колонки канбан-доски по порядковому номеру этапа (1..14)
STAGE_COLORS: list[str] = [
    "#8c8c8c",
    "#1677ff",
    "#13c2c2",
    "#2f54eb",
    "#722ed1",
    "#eb2f96",
    "#f5222d",
    "#fa8c16",
    "#faad14",
    "#a0d911",
    "#52c41a",
    "#389e0d",
    "#237804",
    "#08979c",
]


def stage_seed_rows() -> list[tuple[str, str, int, str]]:
    """Строки справочника этапов: (код, название, порядок, цвет)."""
    return [
        (stage.value, STAGE_TITLES[stage], order, STAGE_COLORS[order - 1])
        for order, stage in enumerate(STAGE_ORDER, start=1)
    ]


def next_stage(stage: WorkflowStage) -> WorkflowStage | None:
    """Следующий этап или None, если процесс завершён."""
    idx = STAGE_ORDER.index(stage)
    return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else None


def prev_stage(stage: WorkflowStage) -> WorkflowStage | None:
    """Предыдущий этап или None, если это первый этап."""
    idx = STAGE_ORDER.index(stage)
    return STAGE_ORDER[idx - 1] if idx > 0 else None
