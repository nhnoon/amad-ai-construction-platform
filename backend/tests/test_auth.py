import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.deps import get_current_user


REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"

TEST_EMAIL = "testuser_phase2@example.com"
TEST_PASSWORD = "Testpass1!"
# project_manager is a global-read-within-organization role (see
# app/ai/scope.py) — test_dashboard_with_auth needs a role that actually
# has org-wide access post-Phase-1 scoping; site_engineer would correctly
# see zero data with no project membership, which isn't what that test
# is checking.
TEST_ROLE = "project_manager"


@pytest.fixture(scope="module")
def raw_client():
    """TestClient with NO dependency overrides — exercises real auth logic."""
    saved = app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as c:
        yield c
    if saved is not None:
        app.dependency_overrides[get_current_user] = saved


@pytest.fixture(scope="module")
def registered_user(client: TestClient):
    r = client.post(REGISTER_URL, json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": "Phase 2 Tester",
        "role": TEST_ROLE,
    })
    if r.status_code == 409:
        pass
    else:
        assert r.status_code == 201
    return {"email": TEST_EMAIL, "password": TEST_PASSWORD}


@pytest.fixture(scope="module")
def auth_token(client: TestClient, registered_user):
    r = client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="module")
def active_auth_token(client: TestClient):
    """Phase 2 — Security & Authentication Hardening: every newly
    registered user must change their password before accessing anything
    other than /auth/me and /auth/change-password (see
    tests/test_password_change_gate.py for dedicated coverage of that gate
    itself). ``auth_token`` above is deliberately left representing a
    freshly registered, not-yet-changed user; this fixture is a separate,
    throwaway account that completes the mandatory change, for the tests
    below that need to call a real, non-exempt endpoint.

    Deliberately does NOT request ``raw_client`` as a co-fixture: that
    fixture is module-scoped and pops app.dependency_overrides for the
    rest of the module the first time ANY test uses it — requesting it
    here too would mean pytest pops the override before this fixture's
    own body runs, breaking the ``client.post(REGISTER_URL, ...)`` call
    below (which needs the admin override active). Using the
    conftest-level ``real_auth_client()`` context manager instead scopes
    the pop/restore to just the one call that actually needs it. The
    override is also force-set immediately below (not just assumed)
    since an EARLIER test in this same module may already have triggered
    `raw_client` and left the override popped for the rest of the module."""
    import uuid
    from app.core.deps import get_current_user
    from tests.conftest import override_get_current_user, real_auth_client

    app.dependency_overrides[get_current_user] = override_get_current_user

    email = f"testuser_phase2_active_{uuid.uuid4().hex[:8]}@example.com"
    password = "Testpass1!"
    r = client.post(REGISTER_URL, json={
        "email": email, "password": password,
        "full_name": "Phase 2 Active Tester", "role": TEST_ROLE,
    })
    assert r.status_code == 201
    login_resp = client.post(LOGIN_URL, json={"email": email, "password": password})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    with real_auth_client() as raw:
        change_resp = raw.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": password, "new_password": "Changed1!"},
        )
        assert change_resp.status_code == 200
        return change_resp.json()["access_token"]


def test_register_success(client: TestClient):
    import uuid
    unique_email = f"new_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(REGISTER_URL, json={
        "email": unique_email,
        "password": "Newpass1!",
        "full_name": "New User",
        "role": "site_engineer",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == unique_email
    assert data["role"] == "site_engineer"
    assert "hashed_password" not in data


def test_register_duplicate_email(client: TestClient, registered_user):
    r = client.post(REGISTER_URL, json={
        "email": registered_user["email"],
        "password": "Another1!",
        "role": "site_engineer",
    })
    assert r.status_code == 409


def test_register_invalid_role(client: TestClient):
    r = client.post(REGISTER_URL, json={
        "email": "badrole@example.com",
        "password": "Test1234!",
        "role": "superuser",
    })
    assert r.status_code == 422


def test_register_short_password(client: TestClient):
    r = client.post(REGISTER_URL, json={
        "email": "shortpw@example.com",
        "password": "abc",
        "role": "site_engineer",
    })
    assert r.status_code == 422


def test_login_success(client: TestClient, registered_user):
    r = client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == registered_user["email"]
    assert data["user"]["role"] == TEST_ROLE


def test_login_wrong_password(client: TestClient, registered_user):
    r = client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": "wrongpassword",
    })
    assert r.status_code == 401


def test_login_unknown_email(client: TestClient):
    r = client.post(LOGIN_URL, json={
        "email": "nobody@nowhere.com",
        "password": "Test1234!",
    })
    assert r.status_code == 401


def test_me_authenticated(raw_client: TestClient, auth_token):
    r = raw_client.get(ME_URL, headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == TEST_EMAIL
    assert data["role"] == TEST_ROLE


def test_me_no_token(raw_client: TestClient):
    r = raw_client.get(ME_URL)
    assert r.status_code == 401


def test_me_invalid_token(raw_client: TestClient):
    r = raw_client.get(ME_URL, headers={"Authorization": "Bearer invalidtoken"})
    assert r.status_code == 401


def test_dashboard_requires_auth(raw_client: TestClient):
    r = raw_client.get("/api/v1/dashboard/summary")
    assert r.status_code == 401


def test_dashboard_with_auth(raw_client: TestClient, active_auth_token):
    r = raw_client.get("/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {active_auth_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "total_projects" in data
    assert "late_purchase_orders" in data
    assert data["total_projects"] > 0
