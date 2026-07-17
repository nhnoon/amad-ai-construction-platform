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

    # ── Copilot Memory Layer (bounded, per-user; read/written by the
    # pipeline — see app/ai/memory.py) ─────────────────────────────────
    # Mirrors Hermes's own memory.user_char_limit / memory.memory_char_limit.
    AI_USER_PROFILE_CHAR_LIMIT: int = 1375
    AI_MEMORY_NOTE_CHAR_LIMIT: int = 2200

    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── Document OCR Foundation (app/ai/document_ocr.py) — local disk only,
    # not object storage. Files are stored under a UUID-derived name, never
    # the user-supplied filename, to prevent path traversal.
    OCR_UPLOAD_DIR: str = str(BACKEND_DIR / "data" / "ocr_uploads")
    OCR_MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB
    OCR_MAX_EXTRACTED_TEXT_CHARS: int = 500_000
    OCR_TEXT_PREVIEW_CHARS: int = 2000

    # ── Contract Intelligence Extractor (app/ai/contract_extraction.py) —
    # reads OCR text already stored by Phase 1, never re-runs OCR.
    CONTRACT_EXTRACTION_MAX_INPUT_CHARS: int = 12_000
    CONTRACT_EXTRACTION_MAX_RAW_RESPONSE_CHARS: int = 20_000

    # ── Site Report Intelligence (app/ai/site_report_reasoning.py) — one
    # Hermes reasoning call per /analyze request, over report-scoped,
    # per-domain-capped evidence (see site_report_evidence.py's ranking/
    # compaction). Reduced from 14,000/480s (AMAD AI Stabilization) once
    # the evidence builder started enforcing strict per-domain caps and the
    # output contract shrank from 14 narrative sections to 7 compact
    # fields — both cut the tokens Hermes needs to read AND generate.
    SITE_REPORT_MAX_EVIDENCE_CHARS: int = 6_000
    SITE_REPORT_MAX_RAW_RESPONSE_CHARS: int = 20_000
    # When a report has no prior report to anchor its evidence window to
    # (the project's first report), how many days back to look for safety/
    # NCR/procurement/meeting/document evidence.
    SITE_REPORT_DEFAULT_LOOKBACK_DAYS: int = 14
    # Hard user-facing wait ceiling is 60s total (AMAD AI Stabilization).
    # Evidence gathering + risk scoring is sub-second (pure DB + Python);
    # this leaves Hermes ~45s of budget before response serialization and
    # network overhead, with headroom under the 60s ceiling. A single
    # bounded LOCAL JSON repair (see site_report_reasoning.py) replaces
    # what used to be a full second Hermes call on validation failure, so
    # this is now a true ceiling, not one of two sequential budgets.
    SITE_REPORT_HERMES_TIMEOUT_SECONDS: int = 45
    # How many prior reports' evidence windows to summarize for trend
    # comparison (repeated/escalating/resolved/new issues) — now compacted
    # into ONE trend snapshot line (build_trend_snapshot) rather than one
    # full line per prior report, so this can stay at 3 without bloating
    # the prompt.
    SITE_REPORT_TREND_LOOKBACK_REPORTS: int = 3

    # ── Knowledge Access Layer (AI-003) — multi-domain Copilot questions
    # (e.g. "What decisions from MTG-1 could delay procurement?") combine
    # evidence from 2+ retrieval domains into one prompt. Measured during
    # implementation: an 11-item multi-domain evidence block exceeded the
    # shared 240s HERMES_TIMEOUT_SECONDS on the same qwen2.5:7b/Ollama setup
    # that answers single-domain questions comfortably within it. Same
    # pattern as SITE_REPORT_HERMES_TIMEOUT_SECONDS — a dedicated, longer
    # timeout for multi-domain generation only, so single-domain Copilot
    # questions keep their existing fast timeout unchanged.
    MULTI_DOMAIN_HERMES_TIMEOUT_SECONDS: int = 400


settings = Settings()
