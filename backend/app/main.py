"""
RTK CRM - Main FastAPI Application.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import time

from app.core.config import settings
from app.core.audit_middleware import AuditMiddleware
from app.database import init_db, health_check
from app.api import (
    auth_router,
    interactions_router,
    workflow_router,
    catalogs_router,
    files_router,
    reports_router,
    integrations_router,
)


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="CRM для управления взаимодействием ИТ Школы Ростелекома с ВУЗами",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Audit Middleware (152-ФЗ)
    app.add_middleware(AuditMiddleware)

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        return response

    # Include routers
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(interactions_router, prefix="/api/v1/interactions", tags=["Interactions"])
    app.include_router(workflow_router, prefix="/api/v1/workflow", tags=["Workflow"])
    app.include_router(catalogs_router, prefix="/api/v1/catalogs", tags=["Catalogs"])
    app.include_router(files_router, prefix="/api/v1/files", tags=["Files"])
    app.include_router(reports_router, prefix="/api/v1/reports", tags=["Reports"])
    app.include_router(integrations_router, prefix="/api/v1/integrations", tags=["Integrations"])

    # Health check endpoint
    @app.get("/health")
    async def health_endpoint():
        db_health = await health_check()
        return {"status": "healthy" if db_health else "unhealthy"}

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }

    # Startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting up RTK CRM...")
        await init_db()
        logger.info("Database initialized")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Mock mode: {settings.MOCK_MODE}")
        logger.info(f"Email notifications: {settings.EMAIL_ENABLED}")

    return app


# Create application instance
app = create_application()
