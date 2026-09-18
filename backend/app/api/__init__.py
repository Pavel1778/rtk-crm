"""Export all API routers."""
from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.interactions import router as interactions_router
from app.api.workflow import router as workflow_router
from app.api.catalogs import router as catalogs_router
from app.api.files import router as files_router
from app.api.reports import router as reports_router
from app.api.integrations import router as integrations_router

__all__ = [
    "auth_router",
    "interactions_router",
    "workflow_router",
    "catalogs_router",
    "files_router",
    "reports_router",
    "integrations_router",
]
