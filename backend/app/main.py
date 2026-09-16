from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.universities import router as universities_router
from app.api.auth import router as auth_router
from app.api.reports import router as reports_router
from app.core.config import settings
import os

app = FastAPI(
    title="RTK CRM API",
    description="CRM для ИТ Школы Ростелекома - Управление взаимодействием с вузами",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS настройки
cors_origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth_router, prefix="/api/v1")
app.include_router(universities_router)
app.include_router(reports_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Корневой эндпоинт."""
    return {"message": "RTK CRM API", "status": "ok", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Проверка здоровья сервиса."""
    return {"status": "healthy"}
