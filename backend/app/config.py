from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional


BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Construction AI Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql://user:password@localhost:5432/construction"

    REDIS_URL: str = "redis://localhost:6379/0"

    # Must be set via SESSION_SECRET environment variable — no hardcoded fallback.
    SESSION_SECRET: str
    ALGORITHM: str = "HS256"

    @field_validator("SESSION_SECRET")
    @classmethod
    def secret_must_not_be_empty(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError(
                "SESSION_SECRET environment variable must be set to a non-empty value. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    @property
    def SECRET_KEY(self) -> str:
        return self.SESSION_SECRET

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = "mock-model"
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_MAX_TOKENS: int = 2000
    LLM_TEMPERATURE: float = 0.0

    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    ALLOWED_ORIGINS: list[str] = ["*"]


settings = Settings()
