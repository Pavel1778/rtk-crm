from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения. Значения берутся из переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Общие
    app_name: str = "RTK CRM"
    environment: str = "development"
    debug: bool = False
    database_url: str = ""
    secret_key: str = "change-me-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # CORS — строка через запятую в env
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Загрузка справочников и демо-данных при старте
    seed_demo_data: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
