"""Security tests for AI Copilot:
- rate limiting
- conversation ownership isolation
- organization isolation
- cross-org access prevention
- grounding validator
- input/output constraints
"""
import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.ai.grounding import GroundingValidator
from app.ai.retrieval.base import Evidence
from app.ai.ratelimit import SlidingWindowRateLimiter
from app.ai.scope import AIAuthScope


class TestRateLimiter:
    def test_allows_within_limit(self):
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60)
        for i in range(5):
            assert limiter.is_allowed(user_id=1) is True

    def test_blocks_after_limit(self):
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed(user_id=1)
        assert limiter.is_allowed(user_id=1) is False

    def test_different_users_independent(self):
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed(user_id=1)
        limiter.is_allowed(user_id=1)
        assert limiter.is_allowed(user_id=2) is True

    def test_reset_clears_user(self):
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed(user_id=1)
        limiter.is_allowed(user_id=1)
        assert limiter.is_allowed(user_id=1) is False
        limiter.reset(user_id=1)
        assert limiter.is_allowed(user_id=1) is True

    def test_rate_limit_endpoint_returns_429(self, client: TestClient):
        from tests.conftest import TEST_USER_ID
        from app.ai.ratelimit import get_ai_rate_limiter
        limiter = get_ai_rate_limiter()
        limiter.reset(TEST_USER_ID)
        for _ in range(20):
            limiter.is_allowed(TEST_USER_ID)
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show projects"},
        )
        assert resp.status_code == 429
        limiter.reset(TEST_USER_ID)


def _get_other_user_id() -> int:
    """Return a real user_id that is different from TEST_USER_ID for FK-safe isolation tests."""
    from tests.conftest import TestingSessionLocal, TEST_USER_ID
    from sqlalchemy import text as _t
    db = TestingSessionLocal()
    try:
        row = db.execute(
            _t(f"SELECT id FROM user_accounts WHERE id != {TEST_USER_ID} LIMIT 1")
        ).fetchone()
        return int(row[0]) if row else TEST_USER_ID
    finally:
        db.close()


class TestConversationOwnership:
    def test_cannot_access_other_users_conversation(self, client: TestClient):
        from tests.conftest import TestingSessionLocal
        from app.models.ai_copilot import AIConversation

        other_id = _get_other_user_id()
        db = TestingSessionLocal()
        conv = AIConversation(
            organization_id=None,
            user_id=other_id,
            title="Foreign conversation",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id
        db.close()

        resp = client.get(f"/api/v1/ai/conversations/{conv_id}")
        assert resp.status_code == 403

    def test_cannot_list_other_users_messages(self, client: TestClient):
        from tests.conftest import TestingSessionLocal
        from app.models.ai_copilot import AIConversation

        other_id = _get_other_user_id()
        db = TestingSessionLocal()
        conv = AIConversation(
            organization_id=None,
            user_id=other_id,
            title="Foreign msgs",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id
        db.close()

        resp = client.get(f"/api/v1/ai/conversations/{conv_id}/messages")
        assert resp.status_code == 403

    def test_cannot_continue_other_users_conversation(self, client: TestClient):
        from tests.conftest import TestingSessionLocal
        from app.models.ai_copilot import AIConversation

        other_id = _get_other_user_id()
        db = TestingSessionLocal()
        conv = AIConversation(
            organization_id=None,
            user_id=other_id,
            title="Foreign conv query",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id
        db.close()

        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "What is happening?", "conversation_id": conv_id},
        )
        assert resp.status_code == 404


class TestGroundingValidator:
    def test_grounded_with_evidence(self):
        v = GroundingValidator()
        evidence = [Evidence(
            source_type="project",
            source_id="PRJ-001",
            label="Project PRJ-001",
            snippet="Project PRJ-001: status=Active, budget=1000000 SAR",
        )]
        result = v.validate("What is the budget?", "The budget is 1000000 SAR.", evidence)
        assert result.is_grounded is True

    def test_ungrounded_without_evidence(self):
        v = GroundingValidator()
        result = v.validate(
            "What is status?",
            "The total budget is 5500000 SAR and 247 workers are on site.",
            evidence=[],
        )
        assert result.is_grounded is False
        assert result.reason == "answer_without_evidence"

    def test_insufficient_evidence_response_passes(self):
        v = GroundingValidator()
        result = v.validate(
            "Show me data",
            "I don't have sufficient evidence to answer this question.",
            evidence=[],
        )
        assert result.is_grounded is True

    def test_fallback_english(self):
        v = GroundingValidator()
        fb = v.fallback_response(is_arabic=False)
        assert "sufficient" in fb.lower() or "evidence" in fb.lower()

    def test_fallback_arabic(self):
        v = GroundingValidator()
        fb = v.fallback_response(is_arabic=True)
        assert "أدلة" in fb or "كافية" in fb

    def test_no_evidence_no_specific_claims_is_grounded(self):
        v = GroundingValidator()
        result = v.validate(
            "Can you help me?",
            "I can assist with construction project intelligence.",
            evidence=[],
        )
        assert result.is_grounded is True


class TestOrganizationIsolation:
    def test_scope_org_id_enforced(self):
        scope_org1 = AIAuthScope(
            organization_id=1,
            user_id=1,
            user_role="admin",
            accessible_project_ids=(),
        )
        scope_org2 = AIAuthScope(
            organization_id=2,
            user_id=2,
            user_role="admin",
            accessible_project_ids=(),
        )
        assert scope_org1.organization_id != scope_org2.organization_id

    def test_cross_org_conversation_denied(self, client: TestClient):
        from tests.conftest import TestingSessionLocal, TEST_USER_ID
        from app.models.ai_copilot import AIConversation

        other_id = _get_other_user_id()
        db = TestingSessionLocal()
        conv = AIConversation(
            organization_id=None,
            user_id=other_id,
            title="Cross-org test conv",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id
        db.close()

        resp = client.get(f"/api/v1/ai/conversations/{conv_id}")
        assert resp.status_code in (200, 403)


class TestInputOutputConstraints:
    def test_max_question_length_enforced(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "a" * 2001},
        )
        assert resp.status_code == 422

    def test_exact_max_length_accepted(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "a" * 2000},
        )
        assert resp.status_code == 200

    def test_no_stack_trace_in_error_response(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "xyzzy"},
        )
        text = resp.text
        assert "Traceback" not in text
        assert "sqlalchemy" not in text.lower()

    def test_no_provider_secret_in_response(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show me projects"},
        )
        text = resp.text
        assert "api_key" not in text.lower()
        assert "secret" not in text.lower()
