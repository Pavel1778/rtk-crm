"""Импорт каталогов из XLS и XLSX файлов."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    import xlrd
except ImportError:  # pragma: no cover
    xlrd = None

try:
    from jsonschema import Draft7Validator
except ImportError:  # pragma: no cover
    Draft7Validator = None

try:
    from openpyxl import load_workbook
except ImportError:  # pragma: no cover
    load_workbook = None


# Типы проблем отчёта о валидации: ошибка блокирует строку, предупреждение — нет.
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_OK = "ok"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class ValidationIssue:
    """Одна проблема в строке импорта: где, что и почему."""

    row: int | None
    field: str
    problem: str
    severity: str = SEVERITY_ERROR
    value: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "row": self.row,
            "field": self.field,
            "problem": self.problem,
            "severity": self.severity,
            "value": self.value,
        }


class CatalogImportResult:
    """Нормализованный результат импорта каталога."""

    def __init__(
        self,
        success: bool,
        data: list[dict[str, Any]],
        errors: list[str] | None = None,
        headers: list[str] | None = None,
        issues: list[ValidationIssue] | None = None,
        total_rows: int | None = None,
    ):
        self.success = success
        self.data = data
        self.errors = errors or []
        self.headers = headers or []
        self.issues = list(issues) if issues is not None else []
        # Если отчёт не передан, синтезируем его из плоского списка ошибок,
        # чтобы потребители старых вызовов видели те же данные.
        if issues is None:
            self.issues = [
                ValidationIssue(row=None, field="", problem=message)
                for message in self.errors
            ]
        self.total_rows = total_rows if total_rows is not None else len(data)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == SEVERITY_ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == SEVERITY_WARNING)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "headers": self.headers,
            "data": self.data,
            "errors": self.errors,
            "count": len(self.data),
            "issues": [issue.to_dict() for issue in self.issues],
            "summary": {
                "total_rows": self.total_rows,
                "valid_rows": len(self.data),
                "warning_rows": len(
                    {
                        issue.row
                        for issue in self.issues
                        if issue.severity == SEVERITY_WARNING
                    }
                ),
                "error_rows": len(
                    {
                        issue.row
                        for issue in self.issues
                        if issue.severity == SEVERITY_ERROR
                    }
                ),
                "error_count": self.error_count,
                "warning_count": self.warning_count,
            },
        }


def parse_catalog_file(
    file: BytesIO,
    catalog_type: str,
    filename: str | None = None,
    mapping: dict[str, str] | None = None,
) -> CatalogImportResult:
    """Разбирает XLS/XLSX и приводит его к общей структуре строк."""
    if catalog_type not in {"universities", "products"}:
        return CatalogImportResult(
            success=False,
            data=[],
            errors=[f"Неизвестный тип каталога: {catalog_type}"],
        )

    suffix = Path(filename or "").suffix.lower() or ".xlsx"
    try:
        headers, rows = _read_table(file, suffix)
    except Exception as exc:  # noqa: BLE001
        return CatalogImportResult(
            success=False,
            data=[],
            errors=[f"Ошибка чтения файла: {exc}"],
        )

    if catalog_type == "universities":
        return _parse_universities(headers, rows, mapping)
    return _parse_products(headers, rows, mapping)


def parse_catalog_json(
    content: bytes,
    catalog_type: str,
    mapping: dict[str, str] | None = None,
) -> CatalogImportResult:
    """Разбирает JSON-массив каталога через ту же нормализацию, что и Excel."""
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return CatalogImportResult(False, [], [f"Некорректный JSON: {exc}"])

    records = payload.get("data") if isinstance(payload, dict) else payload
    if Draft7Validator is not None:
        validation = Draft7Validator({
            "oneOf": [
                {"type": "array", "items": {"type": "object"}},
                {
                    "type": "object",
                    "required": ["data"],
                    "properties": {
                        "data": {"type": "array", "items": {"type": "object"}},
                    },
                },
            ],
        })
        errors = sorted(validation.iter_errors(payload), key=lambda error: list(error.path))
        if errors:
            return CatalogImportResult(
                False,
                [],
                [f"Ошибка структуры JSON: {errors[0].message}"],
            )
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        return CatalogImportResult(
            False,
            [],
            ["JSON должен содержать массив объектов или объект с полем data"],
        )
    if not records:
        return CatalogImportResult(False, [], ["JSON-массив пуст"])

    headers = list(records[0].keys())
    rows = [[record.get(header) for header in headers] for record in records]
    if catalog_type == "universities":
        return _parse_universities(headers, rows, mapping)
    if catalog_type == "products":
        return _parse_products(headers, rows, mapping)
    return CatalogImportResult(False, [], [f"Неизвестный тип каталога: {catalog_type}"])


def _read_table(file: BytesIO, suffix: str) -> tuple[list[str], list[list[Any]]]:
    if suffix == ".xls":
        if xlrd is None:
            raise RuntimeError("xlrd не установлен. Установите xlrd==1.2.0")
        workbook = xlrd.open_workbook(file_contents=file.read())
        sheet = workbook.sheet_by_index(0)
        rows = [sheet.row_values(row_index) for row_index in range(sheet.nrows)]
    elif suffix == ".xlsx":
        if load_workbook is None:
            raise RuntimeError("openpyxl не установлен")
        workbook = load_workbook(file, read_only=True, data_only=True)
        sheet = workbook.active
        rows = [list(row) for row in sheet.iter_rows(values_only=True)]
        workbook.close()
    else:
        raise ValueError("Поддерживаются только файлы .xls и .xlsx")

    if not rows or not any(value is not None for value in rows[0]):
        raise ValueError("Файл пуст или отсутствуют заголовки")

    headers = [_normalise_value(value) for value in rows[0]]
    return headers, rows[1:]


def _normalise_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _column_indices(headers: list[str], aliases: dict[str, str]) -> dict[str, int]:
    indices: dict[str, int] = {}
    for index, header in enumerate(headers):
        alias = aliases.get(header.casefold())
        if alias:
            indices[alias] = index
    return indices


def _mapped_indices(
    headers: list[str],
    aliases: dict[str, str],
    mapping: dict[str, str] | None,
) -> dict[str, int]:
    if not mapping:
        return _column_indices(headers, aliases)
    header_indices = {header.casefold(): index for index, header in enumerate(headers)}
    return {
        field: header_indices[source.casefold()]
        for field, source in mapping.items()
        if source.casefold() in header_indices
    }


def _cell(row: list[Any], indices: dict[str, int], field: str) -> Any:
    index = indices.get(field)
    return row[index] if index is not None and index < len(row) else None


def _parse_universities(
    headers: list[str],
    rows: list[list[Any]],
    mapping: dict[str, str] | None = None,
) -> CatalogImportResult:
    aliases = {
        "название": "name",
        "наименование": "name",
        "name": "name",
        "город": "city",
        "city": "city",
        "контактное лицо": "contact_person",
        "contact person": "contact_person",
        "email": "contact_email",
        "contact email": "contact_email",
        "телефон": "contact_phone",
        "contact phone": "contact_phone",
    }
    return _parse_rows(
        headers,
        rows,
        _mapped_indices(headers, aliases, mapping),
        fields=("name", "city", "contact_person", "contact_email", "contact_phone"),
        required="name",
        error_label="Название",
        field_labels={
            "name": "Название",
            "city": "Город",
            "contact_person": "Контактное лицо",
            "contact_email": "Email",
            "contact_phone": "Телефон",
        },
    )


def _parse_products(
    headers: list[str],
    rows: list[list[Any]],
    mapping: dict[str, str] | None = None,
) -> CatalogImportResult:
    aliases = {
        "название": "name",
        "наименование": "name",
        "name": "name",
        "направление": "direction",
        "direction": "direction",
    }
    return _parse_rows(
        headers,
        rows,
        _mapped_indices(headers, aliases, mapping),
        fields=("name", "direction"),
        required="name",
        error_label="Название",
        field_labels={"name": "Название", "direction": "Направление"},
    )


def _validate_optional_fields(
    row_number: int,
    item: dict[str, Any],
    field_labels: dict[str, str],
) -> list[ValidationIssue]:
    """Проверки необязательных полей: формат и нестандартные значения.

    Такие строки импортируются, но попадают в отчёт как предупреждения.
    """
    issues: list[ValidationIssue] = []

    email = item.get("contact_email")
    if email not in (None, "") and not _EMAIL_RE.match(str(email).strip()):
        issues.append(
            ValidationIssue(
                row=row_number,
                field=field_labels.get("contact_email", "Email"),
                problem="Некорректный email",
                severity=SEVERITY_WARNING,
                value=str(email),
            )
        )

    for field_name in ("city", "contact_person", "contact_phone", "direction"):
        value = item.get(field_name)
        if value not in (None, "") and not isinstance(value, (str, int, float)):
            issues.append(
                ValidationIssue(
                    row=row_number,
                    field=field_labels.get(field_name, field_name),
                    problem="Нестандартное значение",
                    severity=SEVERITY_WARNING,
                    value=str(value),
                )
            )

    return issues


def _parse_rows(
    headers: list[str],
    rows: list[list[Any]],
    indices: dict[str, int],
    fields: tuple[str, ...],
    required: str,
    error_label: str,
    field_labels: dict[str, str] | None = None,
) -> CatalogImportResult:
    field_labels = field_labels or {required: error_label}

    if required not in indices:
        issue = ValidationIssue(
            row=None,
            field=error_label,
            problem=f"Не найдена обязательная колонка '{error_label}'",
        )
        return CatalogImportResult(
            success=False,
            data=[],
            headers=headers,
            errors=[issue.problem],
            issues=[issue],
        )

    data: list[dict[str, Any]] = []
    errors: list[str] = []
    issues: list[ValidationIssue] = []
    total_rows = 0
    # Названия, уже встречавшиеся в файле: повтор — предупреждение.
    seen_names: dict[str, int] = {}

    for row_number, row in enumerate(rows, start=2):
        if not any(value not in (None, "") for value in row):
            continue
        total_rows += 1
        item = {field: _cell(row, indices, field) for field in fields}

        if item[required] in (None, ""):
            message = f"Строка {row_number}: отсутствует {error_label.lower()}"
            errors.append(message)
            issues.append(
                ValidationIssue(
                    row=row_number,
                    field=field_labels.get(required, error_label),
                    problem="Пусто",
                )
            )
            continue

        name = str(item[required]).strip()
        if name in seen_names:
            issues.append(
                ValidationIssue(
                    row=row_number,
                    field=field_labels.get(required, error_label),
                    problem=f"Дубль в файле (строка {seen_names[name]})",
                    severity=SEVERITY_WARNING,
                    value=name,
                )
            )
        else:
            seen_names[name] = row_number

        issues.extend(_validate_optional_fields(row_number, item, field_labels))
        data.append(item)

    return CatalogImportResult(
        success=True,
        data=data,
        errors=errors,
        headers=headers,
        issues=issues,
        total_rows=total_rows,
    )
