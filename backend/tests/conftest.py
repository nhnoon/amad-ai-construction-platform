from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text as sa_text
from sqlalchemy.orm import sessionmaker

from datetime import datetime, timezone

from app.main import app
from app.database import get_db
from app.core.deps import get_current_user
from app.models.auth import UserAccount
from app.config import settings

engine_test = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def _resolve_test_user_id() -> int:
    """Return the real DB id of the seeded admin user for FK-safe test mocking."""
    db = TestingSessionLocal()
    try:
        row = db.execute(
            sa_text("SELECT id FROM user_accounts WHERE email = 'admin@construction.ai' LIMIT 1")
        ).fetchone()
        return int(row[0]) if row else 1
    finally:
        db.close()


def _resolve_test_user_organization_id() -> "int | None":
    """Return the real admin user's actual organization_id.

    Phase 1 production-hardening: override_get_current_user() below builds
    a UserAccount object directly rather than loading it from the DB, so it
    never picked up organization_id (always implicitly None) — harmless
    before organization scoping existed, but since build_ai_scope() now
    determines a global-read user's accessible_project_ids from their
    organization_id, leaving this None would make the mocked test admin see
    zero projects, breaking every existing test that assumes full access.
    Resolved once at import time, same pattern as _resolve_test_user_id().
    """
    db = TestingSessionLocal()
    try:
        row = db.execute(
            sa_text("SELECT organization_id FROM user_accounts WHERE email = 'admin@construction.ai' LIMIT 1")
        ).fetchone()
        return int(row[0]) if row and row[0] is not None else None
    finally:
        db.close()


TEST_USER_ID: int = _resolve_test_user_id()
TEST_USER_ORGANIZATION_ID: "int | None" = _resolve_test_user_organization_id()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user() -> UserAccount:
    return UserAccount(
        id=TEST_USER_ID,
        email="admin@construction.ai",
        full_name="Test Admin",
        role="admin",
        is_active=True,
        hashed_password="x",
        organization_id=TEST_USER_ORGANIZATION_ID,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@contextmanager
def real_auth_client():
    """A TestClient that resolves identity from a real Bearer token
    (register/login as an actual user) instead of the shared mocked admin
    override — for tests that need to verify a genuinely different user's
    real behavior (e.g. RBAC/tenant-isolation checks, Phase 2's
    must-change-password gate).

    app.dependency_overrides is one global dict shared by every TestClient
    instance, including the session-scoped `client` fixture — so this
    must NOT be used at the same time as `client` within one test (fixture
    setup for both would run before the test body, and popping the
    override here would silently break `client` too). Finish any
    admin-mocked (`client` fixture) setup first, then use this,
    ``with real_auth_client() as raw: ...`` — the override is restored
    automatically on exit regardless of what ran inside.
    """
    saved = app.dependency_overrides.pop(get_current_user, None)
    try:
        with TestClient(app) as c:
            yield c
    finally:
        if saved is not None:
            app.dependency_overrides[get_current_user] = saved


@pytest.fixture(autouse=True)
def reset_rate_limiter_global():
    """Reset the AI rate limiter before every test so rate-limit state from
    one test does not bleed into the next.  Applies to all test files."""
    from app.ai.ratelimit import get_ai_rate_limiter
    get_ai_rate_limiter().reset(TEST_USER_ID)
    yield


@pytest.fixture(autouse=True)
def reset_login_rate_limiter_global():
    """Phase 2 — Security & Authentication Hardening: reset the per-IP
    login rate limiter before every test. Starlette's TestClient always
    reports the same synthetic client host, so without this every test
    file's real /auth/login calls would share one sliding window and could
    trip each other's 429s purely from aggregate test-suite volume, not
    real brute-forcing."""
    from app.core.login_security import login_ip_rate_limiter
    login_ip_rate_limiter.reset_all()
    yield


@pytest.fixture(autouse=True)
def reset_global_rate_limiter():
    """RC1 Phase 1 Sprint 3 — API Protection & HTTP Security: reset the
    global (anonymous/authenticated/login/refresh/upload scoped) rate
    limiter before every test — same reasoning as
    reset_login_rate_limiter_global above, and entirely independent of
    it (see app/core/rate_limit.py's module docstring)."""
    from app.core.rate_limit import get_default_rate_limit_store
    get_default_rate_limit_store().reset_all()
    yield


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Watermark-based cleanup: record max IDs before tests, delete higher IDs after.

    Covers B2B tables (organizations, user_accounts, project_memberships) and
    AI Copilot tables (ai_conversations, ai_messages, ai_citations,
    copilot_audit_logs).  Seeded demo data (lower IDs) is never touched.
    """
    db = TestingSessionLocal()
    max_org_id = db.execute(sa_text("SELECT COALESCE(MAX(id), 0) FROM organizations")).scalar()
    max_user_id = db.execute(sa_text("SELECT COALESCE(MAX(id), 0) FROM user_accounts")).scalar()
    max_mem_id = db.execute(sa_text("SELECT COALESCE(MAX(id), 0) FROM project_memberships")).scalar()
    max_conv_id = db.execute(sa_text("SELECT COALESCE(MAX(id), 0) FROM ai_conversations")).scalar()
    max_msg_id = db.execute(sa_text("SELECT COALESCE(MAX(id), 0) FROM ai_messages")).scalar()
    max_cit_id = db.execute(sa_text("SELECT COALESCE(MAX(id), 0) FROM ai_citations")).scalar()
    max_audit_id = db.execute(sa_text("SELECT COALESCE(MAX(id), 0) FROM copilot_audit_logs")).scalar()
    max_refresh_token_id = db.execute(sa_text("SELECT COALESCE(MAX(id), 0) FROM refresh_tokens")).scalar()
    db.close()

    yield

    db = TestingSessionLocal()
    db.execute(sa_text(f"DELETE FROM refresh_tokens WHERE id > {max_refresh_token_id}"))
    db.execute(sa_text(f"DELETE FROM ai_citations WHERE id > {max_cit_id}"))
    db.execute(sa_text(f"DELETE FROM ai_messages WHERE id > {max_msg_id}"))
    db.execute(sa_text(f"DELETE FROM ai_conversations WHERE id > {max_conv_id}"))
    db.execute(sa_text(f"DELETE FROM copilot_audit_logs WHERE id > {max_audit_id}"))
    db.execute(sa_text(f"DELETE FROM project_memberships WHERE id > {max_mem_id}"))
    db.execute(sa_text(f"DELETE FROM user_accounts WHERE id > {max_user_id}"))
    db.execute(sa_text(f"DELETE FROM organizations WHERE id > {max_org_id}"))
    db.commit()
    db.close()
