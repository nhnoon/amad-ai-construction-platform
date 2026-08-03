"""Phase 2 — Security & Authentication Hardening: CORS policy (Goal 6) and
JWT improvements (Goal 5).
"""
from __future__ import annotations

import os

import pytest
from jose import jwt as jose_jwt

from app.config import settings
from app.core.cors import resolve_cors_settings
from app.core.security import create_access_token, decode_access_token


class TestCorsPolicy:
    def test_wildcard_rejected_outside_development(self):
        with pytest.raises(RuntimeError):
            resolve_cors_settings(["*"], "production")

    def test_wildcard_allowed_in_development_but_credentials_disabled(self):
        resolved = resolve_cors_settings(["*"], "development")
        assert resolved.allowed_origins == ["*"]
        assert resolved.allow_credentials is False

    def test_explicit_origins_keep_credentials_enabled(self):
        origins = ["https://app.example.com"]
        resolved = resolve_cors_settings(origins, "production")
        assert resolved.allowed_origins == origins
        assert resolved.allow_credentials is True

    def test_default_allowed_origins_is_not_wildcard(self):
        """The shared default must never be the insecure wildcard — real
        deployments override it via env var, but the fallback itself
        (used whenever ALLOWED_ORIGINS isn't set) must be safe too."""
        assert "*" not in settings.ALLOWED_ORIGINS


class TestJWTImprovements:
    def test_token_has_iat_jti_and_type_claims(self):
        token = create_access_token("someone@example.com")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    def test_two_tokens_for_the_same_subject_have_different_jti(self):
        t1 = create_access_token("someone@example.com")
        t2 = create_access_token("someone@example.com")
        p1, p2 = decode_access_token(t1), decode_access_token(t2)
        assert p1["jti"] != p2["jti"]

    def test_token_missing_type_claim_still_decodes(self):
        """Backward compatibility: a token issued before this Phase 2
        change (no "type" claim at all) must still be accepted for its
        natural remaining lifetime — this change must never invalidate
        already-issued sessions."""
        legacy_payload = {"sub": "legacy@example.com", "exp": _far_future_exp()}
        legacy_token = jose_jwt.encode(legacy_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        decoded = decode_access_token(legacy_token)
        assert decoded is not None
        assert decoded["sub"] == "legacy@example.com"

    def test_token_with_wrong_type_claim_is_rejected(self):
        bad_payload = {"sub": "someone@example.com", "exp": _far_future_exp(), "type": "refresh"}
        bad_token = jose_jwt.encode(bad_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        assert decode_access_token(bad_token) is None

    def test_expired_token_is_rejected(self):
        expired_payload = {"sub": "someone@example.com", "exp": _past_exp()}
        expired_token = jose_jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        assert decode_access_token(expired_token) is None


def _far_future_exp() -> int:
    import time
    return int(time.time()) + 3600


def _past_exp() -> int:
    import time
    return int(time.time()) - 3600
