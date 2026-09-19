"""Точка входа FastAPI: инициализация БД, регистрация роутеров, lifespan."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text

from backend.api import auth, catalogs, directories, files, interactions, reports, stages, universities
from backend.core.config import get_settings
from backend.db.session import SessionLocal, create_tables, engine
from backend.middleware.audit import audit_middleware
from backend.schemas.entities import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """При старте: таблицы + демо-данные (если включено)."""
    settings = get_settings()
    try:
        await create_tables()
        logger.info("Схема БД проверена/создана")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Не удалось подключиться к БД: {exc}")

    if settings.seed_demo_data:
        try:
            from backend.seed import seed_demo

            async with SessionLocal() as session:
                created = await seed_demo(session)
            logger.info(f"Демо-данные: {'загружены' if created else 'уже присутствуют'}")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Ошибка загрузки демо-данных: {exc}")

    yield
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="CRM для сопровождения взаимодействия с вузами-партнёрами",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware для аудита (152-ФЗ)
app.middleware("http")(audit_middleware)


@app.exception_handler(RequestValidationError)
async def validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Приводит ошибки валидации к плоскому русскому виду для формы."""
    errors = [
        {
            "field": ".".join(str(part) for part in err["loc"][1:]) or "body",
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Проверьте правильность заполнения полей", "errors": errors},
    )


app.include_router(auth.router)
app.include_router(universities.router)
app.include_router(directories.router)
app.include_router(catalogs.router)
app.include_router(files.router)
app.include_router(stages.router)
app.include_router(interactions.router)
app.include_router(reports.router)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Проверка доступности приложения и базы данных."""
    db_status = "ok"
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_status = "unavailable"
    return HealthResponse(status="ok", app=settings.app_name, database=db_status)


@app.get("/health", include_in_schema=False)
async def health_compat() -> dict[str, str]:
    """Алиас для Render-проверки: /health -> {"status":"ok"}."""
    return {"status": "ok"}
