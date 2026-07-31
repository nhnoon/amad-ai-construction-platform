import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
from jose import JWTError, jwt
from ..config import settings


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def generate_temporary_password(length: int = 16) -> str:
    """Cryptographically secure random temporary password (Phase 2 —
    Security & Authentication Hardening). Replaces the previous shared,
    hardcoded default ("Welcome123!") issued to every newly created user —
    see app/api/v1/admin/users.py::create_user and app/schemas/admin.py.
    ``secrets.token_urlsafe`` draws from the OS CSPRNG (os.urandom), not
    Python's non-cryptographic ``random`` module."""
    return secrets.token_urlsafe(length)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": str(subject),
        "exp": expire,
        # Phase 2 additions — purely additive claims. decode_access_token()
        # only requires "sub"/"exp" (checked by python-jose itself), so
        # tokens issued before this change remain valid for their natural
        # remaining lifetime; this never breaks existing sessions.
        "iat": now,
        "jti": secrets.token_hex(16),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
            # A few seconds of leeway absorbs clock drift between the
            # issuing and validating processes without weakening the
            # expiry check in any meaningful way.
            options={"leeway": 10},
        )
    except JWTError:
        return None
    # Lenient by design: only reject a token that explicitly claims a
    # non-"access" type (defends against a future token kind — e.g. a
    # password-reset token — being misused as a session token). A token
    # issued before this claim existed has no "type" at all and is still
    # accepted, so already-issued tokens are not invalidated by this change.
    token_type = payload.get("type")
    if token_type is not None and token_type != "access":
        return None
    return payload
