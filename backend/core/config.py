from functools import lru_cache

from pydantic import model_validator
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
    redis_url: str = ""
    secret_key: str = "development-only-change-me-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    # Rate limiting для /api/auth/login: число неуспешных попыток с одного IP
    # за окно (секунды). 0 отключает ограничение.
    login_rate_limit: int = 5
    login_rate_limit_window_seconds: int = 60
    # JWT remains the active auth mode; Keycloak integration is a future
    # closed-contour deployment option.
    mock_mode: bool = True

    # Режим аутентификации: "jwt" — локальные пароли и HS256-токены,
    # "keycloak" — токены выдаёт Keycloak, подпись проверяется по JWKS.
    auth_mode: str = "jwt"
    keycloak_url: str = ""
    keycloak_realm: str = "rtk-crm"
    keycloak_client_id: str = "rtk-crm-frontend"
    # Ожидаемая audience токена. Пустая строка отключает проверку: Keycloak
    # кладёт в aud не client_id, а "account", если в клиенте не включён
    # Audience mapper, поэтому значение задаётся под конкретный realm.
    keycloak_audience: str = ""
    # Кэш публичных ключей realm. Ротация ключей обрабатывается принудительным
    # обновлением, если в токене встретился неизвестный kid.
    keycloak_jwks_ttl_seconds: int = 300
    keycloak_jwks_timeout_seconds: float = 5.0

    # CORS — строка через запятую в env. Явный список: с allow_credentials=True
    # браузер отвергает ответы с `*` в Access-Control-Allow-Origin.
    # 127.0.0.1 и localhost считаются разными origin, поэтому нужны оба.
    cors_origins: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost,"
        "http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1"
    )
    # Дополнительные origin'ы по регулярному выражению (стенды предпросмотра
    # вида https://<branch>.preview.<domain>). Задаётся через env
    # CORS_ORIGIN_REGEX; пустая строка отключает правило.
    cors_origin_regex: str = ""

    # Загрузка справочников и демо-данных при старте
    seed_demo_data: bool = True

    # Уведомления о «зависших» заявках: порог в днях настраивается в админке.
    stuck_timeout_days: int = 14
    # Заглушки каналов уведомлений (Telegram/Email). Пустые значения = выкл.
    telegram_bot_token: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    # Периодическая проверка «зависших» заявок (часы). 0 — выключено.
    notifications_enabled: bool = True
    notifications_interval_hours: int = 12

    # S3-хранилище файлов (Yandex Object Storage или MinIO).
    # Если endpoint пуст — локальный uploads/.
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "rtk-crm"
    s3_secure: bool = False
    # Регион подписи SigV4. Для Yandex Object Storage — ru-central1.
    s3_region: str = "ru-central1"

    @property
    def s3_enabled(self) -> bool:
        return bool(self.s3_endpoint)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        if self.is_production and (
            self.secret_key == "development-only-change-me-32-chars"
            or len(self.secret_key) < 32
        ):
            raise ValueError(
                "SECRET_KEY must be a unique value of at least 32 characters in production"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
