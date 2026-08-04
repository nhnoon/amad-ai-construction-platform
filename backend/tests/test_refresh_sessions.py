"""RC1 Phase 1 Sprint 1 — Identity & Session Security.

Covers the refresh-token/session lifecycle end to end: login issuing a
refresh token, rotation on every /auth/refresh, reuse/replay detection,
expiry, logout (single session) vs logout-all (every session), listing
active sessions, concurrent-device independence, tenant/user isolation of
the new endpoints, and that RBAC on unrelated routes is unaffected by a
token minted through /auth/refresh instead of /auth/login.

Registration is admin-only (see app/api/v1/auth.py::register), so every
test here registers through the shared, admin-mocked ``client`` fixture
first — same as tests/test_auth.py::registered_user — and only drops into
``real_auth_client()`` (override popped) for the login/refresh/logout/
sessions calls that need a genuinely distinct, real-token identity. See
tests/conftest.py's docstring on real_auth_client() for why these two
must not overlap within a single TestClient call.
"""
import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text as sa_text

from app.config import settings
from app.core.security import decode_access_token
from tests.conftest import real_auth_client, TestingSessionLocal

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
LOGOUT_ALL_URL = "/api/v1/auth/logout-all"
SESSIONS_URL = "/api/v1/auth/sessions"
ME_URL = "/api/v1/auth/me"
PASSWORD = "Testpass1!"


def _register(client: TestClient, role="project_manager", password=PASSWORD) -> str:
    email = f"sprint1_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post(REGISTER_URL, json={
        "email": email, "password": password, "full_name": "Sprint1 Tester", "role": role,
    })
    assert r.status_code == 201, r.text
    return email


def _login(real_client: TestClient, email: str, password=PASSWORD) -> dict:
    r = real_client.post(LOGIN_URL, json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _register_and_login(client: TestClient, real_client: TestClient, role="project_manager") -> tuple[str, dict]:
    email = _register(client, role=role)
    return email, _login(real_client, email)


def _activate(real_client: TestClient, login: dict, password=PASSWORD) -> None:
    """Clears must_change_password (Phase 2's gate — see app/core/deps.py)
    via the existing change-password flow, matching
    tests/test_auth.py::active_auth_token. Needed for any test hitting a
    CurrentUser/CurrentScope-gated route. Does not touch the session: the
    refresh_token already issued by login remains valid (change-password
    only reissues an access token — see app/api/v1/auth.py::change_password,
    deliberately untouched by this sprint)."""
    r = real_client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"current_password": password, "new_password": "Changed1!"},
    )
    assert r.status_code == 200, r.text


