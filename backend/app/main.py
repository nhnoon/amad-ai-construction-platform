from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .config import settings
from .core.cors import resolve_cors_settings
from .core.docs_routes import register_docs_routes
from .core.password_gate_middleware import PasswordChangeRequiredMiddleware
from .core.rate_limit import RateLimitMiddleware
from .core.request_context import RequestContextMiddleware
from .core.request_protection import RequestProtectionMiddleware
from .core.security_headers import SecurityHeadersMiddleware
from .api.v1.router import router as v1_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    yield
    logger.info("Shutting down")


DOCS_URL = "/api/docs"
REDOC_URL = "/api/redoc"
OPENAPI_URL = "/api/openapi.json"


def _docs_urls(environment: str) -> dict[str, str | None]:
    """RC1 Phase 0 — Security Remediation (Finding 5): interactive API docs
    (Swagger UI, ReDoc) and the raw OpenAPI schema are only served outside
    production. Passing None for docs_url/redoc_url/openapi_url means
    FastAPI never registers those routes at all — a request to any of them
    404s exactly like any other undefined route, rather than merely being
    unlinked from a UI while still reachable directly.

    RC1 Phase 1 Sprint 3 — API Protection & HTTP Security: docs_url and
    redoc_url are now ALWAYS None here, even outside production — FastAPI's
    own built-in docs routes render one inline <script>/<style> tag with no
    way to attach a CSP nonce (see app/core/security_headers.py's module
    docstring). register_docs_routes() below registers nonce-aware
    replacements at the exact same URLs instead, separately, only when
    docs_enabled() is true. openapi_url is unaffected — the raw JSON schema
    response has no HTML/nonce concerns, so it stays on FastAPI's own
    built-in route.

    Factored out as a pure function (same reasoning as
    app/core/cors.py::resolve_cors_settings) so this policy is
    unit-testable without booting the whole ASGI app with a different
    ENVIRONMENT.
    """
    if environment == "production":
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": None, "redoc_url": None, "openapi_url": OPENAPI_URL}


def docs_enabled(environment: str) -> bool:
    return environment != "production"


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Construction Operations Intelligence Platform",
    lifespan=lifespan,
    **_docs_urls(settings.ENVIRONMENT),
)

if docs_enabled(settings.ENVIRONMENT):
    register_docs_routes(app, docs_url=DOCS_URL, redoc_url=REDOC_URL, openapi_url=OPENAPI_URL)

# ── Middleware stack ──────────────────────────────────────────────────
# Starlette applies middleware in reverse registration order (the last
# one added wraps every other one, seeing the request first and the
# response last). Order below, outermost (added last) to innermost
# (added first):
#
#   CORSMiddleware               — must stay outermost: any error response
#                                   from every layer below it still needs
#                                   CORS headers, or the browser can't even
#                                   read the real status/body to know why a
#                                   request failed (see the pre-existing
#                                   comment at its call site below).
#   SecurityHeadersMiddleware    — adds headers to every response,
#                                   including error responses from the
#                                   layers below it.
#   RequestProtectionMiddleware  — pure-ASGI size/timeout guard; runs
#                                   before rate limiting so an oversized/
#                                   slow request is rejected without even
#                                   spending a rate-limit "slot".
#   RateLimitMiddleware          — independent of, and in addition to, the
#                                   existing login IP throttle + DB lockout
#                                   (Phase 2) — see app/core/rate_limit.py.
#   PasswordChangeRequiredMiddleware — unchanged from Phase 2; innermost.
#   RequestContextMiddleware     — wraps PasswordChangeRequiredMiddleware
#                                   and the router, so its contextvar is
#                                   active for both — makes per-request
#                                   IP/User-Agent/request_id available to
#                                   app/core/audit_log.py's writes, however
#                                   deep in the call stack they happen (see
#                                   app/core/request_context.py). Also
#                                   stamps X-Request-ID on every response.
app.add_middleware(PasswordChangeRequiredMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestProtectionMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

_cors = resolve_cors_settings(settings.ALLOWED_ORIGINS, settings.ENVIRONMENT)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors.allowed_origins,
    allow_credentials=_cors.allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/api/healthz", tags=["health"])
def root_health():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}
