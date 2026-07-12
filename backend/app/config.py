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

    # ── Hermes Agent (local CLI runtime, used when LLM_PROVIDER=hermes) ────
    # Hermes exposes no HTTP chat-completions endpoint for this integration;
    # the supported non-interactive path is its CLI oneshot mode
    # (`hermes -z ...`), invoked as a subprocess. See
    # backend/app/ai/providers/hermes.py for the full rationale.
    # Path to the hermes executable. Auto-detected via PATH when unset.
    HERMES_BIN: Optional[str] = None
    # Isolated Hermes profile (own config.yaml/SOUL.md/toolsets) so the
    # AMAD integration never inherits the user's personal Hermes tools,
    # memory, or skills. Created via `hermes profile create amad --clone`.
    HERMES_PROFILE: str = "amad"
    # Hermes-internal provider name for the local Ollama endpoint, as
    # registered in the amad profile's config.yaml (providers.ollama-launch).
    # Distinct from LLM_PROVIDER=hermes (AMAD's own provider selector).
    HERMES_PROVIDER: str = "ollama-launch"
    # Base URL of the underlying Ollama OpenAI-compatible endpoint that the
    # amad profile's ollama-launch provider points at. Only used for a cheap
    # liveness check (is_available()) — actual generation always goes
    # through the Hermes CLI, never a direct HTTP call from AMAD.
    HERMES_BASE_URL: str = "http://127.0.0.1:11434/v1"
    # Measured locally: ~255s cold (first call after Ollama/Hermes start),
    # ~54s warm, for a trivial one-line grounded answer via the full Hermes
    # Agent framework (session/compression/skill init) on qwen2.5:3b + 8GB
    # RAM. Generous default to tolerate the cold-start case.
    HERMES_TIMEOUT_SECONDS: int = 240
    # No HERMES_API_KEY: the local Ollama endpoint the amad profile talks to
    # requires no authentication (Hermes's own config.yaml uses the Ollama
    # convention of a dummy placeholder key).

    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    ALLOWED_ORIGINS: list[str] = ["*"]


settings = Settings()
