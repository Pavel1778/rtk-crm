"""Точка входа FastAPI: инициализация БД, регистрация роутеров, lifespan."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text

from app.api import (
    auth,
    catalogs,
    directories,
    files,
    interactions,
    notifications,
    reports,
    stages,
    universities,
)
from app.core.config import get_settings
from app.db.session import SessionLocal, create_tables, engine
from app.middleware.audit import audit_middleware
from app.middleware.rate_limit import login_rate_limit_middleware
from app.schemas.entities import HealthResponse
from app.services.report_cache import close_report_cache
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """При старте: таблицы + демо-данные (если включено)."""
    settings = get_settings()
    try:
        # Удаляем старый тип enum userrole, если он существует
        async with engine.begin() as conn:
            try:
                await conn.execute(text("DROP TYPE IF EXISTS userrole CASCADE"))
                logger.info("Удалён старый тип enum userrole")
            except Exception:  # noqa: BLE001
                pass  # Тип может не существовать
        await create_tables()
        logger.info("Схема БД проверена/создана")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Не удалось подключиться к БД: {exc}")

    if settings.seed_demo_data:
        try:
            from app.seed import seed_demo

            async with SessionLocal() as session:
                created = await seed_demo(session)
            logger.info(f"Демо-данные: {'загружены' if created else 'уже присутствуют'}")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Ошибка загрузки демо-данных: {exc}")

    start_scheduler()

    yield
    stop_scheduler()
    await close_report_cache()
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="CRM для сопровождения взаимодействия с вузами-партнёрами",
    version="1.0.0",
    lifespan=lifespan,
)

# Аудит добавляется первым, чтобы CORS оставался внешним middleware и
# добавлял заголовки также к ответам с ошибками и потоковым файлам.
app.middleware("http")(audit_middleware)
# Rate limiting логина — дешёвый in-process счётчик перед обработчиком.
app.middleware("http")(login_rate_limit_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
    max_age=3600,
)

# Метрики Prometheus (RPS, latency, error rate) на /metrics. Инструментатор
# не является обязательной зависимостью: без пакета маршрут не появляется.
try:  # pragma: no cover - зависит от установленного пакета
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(
        app, include_in_schema=True, should_gzip=True
    )
except ImportError:  # pragma: no cover
    pass


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
app.include_router(notifications.router)


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


@app.get("/healthz", tags=["system"])
async def healthz() -> dict[str, str]:
    """Liveness-проба: процесс жив и отвечает (без проверки зависимостей)."""
    return {"status": "ok"}


@app.get("/readyz", tags=["system"])
async def readyz() -> JSONResponse:
    """Readiness-проба: доступность БД, Redis/KeyDB и MinIO/S3-хранилища.

    Используется в healthcheck балансировщика и docker-compose. Возвращает
    503, если хотя бы одна критичная зависимость недоступна.
    """
    checks: dict[str, str] = {}

    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001
        checks["database"] = "unavailable"

    checks["cache"] = await _check_cache()
    checks["storage"] = await _check_storage()

    ready = all(value != "unavailable" for value in checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ok" if ready else "degraded", "checks": checks},
    )


async def _check_cache() -> str:
    """Redis/KeyDB необязателен: без REDIS_URL считаем режим fallback."""
    settings_ = get_settings()
    if not settings_.redis_url:
        return "disabled"
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings_.redis_url)
        await client.ping()
        await client.aclose()
        return "ok"
    except Exception:  # noqa: BLE001
        return "unavailable"


async def _check_storage() -> str:
    """MinIO/S3 необязателен: в dev используется локальный uploads/."""
    settings_ = get_settings()
    if not settings_.s3_enabled:
        return "local"
    try:
        from app.services.file_storage import get_storage

        storage = get_storage()
        await storage.ping()
        return "ok"
    except Exception:  # noqa: BLE001
        return "unavailable"


@app.get("/api/debug/cors", tags=["system"])
async def debug_cors() -> dict[str, object]:
    """Диагностика CORS: дошла ли CORS_ORIGINS из окружения до контейнера."""
    return {
        "cors_origins_setting": settings.cors_origins,
        "cors_origins_list": settings.cors_origins_list,
    }
