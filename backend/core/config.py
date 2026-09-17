from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения. Значения берутся из переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Общие
    app_name: str = "RTK CRM"
    debug: bool = False

    # База данных
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/rtk_crm"
    )

    # Безопасность
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:4173",
    ]

    # Загрузка справочников и демо-данных при старте
    seed_demo_data: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
