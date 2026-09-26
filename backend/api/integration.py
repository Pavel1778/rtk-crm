"""API интеграции с LMS и CMS сайта (ФТ-5).

Эндпоинты двусторонней интеграции:

* ``GET  /api/integration/schema`` — утверждённые поля пакета (контракт).
* ``POST /api/integration/preview`` — разбор входящего JSON без записи (dry-run).
* ``POST /api/integration/import`` — импорт входящего пакета в workflow.
* ``GET  /api/integration/pull/{source}`` — забор пакета из LMS/CMS (заглушка).
* ``GET  /api/integration/outbound`` — исходящий пакет для внешних систем.

Внешние системы на момент разработки недоступны (контракт не предоставлен),
поэтому ``pull`` читает заглушку. Разбор и запись — реальные: переход на
живой эндпоинт сводится к замене источника данных.
"""

from __future__ import annotations

from typing import Any

from app.api.interactions import _default_stage, _ensure_parallel_limit
from app.auth.security import get_current_user, require_manager_or_admin
from app.db.session import get_db
from app.models.entities import (
    Interaction,
    ITDirection,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from app.models.enums import WorkflowScope
from app.services.integration import (
    KNOWN_FIELDS,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    ParsedRecord,
    fetch_stub,
    parse_payload,
)
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/integration", tags=["integration"])


class ImportSummary(BaseModel):
    """Итог импорта: что создано, что обновлено, что отброшено."""

    source: str
    total: int
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_ids: list[int] = Field(default_factory=list)


@router.get("/schema")
async def integration_schema(
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Утверждённые поля пакета обмена (контракт для LMS и CMS)."""
    return {
        "required": list(REQUIRED_FIELDS),
        "optional": list(OPTIONAL_FIELDS),
        "known": sorted(KNOWN_FIELDS),
        "scope_values": [scope.value for scope in WorkflowScope],
        "notes": (
            "Источник может передать подмножество полей. Неизвестные поля "
            "игнорируются и возвращаются в warnings. null внутри массива "
            "пропускается без ошибки."
        ),
    }


async def _resolve_university(db: AsyncSession, name: str) -> University | None:
    return await db.scalar(select(University).where(University.name == name))


async def _resolve_product(db: AsyncSession, name: str | None) -> ITProduct | None:
    if not name:
        return None
    return await db.scalar(select(ITProduct).where(ITProduct.name == name))


async def _resolve_direction(db: AsyncSession, name: str | None) -> ITDirection | None:
    if not name:
        return None
    return await db.scalar(select(ITDirection).where(ITDirection.name == name))


async def _resolve_stage(
    db: AsyncSession, code: str | None, scope: WorkflowScope
) -> WorkflowStageRef:
    """Находит этап по коду либо берёт первый этап нужной воронки."""
    if code:
        stage = await db.scalar(
            select(WorkflowStageRef).where(
                WorkflowStageRef.code == code,
                WorkflowStageRef.scope == scope,
            )
        )
        if stage is not None:
            return stage
    return await _default_stage(db, scope)


async def _resolve_kam(db: AsyncSession, email: str | None) -> User | None:
    if not email:
        return None
    return await db.scalar(select(User).where(User.email == email))


def _records_from_payload(payload: Any) -> tuple[list[ParsedRecord], list[str], list[str]]:
    parsed = parse_payload(payload)
    return parsed.records, parsed.errors, parsed.warnings


@router.post("/preview", response_model=ImportSummary)
async def preview_integration(
    payload: Any = Body(...),
    source: str = Query(default="lms"),
    _: User = Depends(require_manager_or_admin),
) -> ImportSummary:
    """Dry-run: разбирает пакет и показывает план без записи в БД.

    Принимает как массив записей, так и объект с ключом ``items`` — источники
    отдают оба варианта.
    """
    records, errors, warnings = _records_from_payload(payload)
    return ImportSummary(
        source=source,
        total=len(records) + len(errors),
        skipped=len(errors),
        errors=errors,
        warnings=warnings,
    )


async def _apply_records(
    db: AsyncSession,
    records: list[ParsedRecord],
    summary: ImportSummary,
) -> None:
    """Создаёт и дополняет карточки по разобранным записям."""
    for record in records:
        scope = (
            WorkflowScope.B2C if record.scope == "b2c" else WorkflowScope.B2B
        )
        university = await _resolve_university(db, record.university)
        if university is None:
            summary.skipped += 1
            summary.errors.append(
                f"{record.external_id}: вуз «{record.university}» не найден в справочнике"
            )
            continue

        product = await _resolve_product(db, record.product)
        direction = await _resolve_direction(db, record.direction)
        if product is not None and direction is not None and product.direction_id is None:
            product.direction_id = direction.id

        stage = await _resolve_stage(db, record.stage_code, scope)
        kam = await _resolve_kam(db, record.assigned_kam_email)

        # Сопоставление по номеру договора: повторный импорт обновляет
        # существующую карточку вместо создания дубля.
        existing = None
        if record.contract_number:
            existing = await db.scalar(
                select(Interaction).where(
                    Interaction.contract_number == record.contract_number,
                    Interaction.scope == scope,
                )
            )

        if existing is not None:
            existing.product_id = product.id if product else existing.product_id
            existing.university_specialist = (
                record.university_specialist or existing.university_specialist
            )
            existing.notes = record.notes or existing.notes
            summary.updated += 1
            continue

        try:
            await _ensure_parallel_limit(db, university.id)
        except HTTPException as exc:
            summary.skipped += 1
            summary.errors.append(f"{record.external_id}: {exc.detail}")
            continue

        interaction = Interaction(
            university_id=university.id,
            product_id=product.id if product else None,
            stage_id=stage.id,
            assigned_kam_id=kam.id if kam else None,
            scope=scope,
            contract_number=record.contract_number or record.external_id,
            contract_date=record.contract_date,
            university_specialist=record.university_specialist,
            notes=record.notes,
        )
        db.add(interaction)
        await db.flush()
        summary.created += 1
        summary.created_ids.append(interaction.id)


async def _run_import(
    db: AsyncSession,
    payload: Any,
    source: str,
) -> ImportSummary:
    records, errors, warnings = _records_from_payload(payload)
    summary = ImportSummary(
        source=source, total=len(records) + len(errors), errors=errors, warnings=warnings
    )
    await _apply_records(db, records, summary)
    await db.commit()
    if summary.created:
        from app.services.report_cache import invalidate_report_cache

        await invalidate_report_cache()
    return summary


@router.post("/import", response_model=ImportSummary)
async def import_integration(
    payload: Any = Body(...),
    source: str = Query(default="lms"),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_manager_or_admin),
) -> ImportSummary:
    """Импортирует пакет в workflow: новые карточки создаются, существующие
    дополняются. Ключ сопоставления — ``external_id`` в номере договора.
    """
    return await _run_import(db, payload, source)


@router.get("/pull/{source}", response_model=ImportSummary)
async def pull_from_source(
    source: str,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_manager_or_admin),
) -> ImportSummary:
    """Забирает пакет из внешней системы и импортирует его.

    Источник — заглушка LMS или CMS: контракт от заказчика ещё не получен.
    """
    if source not in {"lms", "cms"}:
        raise HTTPException(status_code=404, detail="Неизвестный источник")
    payload = fetch_stub(source)  # type: ignore[arg-type]
    return await _run_import(db, payload, source)


@router.get("/outbound")
async def outbound_package(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager_or_admin),
) -> dict[str, Any]:
    """Исходящий пакет для LMS/CMS: данные карточек и ключи связи.

    Формируется из той же выборки, что отчёт `GET /api/reports/json`, поэтому
    принимающая сторона видит те же поля и идентификаторы.
    """
    from app.api.reports import _build_interaction_data, _files_by_interaction

    data = await _build_interaction_data(
        db, None, None, None, None, None, None, None, None
    )
    files = await _files_by_interaction(db, [item["id"] for item in data])
    for item in data:
        item["files"] = files.get(item["id"], [])

    return {
        "direction": "crm->external",
        "targets": ["lms", "cms"],
        "total": len(data),
        "items": data,
    }
