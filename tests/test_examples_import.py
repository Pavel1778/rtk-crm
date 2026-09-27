"""Образцы от кейсодержателя в `docs/examples/` должны реально импортироваться.

Эти файлы лежат в репозитории как демонстрация форматов, но раньше их
проверяли только синтетические копии в `tests/test_excel_import.py` — поэтому
расхождение между инструкцией в README и фактическим контрактом импорта
оставалось незамеченным. Здесь образцы открываются с диска и прогоняются
через те же парсеры, что вызывает UI.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest

from backend.api.integration import _records_from_payload
from backend.services.excel_import import parse_catalog_file, parse_catalog_json

EXAMPLES = Path(__file__).resolve().parents[1] / "docs" / "examples"

VENDORS = EXAMPLES / "vendors.xlsx"
USERS = EXAMPLES / "users_b2c.xlsx"
PAYMENTS = EXAMPLES / "payments_b2c.json"


def test_vendors_xlsx_imports_as_products() -> None:
    """«Компания/Продукт/...» из выгрузки вендоров даёт каталог продуктов."""
    result = parse_catalog_file(BytesIO(VENDORS.read_bytes()), "products", VENDORS.name)

    assert result.success is True, result.errors
    assert result.data, "каталог вендоров не должен быть пустым"
    # Контакты вендоров (ФИО, телефон, почта) в каталог продуктов не попадают.
    assert all(set(item) <= {"name", "direction"} for item in result.data)
    assert all(item["name"] for item in result.data)


def test_users_xlsx_imports_without_pii() -> None:
    """Анкета даёт учётные записи, а ПДн-колонки не переносятся."""
    result = parse_catalog_file(BytesIO(USERS.read_bytes()), "users", USERS.name)

    assert result.success is True, result.errors
    assert result.data
    allowed = {"email", "full_name", "last_name", "first_name", "middle_name", "role"}
    for item in result.data:
        assert item["email"]
        # Ни СНИЛС, ни паспорт, ни адрес регистрации в результат не попадают.
        assert set(item) <= allowed


def test_payments_json_imports_as_products() -> None:
    """Ведущий null пропускается, колонка «Курс» становится названием."""
    result = parse_catalog_json(PAYMENTS.read_bytes(), "products")

    assert result.success is True, result.errors
    assert result.data
    assert all(item["name"] for item in result.data)


def test_payments_json_does_not_match_integration_contract() -> None:
    """README не должен отправлять этот файл в раздел «Интеграция».

    Контракт интеграции требует ``external_id`` и ``university``; у заявок
    B2C их нет. Тест фиксирует это расхождение, чтобы инструкция не разошлась
    с кодом снова.
    """
    records, errors, _ = _records_from_payload(
        json.loads(PAYMENTS.read_text(encoding="utf-8"))
    )

    assert not records
    assert errors
    assert all("external_id" in error for error in errors)


@pytest.mark.parametrize("path", [VENDORS, USERS, PAYMENTS])
def test_example_files_are_tracked_and_non_empty(path: Path) -> None:
    assert path.is_file() and path.stat().st_size > 0