def test_login_issues_refresh_token(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        assert "refresh_token" in login and login["refresh_token"]
        assert login["access_token"]
        assert login["token_type"] == "bearer"


def test_refresh_success_rotates_token(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        old_refresh = login["refresh_token"]

        r = c.post(REFRESH_URL, json={"refresh_token": old_refresh})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["refresh_token"] != old_refresh
        assert data["access_token"]

        me = c.get(ME_URL, headers={"Authorization": f"Bearer {data['access_token']}"})
        assert me.status_code == 200
        assert me.json()["email"] == email


def test_refresh_rotation_invalidates_old_token(client: TestClient):
    """The previous refresh token must not work a second time after a
    successful rotation — otherwise rotation would be cosmetic."""
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        old_refresh = login["refresh_token"]

        r1 = c.post(REFRESH_URL, json={"refresh_token": old_refresh})
        assert r1.status_code == 200

        r2 = c.post(REFRESH_URL, json={"refresh_token": old_refresh})
        assert r2.status_code == 401


def test_refresh_replay_revokes_whole_session(client: TestClient):
    """Replaying an already-rotated token doesn't just fail itself — it
    must kill the entire session lineage, including the token that
    replaced it, since a live copy of a consumed token is proof of theft
    or a race, either of which makes the whole chain untrustworthy."""
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        old_refresh = login["refresh_token"]

        r1 = c.post(REFRESH_URL, json={"refresh_token": old_refresh})
        assert r1.status_code == 200
        new_refresh = r1.json()["refresh_token"]

        replay = c.post(REFRESH_URL, json={"refresh_token": old_refresh})
        assert replay.status_code == 401

        followup = c.post(REFRESH_URL, json={"refresh_token": new_refresh})
        assert followup.status_code == 401


def test_stale_refresh_token_reuse_after_multiple_rotations(client: TestClient):
    """A token from several rotations back is still detected as reuse,
    not just the immediately-prior one."""
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        token_gen1 = login["refresh_token"]

        r2 = c.post(REFRESH_URL, json={"refresh_token": token_gen1})
        token_gen2 = r2.json()["refresh_token"]
        r3 = c.post(REFRESH_URL, json={"refresh_token": token_gen2})
        assert r3.status_code == 200
        token_gen3 = r3.json()["refresh_token"]

        stale = c.post(REFRESH_URL, json={"refresh_token": token_gen1})
        assert stale.status_code == 401

        current_dead = c.post(REFRESH_URL, json={"refresh_token": token_gen3})
        assert current_dead.status_code == 401


def test_refresh_unknown_token_rejected():
    with real_auth_client() as c:
        r = c.post(REFRESH_URL, json={"refresh_token": "not-a-real-token"})
        assert r.status_code == 401


def test_refresh_expired_token_rejected(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
    refresh_token = login["refresh_token"]

    token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    db = TestingSessionLocal()
    db.execute(
        sa_text("UPDATE refresh_tokens SET expires_at = now() - interval '1 day' WHERE token_hash = :h"),
        {"h": token_hash},
    )
    db.commit()
    db.close()

    with real_auth_client() as c:
        r = c.post(REFRESH_URL, json={"refresh_token": refresh_token})
        assert r.status_code == 401


def test_logout_revokes_session(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        refresh_token = login["refresh_token"]

        r = c.post(LOGOUT_URL, json={"refresh_token": refresh_token})
        assert r.status_code == 200

        after = c.post(REFRESH_URL, json={"refresh_token": refresh_token})
        assert after.status_code == 401


def test_logout_is_idempotent_and_does_not_leak_validity(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        refresh_token = login["refresh_token"]

        r1 = c.post(LOGOUT_URL, json={"refresh_token": refresh_token})
        assert r1.status_code == 200
        # Logging out again (or with a token that never existed) returns
        # the same 200 — never a different status that would reveal
        # whether the token was previously valid.
        r2 = c.post(LOGOUT_URL, json={"refresh_token": refresh_token})
        assert r2.status_code == 200
        r3 = c.post(LOGOUT_URL, json={"refresh_token": "totally-made-up"})
        assert r3.status_code == 200


def test_logout_only_kills_one_device_not_others(client: TestClient):
    """Independent logout per device: logging out session A must not
    affect session B for the same user."""
    email = _register(client)
    with real_auth_client() as c:
        login_a = _login(c, email)
        login_b = _login(c, email)

        r = c.post(LOGOUT_URL, json={"refresh_token": login_a["refresh_token"]})
        assert r.status_code == 200

        dead = c.post(REFRESH_URL, json={"refresh_token": login_a["refresh_token"]})
        assert dead.status_code == 401

        alive = c.post(REFRESH_URL, json={"refresh_token": login_b["refresh_token"]})
        assert alive.status_code == 200


def test_concurrent_sessions_tracked_independently(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login_a = _login(c, email)
        _login(c, email)
        _login(c, email)

        r = c.get(SESSIONS_URL, headers={"Authorization": f"Bearer {login_a['access_token']}"})
        assert r.status_code == 200
        sessions = r.json()
        assert len(sessions) == 3
        for s in sessions:
            assert "device" in s and "ip_address" in s and "user_agent" in s
            assert "created_at" in s and "expires_at" in s


def test_logout_all_revokes_every_session(client: TestClient):
    email = _register(client)
    with real_auth_client() as c:
        login_a = _login(c, email)
        login_b = _login(c, email)

        r = c.post(LOGOUT_ALL_URL, headers={"Authorization": f"Bearer {login_a['access_token']}"})
        assert r.status_code == 200
        assert r.json()["revoked_count"] >= 2

        for login in (login_a, login_b):
            dead = c.post(REFRESH_URL, json={"refresh_token": login["refresh_token"]})
            assert dead.status_code == 401

        # The access token itself is still valid (stateless, short-lived);
        # only the underlying sessions are gone.
        sessions = c.get(SESSIONS_URL, headers={"Authorization": f"Bearer {login_a['access_token']}"})
        assert sessions.status_code == 200
        assert sessions.json() == []


def test_sessions_tenant_isolation_across_users(client: TestClient):
    """GET /auth/sessions must never leak another user's sessions, and
    logout-all must never touch another user's sessions — regardless of
    role. This is the cross-user isolation Phase 1 already enforces for
    every other resource; the new session endpoints must uphold the same
    invariant since they introduce a brand-new per-user data surface."""
    email_a = _register(client)
    email_b = _register(client)
    with real_auth_client() as c:
        login_a = _login(c, email_a)
        login_b = _login(c, email_b)

        r = c.get(SESSIONS_URL, headers={"Authorization": f"Bearer {login_a['access_token']}"})
        assert r.status_code == 200
        assert len(r.json()) == 1  # only A's own session, never B's

        # A's logout-all must not revoke B's session.
        c.post(LOGOUT_ALL_URL, headers={"Authorization": f"Bearer {login_a['access_token']}"})
        b_still_alive = c.post(REFRESH_URL, json={"refresh_token": login_b["refresh_token"]})
        assert b_still_alive.status_code == 200


def test_rbac_unaffected_by_refreshed_access_token(client: TestClient):
    """A role-gated route must behave identically whether the caller's
    access token came from /auth/login or from a subsequent
    /auth/refresh — refresh must not upgrade, downgrade, or otherwise
    alter the caller's role/claims. Checks both directions: a role that
    IS allowed still gets in, and a role that is NOT allowed is still
    rejected, purely based on which token was refreshed."""
    PROCUREMENT_URL = "/api/v1/procurement/purchase-requests"
    email_allowed = _register(client, role="procurement_officer")
    email_denied = _register(client, role="viewer")

    with real_auth_client() as c:
        login_allowed = _login(c, email_allowed)
        _activate(c, login_allowed)
        allowed_token = c.post(
            REFRESH_URL, json={"refresh_token": login_allowed["refresh_token"]}
        ).json()["access_token"]
        r_allowed = c.get(PROCUREMENT_URL, headers={"Authorization": f"Bearer {allowed_token}"})
        assert r_allowed.status_code == 200

        login_denied = _login(c, email_denied)
        _activate(c, login_denied)
        denied_token = c.post(
            REFRESH_URL, json={"refresh_token": login_denied["refresh_token"]}
        ).json()["access_token"]
        r_denied = c.get(PROCUREMENT_URL, headers={"Authorization": f"Bearer {denied_token}"})
        assert r_denied.status_code == 403


def test_access_token_lifetime_matches_configured_short_default(client: TestClient):
    """RC1 Phase 1 Sprint 2 — Frontend Session Integration, Part G:
    ACCESS_TOKEN_EXPIRE_MINUTES was reduced from 480 to 30 now that the
    frontend transparently refreshes on a 401 (see
    artifacts/web/src/lib/auth.ts's setRefreshHandler wiring, verified
    against the real custom-fetch.ts module before this default changed).
    Asserts the *effect* of that config value on a freshly minted token's
    own exp/iat claims, rather than hardcoding "30" here — so this test
    stays correct if the configured default is tuned again later."""
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
    payload = decode_access_token(login["access_token"])
    assert payload is not None
    lifetime_seconds = payload["exp"] - payload["iat"]
    expected_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    # A few seconds of tolerance for wall-clock time elapsed during the
    # request/response round trip itself.
    assert abs(lifetime_seconds - expected_seconds) <= 5
    # The old 8-hour (480 min) lifetime must be gone, not just "some other
    # value" — this is the actual security improvement Part G exists for.
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES < 480


def test_silent_refresh_keeps_session_alive_indefinitely(client: TestClient):
    """RC1 Phase 1 Sprint 2, Part G: the whole point of shortening the
    access-token lifetime is that an ACTIVE user (one who keeps refreshing
    before their current access token expires) never gets logged out — only
    an abandoned session eventually expires. Simulates the frontend's
    silent-refresh loop with several sequential rotations and confirms the
    session is still fully usable after all of them, with a working access
    token at every step."""
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        refresh_token = login["refresh_token"]

        for _ in range(5):
            r = c.post(REFRESH_URL, json={"refresh_token": refresh_token})
            assert r.status_code == 200, r.text
            data = r.json()
            # Each rotation's access token must actually work.
            me = c.get(ME_URL, headers={"Authorization": f"Bearer {data['access_token']}"})
            assert me.status_code == 200
            refresh_token = data["refresh_token"]


def test_revoked_refresh_token_cannot_extend_session(client: TestClient):
    """RC1 Phase 1 Sprint 2, Part G explicit requirement: once a refresh
    token is revoked (via logout), it must never be usable to mint another
    access token — the session cannot be silently extended past that
    point, no matter how many times it's retried."""
    email = _register(client)
    with real_auth_client() as c:
        login = _login(c, email)
        refresh_token = login["refresh_token"]

        revoked = c.post(LOGOUT_URL, json={"refresh_token": refresh_token})
        assert revoked.status_code == 200

        for _ in range(3):
            attempt = c.post(REFRESH_URL, json={"refresh_token": refresh_token})
            assert attempt.status_code == 401
