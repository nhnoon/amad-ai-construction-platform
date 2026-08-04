"""RC1 Phase 1 Sprint 1 — Identity & Session Security.

Refresh-token session lifecycle: opaque, server-side, rotated-on-use
tokens (deliberately NOT JWTs — see create_access_token/decode_access_token
in security.py for the separate, stateless access-token side, which is
unaffected by anything in this module). Mirrors this codebase's existing
"DB-persisted because it must survive restarts and be individually
revocable" precedent (see login_security.py's per-account lockout being
DB-persisted rather than in-memory, for the same reason).

Rotation & reuse detection
---------------------------
Every login starts a new *family* (one row, family_id = secrets.token_hex).
Every successful refresh revokes the presented token and inserts a new row
in the SAME family — this is the rotation. If a refresh token is ever
presented that is already revoked, that is proof the token has already
been consumed once (either by the legitimate client's own prior rotation
being replayed, or by an attacker who obtained a copy) — a live, unexpired
copy of an already-used token should never exist. Either way the whole
family is no longer trustworthy, so every token in it is revoked
immediately, forcing a fresh login for that session lineage. This is what
defends against replay attacks, rotated-token reuse, and an attacker
holding a second live copy of the same refresh token.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import Request
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..config import settings
from ..models.auth import RefreshToken, UserAccount
from .login_security import client_ip_from_request


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _new_raw_token() -> str:
    return secrets.token_urlsafe(48)


def _new_family_id() -> str:
    return secrets.token_hex(16)


def _expiry_for(remember_me: bool) -> datetime:
    days = (
        settings.REFRESH_TOKEN_REMEMBER_ME_EXPIRE_DAYS
        if remember_me
        else settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return datetime.now(timezone.utc) + timedelta(days=days)


def _as_aware(dt: datetime) -> datetime:
    """Defends against a naive datetime slipping in from a non-Postgres
    test backend; Postgres TIMESTAMPTZ columns already round-trip aware
    UTC datetimes, so this is a no-op in the normal path."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _request_context(request: Request, device: str | None) -> dict:
    return {
        "device": device,
        "ip_address": client_ip_from_request(request),
        "user_agent": request.headers.get("user-agent"),
    }


def create_session(
    db: Session,
    user: UserAccount,
    request: Request,
    remember_me: bool = False,
    device: str | None = None,
) -> tuple[str, RefreshToken]:
    """Start a brand-new session (family) — called on login. Returns the
    raw token (given to the client, never stored) and the persisted row."""
    raw_token = _new_raw_token()
    row = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        family_id=_new_family_id(),
        remember_me=remember_me,
        expires_at=_expiry_for(remember_me),
        **_request_context(request, device),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return raw_token, row


class RefreshOutcome(str, Enum):
    INVALID = "invalid"
    EXPIRED = "expired"
    REUSED = "reused"
    OK = "ok"


@dataclass
class RefreshResult:
    outcome: RefreshOutcome
    user: UserAccount | None = None
    raw_token: str | None = None
    row: RefreshToken | None = None


def _revoke_family(db: Session, family_id: str, now: datetime) -> None:
    db.query(RefreshToken).filter(
        and_(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
    ).update({"revoked_at": now}, synchronize_session=False)


def rotate_refresh_token(
    db: Session,
    raw_token: str,
    request: Request,
    device: str | None = None,
) -> RefreshResult:
    """Validate + rotate a presented refresh token. Never raises — every
    outcome (including reuse/expiry) is reported via RefreshResult.outcome
    so the caller (the /auth/refresh endpoint) decides the HTTP response."""
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == _hash_token(raw_token)).first()
    if row is None:
        return RefreshResult(outcome=RefreshOutcome.INVALID)

    now = datetime.now(timezone.utc)

    if row.revoked_at is not None:
        # Reuse of an already-consumed token — kill the whole family
        # regardless of why it was revoked (prior rotation or an explicit
        # earlier logout): it must never mint a new access token again.
        _revoke_family(db, row.family_id, now)
        db.commit()
        # RC1 Phase 1 Sprint 4 — Enterprise Audit Logging: `row` included
        # (was omitted on every failure outcome before) purely so
        # /auth/refresh can attribute its audit event to an actor; the
        # HTTP response is unaffected either way.
        return RefreshResult(outcome=RefreshOutcome.REUSED, row=row)

    if _as_aware(row.expires_at) <= now:
        row.revoked_at = now
        db.commit()
        return RefreshResult(outcome=RefreshOutcome.EXPIRED, row=row)

    user = db.query(UserAccount).filter(UserAccount.id == row.user_id).first()
    if user is None or not user.is_active:
        row.revoked_at = now
        db.commit()
        return RefreshResult(outcome=RefreshOutcome.INVALID, row=row)

    # Rotate: revoke the presented token and mint its replacement in the
    # same family, so GET /auth/sessions and logout-all still see one
    # logical session across the whole rotation chain.
    row.revoked_at = now
    row.last_used_at = now
    new_raw = _new_raw_token()
    new_row = RefreshToken(
        user_id=row.user_id,
        token_hash=_hash_token(new_raw),
        family_id=row.family_id,
        remember_me=row.remember_me,
        expires_at=_expiry_for(row.remember_me),
        **_request_context(request, device or row.device),
    )
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return RefreshResult(outcome=RefreshOutcome.OK, user=user, raw_token=new_raw, row=new_row)


def revoke_token(db: Session, raw_token: str) -> int | None:
    """Logout: revoke the presented token's whole family (kills the
    session, not just this one physical token). Idempotent by design —
    returns None (not an error) for an unknown or already-revoked token,
    so a repeated/racing logout call never leaks whether a token was
    still live. Returns the session's owner user_id on an actual
    revocation — RC1 Phase 1 Sprint 4 (Enterprise Audit Logging) added
    this return value (was plain bool) purely so the /auth/logout route
    can attribute its audit event to an actor; the logout response body
    is unaffected either way (see app/api/v1/auth.py::logout, which
    always returns the same message regardless)."""
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == _hash_token(raw_token)).first()
    if row is None or row.revoked_at is not None:
        return None
    user_id = row.user_id
    _revoke_family(db, row.family_id, datetime.now(timezone.utc))
    db.commit()
    return user_id


def revoke_all_for_user(db: Session, user_id: int) -> int:
    """Logout-all: revoke every live session (every family) for this user.
    Scoped strictly to user_id — callers must never pass another user's id
    (there is no cross-user session control in this app; see
    app/api/v1/auth.py::logout_all, which always uses the caller's own
    identity, never a client-supplied user id)."""
    now = datetime.now(timezone.utc)
    count = (
        db.query(RefreshToken)
        .filter(and_(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)))
        .update({"revoked_at": now}, synchronize_session=False)
    )
    db.commit()
    return count


def get_active_sessions(db: Session, user_id: int) -> list[RefreshToken]:
    now = datetime.now(timezone.utc)
    return (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .order_by(RefreshToken.created_at.desc())
        .all()
    )
