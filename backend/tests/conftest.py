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


TEST_USER_ID: int = _resolve_test_user_id()


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
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_rate_limiter_global():
    """Reset the AI rate limiter before every test so rate-limit state from
    one test does not bleed into the next.  Applies to all test files."""
    from app.ai.ratelimit import get_ai_rate_limiter
    get_ai_rate_limiter().reset(TEST_USER_ID)
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
    db.close()

    yield

    db = TestingSessionLocal()
    db.execute(sa_text(f"DELETE FROM ai_citations WHERE id > {max_cit_id}"))
    db.execute(sa_text(f"DELETE FROM ai_messages WHERE id > {max_msg_id}"))
    db.execute(sa_text(f"DELETE FROM ai_conversations WHERE id > {max_conv_id}"))
    db.execute(sa_text(f"DELETE FROM copilot_audit_logs WHERE id > {max_audit_id}"))
    db.execute(sa_text(f"DELETE FROM project_memberships WHERE id > {max_mem_id}"))
    db.execute(sa_text(f"DELETE FROM user_accounts WHERE id > {max_user_id}"))
    db.execute(sa_text(f"DELETE FROM organizations WHERE id > {max_org_id}"))
    db.commit()
    db.close()
