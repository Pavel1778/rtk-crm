"""Интеграция с внешними системами заказчика: LMS и CMS сайта (ФТ-5).

По Q&A кейсодержателя интеграция двусторонняя:

* **Входящая** — CRM забирает данные из LMS и CMS по API в формате JSON и
  раскладывает их по существующему или новому workflow.
* **Исходящая** — CRM отдаёт выгрузку (`GET /api/reports/json`) с ключами
  связи БД и S3, чтобы принимающая сторона сопоставила объекты.

Контракт с внешней стороны на момент разработки не предоставлен, поэтому
внешние системы здесь представлены заглушками: они отдают JSON по
утверждённым полям и принимают исходящие пакеты. Разбор входящего JSON —
реальный: та же схема, что согласована для LMS/CMS, поэтому замена заглушки
на живой эндпоинт сводится к смене URL в конфиге.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# Утверждённые поля входящего пакета. Источник может передать подмножество —
# отсутствующие ключи не считаются ошибкой, а попадают в warnings.
REQUIRED_FIELDS: tuple[str, ...] = ("external_id", "university")
OPTIONAL_FIELDS: tuple[str, ...] = (
    "product",
    "direction",
    "stage_code",
    "scope",
    "contract_number",
    "contract_date",
    "assigned_kam_email",
    "university_specialist",
    "notes",
)

KNOWN_FIELDS: frozenset[str] = frozenset(REQUIRED_FIELDS + OPTIONAL_FIELDS)

SourceSystem = Literal["lms", "cms"]


@dataclass
class ParsedRecord:
    """Разобранная запись входящего пакета."""

    external_id: str
    university: str
    product: str | None = None
    direction: str | None = None
    stage_code: str | None = None
    scope: str = "b2b"
    contract_number: str | None = None
    contract_date: str | None = None
    assigned_kam_email: str | None = None
    university_specialist: str | None = None
    notes: str | None = None


@dataclass
class ParseResult:
    """Итог разбора пакета: валидные записи и причины отбраковки."""

    records: list[ParsedRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unknown_fields: set[str] = field(default_factory=set)

    @property
    def total(self) -> int:
        return len(self.records) + len(self.errors)


def _clean(value: Any) -> str | None:
    """Нормализует скаляр к строке; пустые значения приводит к None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_payload(payload: Any) -> ParseResult:
    """Разбирает входящий JSON в записи.

    Принимает как список записей, так и объект с ключом ``items`` — оба
    варианта встречаются в выгрузках LMS и CMS. ``null`` в начале массива
    (встречается в реальных выгрузках заказчика) пропускается, а не роняет
    разбор.
    """
    result = ParseResult()

    if isinstance(payload, dict):
        items = payload.get("items", payload.get("records"))
        if items is None:
            result.errors.append("Ожидался массив записей или объект с ключом 'items'")
            return result
    else:
        items = payload

    if not isinstance(items, list):
        result.errors.append("Поле 'items' должно быть массивом")
        return result

    for index, raw in enumerate(items):
        # `null` внутри массива — легитимный случай, пропускаем без ошибки.
        if raw is None:
            result.warnings.append(f"Строка {index + 1}: пустое значение пропущено")
            continue
        if not isinstance(raw, dict):
            result.errors.append(f"Строка {index + 1}: ожидался объект")
            continue

        result.unknown_fields.update(set(raw) - KNOWN_FIELDS)

        external_id = _clean(raw.get("external_id"))
        university = _clean(raw.get("university"))
        if not external_id:
            result.errors.append(f"Строка {index + 1}: не указан 'external_id'")
            continue
        if not university:
            result.errors.append(
                f"Строка {index + 1} ({external_id}): не указан 'university'"
            )
            continue

        scope = (_clean(raw.get("scope")) or "b2b").lower()
        if scope not in {"b2b", "b2c"}:
            result.warnings.append(
                f"Строка {index + 1} ({external_id}): неизвестный scope '{scope}', "
                "применён b2b"
            )
            scope = "b2b"

        result.records.append(
            ParsedRecord(
                external_id=external_id,
                university=university,
                product=_clean(raw.get("product")),
                direction=_clean(raw.get("direction")),
                stage_code=_clean(raw.get("stage_code")),
                scope=scope,
                contract_number=_clean(raw.get("contract_number")),
                contract_date=_clean(raw.get("contract_date")),
                assigned_kam_email=_clean(raw.get("assigned_kam_email")),
                university_specialist=_clean(raw.get("university_specialist")),
                notes=_clean(raw.get("notes")),
            )
        )

    if result.unknown_fields:
        result.warnings.append(
            "Неизвестные поля проигнорированы: "
            + ", ".join(sorted(result.unknown_fields))
        )
    return result


def stub_lms_payload() -> dict[str, Any]:
    """Заглушка ответа LMS по утверждённым полям.

    Заменяется на реальный вызов при появлении контракта от заказчика.
    """
    return {
        "source": "lms",
        "items": [
            {
                "external_id": "LMS-1001",
                "university": "МГТУ им. Н. Э. Баумана",
                "product": "RUBOTYAKA",
                "direction": "Информационная безопасность",
                "stage_code": "teacher_training",
                "scope": "b2b",
                "contract_number": "LMS-2026/17",
                "university_specialist": "Иванов И. И.",
                "notes": "Загружено из LMS (заглушка)",
            },
            {
                "external_id": "LMS-1002",
                "university": "ИТМО",
                "product": "Skill Portal",
                "direction": "Разработка ПО",
                "stage_code": "implementation",
                "scope": "b2b",
                "university_specialist": "Петров П. П.",
                "notes": "Загружено из LMS (заглушка)",
            },
        ],
    }


def stub_cms_payload() -> dict[str, Any]:
    """Заглушка ответа CMS сайта по утверждённым полям."""
    return {
        "source": "cms",
        "items": [
            {
                "external_id": "CMS-2043",
                "university": "Университет ИТЭГ",
                "product": "Cyber Range",
                "direction": "Информационная безопасность",
                "stage_code": "meeting",
                "scope": "b2b",
                "contract_number": "CMS-2026/88",
                "university_specialist": "Сидоров С. С.",
                "notes": "Загружено из CMS сайта (заглушка)",
            },
            {
                "external_id": "CMS-2044",
                "university": "НГУ",
                "product": "AI Studio",
                "direction": "Искусственный интеллект",
                "stage_code": "communication",
                "scope": "b2b",
                "university_specialist": "Смирнова Е. В.",
                "notes": "Загружено из CMS сайта (заглушка)",
            },
        ],
    }


def fetch_stub(source: SourceSystem) -> dict[str, Any]:
    """Возвращает пакет от заглушки нужной внешней системы."""
    return stub_lms_payload() if source == "lms" else stub_cms_payload()
