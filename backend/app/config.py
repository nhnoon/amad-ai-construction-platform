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
    # RC1 Phase 0 — Security Remediation (Finding 8): defaults to False (was
    # True). DEBUG is not read anywhere in the running application today —
    # FastAPI's own debug= flag is never wired to it — so this value is
    # currently inert either way. It is hardened regardless: see
    # resolve_debug_setting() below and its call site at the bottom of this
    # file, which refuses to start with DEBUG=true outside development, so
    # a future change that *does* wire this in can never silently leak
    # tracebacks in production.
    DEBUG: bool = False

    API_V1_PREFIX: str = "/api/v1"

    # RC1 Phase 0 — Security Remediation (Finding 7): must be set via the
    # DATABASE_URL environment variable — no hardcoded fallback. This used
    # to default to "postgresql://user:password@localhost:5432/construction",
    # which meant a deployment that forgot to set DATABASE_URL would
    # silently attempt to connect to a generic local placeholder instead of
    # failing fast with a clear error. Mirrors the existing SESSION_SECRET
    # pattern immediately below.
    DATABASE_URL: str

    REDIS_URL: str = "redis://localhost:6379/0"

    # Must be set via SESSION_SECRET environment variable — no hardcoded fallback.
    SESSION_SECRET: str
    ALGORITHM: str = "HS256"

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_must_not_be_empty(cls, v: str) -> str:
        if not v or v.strip() == "":
            # Deliberately does not echo `v` back — even an empty/whitespace
            # value is rejected without ever including database connection
            # details (host/user/password) in an error message or log line.
            raise ValueError(
                "DATABASE_URL environment variable must be set to a non-empty value. "
                "See backend/.env.example for the expected format."
            )
        return v

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

    # RC1 Phase 1 Sprint 2 — Frontend Session Integration: reduced from 480
    # (8 hours) now that the frontend transparently refreshes access tokens
    # on a 401 (silent refresh — see custom-fetch.ts's setRefreshHandler
    # wiring in artifacts/web/src/lib/auth.ts, verified end to end before
    # this default changed). A stolen/leaked access token is now usable
    # for at most 30 minutes regardless of the refresh token's own state,
    # instead of up to 8 hours. Still fully overridable via the
    # ACCESS_TOKEN_EXPIRE_MINUTES environment variable.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Login brute-force protection (Phase 2 — Security & Authentication
    # Hardening) ────────────────────────────────────────────────────────
    # Per-IP sliding-window throttle on POST /auth/login, checked before
    # any credential/lockout logic (see app/core/login_security.py).
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60
    # Per-account lockout (DB-persisted on UserAccount — survives restarts,
    # unlike the IP throttle above) after this many consecutive failed
    # attempts, for this many minutes, then auto-unlocks (see
    # app/api/v1/auth.py::login).
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # ── Refresh Token & Session Security (RC1 Phase 1 Sprint 1) ─────────
    # Refresh tokens are opaque, server-side, rotated-on-use identifiers
    # (see app/core/session_security.py) — deliberately NOT JWTs like the
    # stateless access token above, because they must be individually
    # revocable (logout / logout-all) and enumerable (GET /auth/sessions).
    # Sliding expiry: every successful rotation resets a token's
    # expires_at to now + one of the two windows below, so an
    # actively-used session never expires mid-use while an abandoned one
    # still expires on schedule.
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # "Remember me" (opt-in per login via UserLogin.remember_me) — a
    # longer sliding window for a user who explicitly asked to stay
    # signed in on a trusted device. Never the default.
    REFRESH_TOKEN_REMEMBER_ME_EXPIRE_DAYS: int = 30

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

    # Phase 2 — Security & Authentication Hardening: the previous default
    # ("*") combined with the CORSMiddleware's allow_credentials=True in
    # app/main.py is the exact "wildcard origin + credentials" anti-pattern
    # (Starlette reflects the request's Origin header back when "*" is
    # paired with credentials, which is equivalent in practice to trusting
    # every origin). Real deployments must set ALLOWED_ORIGINS explicitly
    # via env var; this default only covers the local Vite dev server.
    # See app/main.py for the startup guard that enforces this in
    # non-development environments.
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

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

    # ── Document Storage System (Sprint 1 — app/ai/document_storage.py,
    # app/storage/) — persistent, versioned, checksummed file storage for
    # Document rows. Deliberately separate from OCR_UPLOAD_DIR above: that
    # directory is OCR's own ephemeral single-file-per-document working
    # copy (app/ai/document_ocr.py), unaffected by this. "local" is the
    # only implemented provider; "s3"/"azure_blob" are interface-complete
    # stubs (app/storage/providers_stub.py) pending an SDK dependency this
    # project doesn't currently install plus real credentials — selecting
    # either fails fast and loud at get_storage_service() time rather than
    # silently falling back to local disk.
    DOCUMENT_STORAGE_PROVIDER: str = "local"
    DOCUMENT_STORAGE_DIR: str = str(BACKEND_DIR / "data" / "document_storage")
    DOCUMENT_MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    # Unused by LocalStorageService — read only by the future S3/Azure
    # providers once implemented.
    DOCUMENT_STORAGE_S3_BUCKET: Optional[str] = None
    DOCUMENT_STORAGE_S3_REGION: Optional[str] = None
    DOCUMENT_STORAGE_AZURE_CONTAINER: Optional[str] = None
    DOCUMENT_STORAGE_AZURE_CONNECTION_STRING: Optional[str] = None

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

    # ── Security Headers (RC1 Phase 1 Sprint 3 — API Protection & HTTP
    # Security) ───────────────────────────────────────────────────────
    # Master switch. Each header below also has its own switch, so a
    # deployment behind a reverse proxy/CDN that already emits SOME of
    # these (common for HSTS/COOP at the edge) can disable just those
    # without losing the rest — see app/core/security_headers.py.
    SECURITY_HEADERS_ENABLED: bool = True

    HSTS_ENABLED: bool = True
    HSTS_MAX_AGE_SECONDS: int = 31_536_000  # 1 year — standard preload-eligible duration
    HSTS_INCLUDE_SUBDOMAINS: bool = True
    # Submitting to the browser HSTS preload list is a one-way, hard-to-
    # reverse operational decision (removal takes months) — never inferred
    # from other settings, always an explicit opt-in.
    HSTS_PRELOAD: bool = False

    X_FRAME_OPTIONS_ENABLED: bool = True
    X_FRAME_OPTIONS: str = "DENY"

    X_CONTENT_TYPE_OPTIONS_ENABLED: bool = True

    REFERRER_POLICY_ENABLED: bool = True
    REFERRER_POLICY: str = "strict-origin-when-cross-origin"

    PERMISSIONS_POLICY_ENABLED: bool = True
    # This API serves no browser feature that needs any of these — every
    # directive denied to every origin (an explicit empty allowlist, not
    # just the browser default).
    PERMISSIONS_POLICY: str = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"

    CROSS_ORIGIN_OPENER_POLICY_ENABLED: bool = True
    CROSS_ORIGIN_OPENER_POLICY: str = "same-origin"

    CROSS_ORIGIN_RESOURCE_POLICY_ENABLED: bool = True
    CROSS_ORIGIN_RESOURCE_POLICY: str = "same-origin"

    # Cross-Origin-Embedder-Policy — the one header Sprint 3 says to add
    # "only if compatible". COEP:require-corp blocks loading ANY
    # cross-origin resource that doesn't itself opt in via CORP/CORS,
    # which would break the dev-only Swagger/ReDoc UIs' CDN-hosted JS/CSS/
    # fonts (see CSP_* below). Off by default for exactly that reason; an
    # operator running this API with no cross-origin dependents at all
    # (e.g. production, where /docs and /redoc are disabled entirely) can
    # opt in.
    CROSS_ORIGIN_EMBEDDER_POLICY_ENABLED: bool = False
    CROSS_ORIGIN_EMBEDDER_POLICY: str = "require-corp"

    # ── Content Security Policy ──────────────────────────────────────
    # See app/core/security_headers.py::build_csp for the actual policy
    # construction (different in development vs production — Part B).
    CSP_ENABLED: bool = True
    # Report-only mode: sends Content-Security-Policy-Report-Only instead
    # of the enforcing header, so a policy change can be observed via
    # browser devtools/violation reports before it can block anything.
    CSP_REPORT_ONLY: bool = False
    # Origins the stock (un-self-hosted) FastAPI Swagger/ReDoc HTML loads
    # from — dev-only allowances, never present in the production policy
    # (docs are disabled entirely in production; see app/main.py).
    CSP_SWAGGER_CDN_ORIGIN: str = "https://cdn.jsdelivr.net"
    CSP_SWAGGER_FAVICON_ORIGIN: str = "https://fastapi.tiangolo.com"
    CSP_REDOC_FONTS_CSS_ORIGIN: str = "https://fonts.googleapis.com"
    CSP_REDOC_FONTS_ORIGIN: str = "https://fonts.gstatic.com"

    # ── Global API Rate Limiting (Part C) ────────────────────────────
    # In-memory sliding-window counters — same trade-off/precedent as the
    # existing per-IP login throttle (app/core/login_security.py) and the
    # AI Copilot rate limiter (app/ai/ratelimit.py): resets on restart,
    # acceptable for a request-rate cap (unlike DB-persisted account
    # lockout, this doesn't need to survive restarts). See
    # app/core/rate_limit.py's RateLimitStore abstraction — a future
    # RedisRateLimitStore can satisfy the same interface without any
    # caller changing. Independent of, and in addition to, the existing
    # Sprint 1/2 login IP throttle + per-account DB lockout — this sprint
    # must not modify that behavior (see login_security.py), so the
    # "login" scope below is a second, separate layer using its own
    # counters/keys.
    RATE_LIMIT_ENABLED: bool = True

    RATE_LIMIT_ANONYMOUS_MAX_REQUESTS: int = 60
    RATE_LIMIT_ANONYMOUS_WINDOW_SECONDS: int = 60

    RATE_LIMIT_AUTHENTICATED_MAX_REQUESTS: int = 300
    RATE_LIMIT_AUTHENTICATED_WINDOW_SECONDS: int = 60

    RATE_LIMIT_LOGIN_MAX_REQUESTS: int = 10
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 60

    RATE_LIMIT_REFRESH_MAX_REQUESTS: int = 30
    RATE_LIMIT_REFRESH_WINDOW_SECONDS: int = 60

    RATE_LIMIT_UPLOAD_MAX_REQUESTS: int = 20
    RATE_LIMIT_UPLOAD_WINDOW_SECONDS: int = 60

    # ── Request Protection (Part D/E) ────────────────────────────────
    # See app/core/request_protection.py — a pure-ASGI middleware
    # (deliberately not BaseHTTPMiddleware, which fully buffers the body
    # before application code ever sees it, defeating the point of a
    # size cap meant to bound memory use for an oversized request).
    REQUEST_PROTECTION_ENABLED: bool = True
    # Cap for ordinary (non-multipart) bodies — JSON payloads, form
    # posts, etc. Generous relative to every real payload this API
    # accepts today while still bounding worst-case abuse.
    REQUEST_MAX_BODY_SIZE_BYTES: int = 2 * 1024 * 1024  # 2 MB
    # Cap for multipart/form-data (upload) requests specifically —
    # deliberately ABOVE the largest existing application-layer cap
    # (DOCUMENT_MAX_FILE_SIZE_BYTES = 50 MB) so this can never reject an
    # upload the application would otherwise accept; it exists purely as
    # an outer safety net against a request the application-layer check
    # would never even get to see (e.g. a deliberately unbounded
    # multipart stream the app-layer .read() would otherwise buffer in
    # full before checking its length).
    REQUEST_MAX_UPLOAD_SIZE_BYTES: int = 60 * 1024 * 1024  # 60 MB
    # Ceiling on how long it may take to fully RECEIVE the request body
    # (slow-loris protection) — deliberately NOT a ceiling on how long the
    # application then takes to process an already-fully-received request
    # (see app/core/request_protection.py's module docstring for why: the
    # AI Copilot's LLM-backed responses legitimately take 60-150s+ and
    # already have their own considered timeout budgets elsewhere —
    # HERMES_TIMEOUT_SECONDS and friends — a generic HTTP-layer request
    # size/slowness guard has no business overriding those). Uploads get
    # a longer allowance (a legitimate slow connection uploading tens of
    # MB takes real time to arrive); an ordinary request's body should
    # never legitimately take anywhere near this long to arrive.
    REQUEST_TIMEOUT_SECONDS: int = 30
    REQUEST_UPLOAD_TIMEOUT_SECONDS: int = 120


def resolve_debug_setting(debug: bool, environment: str) -> bool:
    """Validate the DEBUG flag against the running environment.

    RC1 Phase 0 — Security Remediation (Finding 8): DEBUG is not currently
    read anywhere in the running application — FastAPI's own `debug=` flag
    is never wired to it — so today's behavior is safe regardless of this
    value. It is hardened anyway: the day someone wires
    `FastAPI(debug=settings.DEBUG)` as an apparently-harmless fix for "why
    doesn't DEBUG do anything", a forgotten `DEBUG=true` left over from
    local development would leak full tracebacks (file paths, source
    lines, possibly database connection details via SQLAlchemy exceptions)
    to every API client in that environment.

    Mirrors the identical ALLOWED_ORIGINS-wildcard guard in
    app/core/cors.py::resolve_cors_settings — same "refuse to boot outside
    development" policy, factored out as a pure function for the same
    reason: unit-testable without booting Settings/the ASGI app.
    """
    if debug and environment != "development":
        raise RuntimeError(
            "DEBUG=true is not allowed outside ENVIRONMENT=development — "
            "set DEBUG=false (or unset it) for this environment."
        )
    return debug


settings = Settings()
resolve_debug_setting(settings.DEBUG, settings.ENVIRONMENT)
