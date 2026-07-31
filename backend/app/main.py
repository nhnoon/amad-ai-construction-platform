from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .config import settings
from .core.cors import resolve_cors_settings
from .core.password_gate_middleware import PasswordChangeRequiredMiddleware
from .api.v1.router import router as v1_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Construction Operations Intelligence Platform",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Phase 2 — Security & Authentication Hardening: enforces "must change
# password before doing anything else" application-wide (see
# app/core/password_gate_middleware.py). Starlette applies middleware in
# reverse registration order (the last one added wraps every other one),
# so this must be added BEFORE CORSMiddleware — otherwise a short-circuited
# 403 from this gate would skip CORSMiddleware entirely and arrive at the
# browser with no CORS headers, and the frontend would never be able to
# read the response body to know it should redirect to Change Password.
app.add_middleware(PasswordChangeRequiredMiddleware)

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
