"""Integrations API router - mock LMS and CMS webhooks."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user, CurrentUser

router = APIRouter()


@router.post("/lms/sync")
async def sync_lms(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mock LMS synchronization endpoint."""
    # In production, implement actual LMS integration
    return {
        "status": "success",
        "message": "LMS sync completed (mock)",
        "synced_count": 0,
    }


@router.post("/laravel/sync")
async def sync_laravel(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mock Laravel CMS synchronization endpoint."""
    # In production, implement actual CMS integration
    return {
        "status": "success",
        "message": "Laravel CMS sync completed (mock)",
        "synced_count": 0,
    }


@router.get("/status")
async def get_integration_status(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get integration status."""
    return {
        "lms": {"connected": False, "last_sync": None},
        "cms": {"connected": False, "last_sync": None},
    }
