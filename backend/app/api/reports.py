from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database import get_db
from app.models.university import University
from app.models.workflow import WorkflowStage
from app.schemas.university import UniversityResponse
from app.services.reports import ReportService
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/universities/pdf")
async def generate_pdf_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Генерация PDF отчета по всем вузам."""
    result = await db.execute(select(University))
    universities = result.scalars().all()
    
    # Преобразование данных для отчета
    uni_data = []
    for uni in universities:
        stage_result = None
        if uni.current_workflow_stage_id:
            stage_result = await db.execute(
                select(WorkflowStage).where(WorkflowStage.id == uni.current_workflow_stage_id)
            )
            stage = stage_result.scalar_one_or_none()
            stage_name = stage.name if stage else "Не указан"
        else:
            stage_name = "Не указан"
        
        uni_data.append({
            "name": uni.name,
            "product": uni.product or "",
            "status": uni.status,
            "manager_name": uni.manager_name or "",
            "workflow_stage": stage_name,
            "license_signed": uni.license_signed,
        })
    
    pdf_bytes = ReportService.generate_pdf_report(uni_data)
    
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=report.pdf"}
    )


@router.get("/universities/xlsx")
async def generate_xlsx_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Генерация XLSX отчета по всем вузам."""
    result = await db.execute(select(University))
    universities = result.scalars().all()
    
    # Преобразование данных для отчета
    uni_data = []
    for uni in universities:
        uni_data.append({
            "name": uni.name,
            "vendor": uni.vendor or "",
            "product": uni.product or "",
            "contract_number": uni.contract_number or "",
            "license_signed": uni.license_signed,
            "license_expiry_year": uni.license_expiry_year,
            "status": uni.status,
            "manager_name": uni.manager_name or "",
            "university_responsible": uni.university_responsible or "",
            "comment": uni.comment or "",
        })
    
    xlsx_bytes = ReportService.generate_xlsx_report(uni_data)
    
    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=report.xlsx"}
    )
