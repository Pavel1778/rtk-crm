"""Reports API router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user, CurrentUser
from app.services.excel_export import generate_xlsx, generate_xls
from app.services.pdf_export import generate_pdf
from app.services.reports import build_dashboard

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard KPI and charts data."""
    return await build_dashboard(db, current_user)


@router.get("/interactions/xlsx")
async def export_xlsx(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export interactions to XLSX."""
    try:
        output = generate_xlsx([], [])  # Pass actual data in production
        return {
            "filename": "interactions.xlsx",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "size": len(output.getvalue()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interactions/xls")
async def export_xls(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export interactions to XLS."""
    try:
        output = generate_xls([], [])  # Pass actual data in production
        return {
            "filename": "interactions.xls",
            "content_type": "application/vnd.ms-excel",
            "size": len(output.getvalue()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interactions/pdf")
async def export_pdf(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export interactions to PDF."""
    try:
        output = generate_pdf([], {})  # Pass actual data in production
        return {
            "filename": "interactions.pdf",
            "content_type": "application/pdf",
            "size": len(output.getvalue()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interactions/json")
async def export_json(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export interactions to JSON."""
    # Implementation similar to other exports
    return {"message": "JSON export endpoint"}
