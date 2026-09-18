from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "RTK CRM"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    DATABASE_URL: str
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    SECRET_KEY: str = "secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    MOCK_MODE: bool = True
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "rtk-crm"
    KEYCLOAK_CLIENT_ID: str = "rtk-crm-web"
    
    REDIS_URL: str = "redis://localhost:6379/0"
    
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "rtk-crm-files"
    S3_USE_SSL: bool = False
    
    EMAIL_ENABLED: bool = False
    EMAIL_HOST: str = "smtp.yandex.ru"
    EMAIL_PORT: int = 465
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    EMAIL_FROM_NAME: str = "RTK CRM"
    
    MAX_FILE_SIZE_MB: int = 50

settings = Settings()
