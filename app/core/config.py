# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    DATABASE_URL: str
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Business Bot Management API"
    DEBUG: bool = False

    CORS_ORIGINS: str = "http://localhost:3000"

    MAX_UPLOAD_SIZE: int = 5242880
    UPLOAD_DIR: str = "./uploads"

    SECRET_KEY: str
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_MAX_AGE: int = 86400 * 30  # 30 days
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_DOMAIN: str | None = None

    VERIFICATION_CODE_EXPIRY: int = 600  # 10 minutes in seconds
    VERIFICATION_CODE_MAX_ATTEMPTS: int = 3
    VERIFICATION_CODE_RATE_LIMIT: int = 60  # 1 minute in seconds

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "qren.freelance@gmail.com"
    SMTP_PASSWORD: str = "tevy zzdx vksa vqid"
    SMTP_FROM_NAME: str = "Добро пожаловать!"
    SENDGRID_API_KEY: str = "your-sendgrid-api-key"  # Замените на ваш ключ

    SMSC_LOGIN: str = "Igul"
    SMSC_PASSWORD: str = "HgyHFcvF9"

    BOT_WORKER_URL: str =  "http://bot-worker:8080"
    WEBHOOK_BASE_URL: str = "${WEBHOOK_BASE_URL:-http://localhost}"
    REDIS_URL: str

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()