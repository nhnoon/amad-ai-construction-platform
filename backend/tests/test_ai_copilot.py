"""Tests for AI Copilot API routes — end-to-end with FakeLLMProvider."""
import pytest
from fastapi.testclient import TestClient


class TestCopilotQuery:
    def test_query_returns_200(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "What is the status of active projects?"},
        )
        assert resp.status_code == 200

    def test_query_response_shape(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show me project overview"},
        )
        data = resp.json()
        assert "conversation_id" in data
        assert "message_id" in data
        assert "answer" in data
        assert "citations" in data
        assert "confidence" in data
        assert "latency_ms" in data
        assert "status" in data
        assert "intent" in data

    def test_query_creates_conversation(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "How many suppliers do we have?"},
        )
        data = resp.json()
        conv_id = data["conversation_id"]
        assert isinstance(conv_id, int)
        assert conv_id > 0

    def test_query_continues_conversation(self, client: TestClient):
        resp1 = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show me projects"},
        )
        conv_id = resp1.json()["conversation_id"]

        resp2 = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Tell me more", "conversation_id": conv_id},
        )
        assert resp2.status_code == 200
        assert resp2.json()["conversation_id"] == conv_id

    def test_question_too_long_rejected(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "x" * 2001},
        )
        assert resp.status_code == 422

    def test_empty_question_rejected(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": ""},
        )
        assert resp.status_code == 422

    def test_unknown_fields_rejected(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Hello", "unknown_field": "bad"},
        )
        assert resp.status_code == 422

    def test_project_id_context_accepted(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show me site reports", "project_id": 1},
        )
        assert resp.status_code == 200

    def test_arabic_question_handled(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "ما هو وضع المشاريع؟"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"]

    def test_unknown_domain_returns_answer(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "xyzzy frobnicator quux"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "unsupported_intent"

    def test_citations_list_type(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Give me a project overview"},
        )
        data = resp.json()
        assert isinstance(data["citations"], list)

    def test_confidence_valid_values(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show projects"},
        )
        data = resp.json()
        assert data["confidence"] in ("none", "low", "medium", "high")

    def test_intent_field_present(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show safety events"},
        )
        data = resp.json()
        assert isinstance(data["intent"], str)
        assert len(data["intent"]) > 0

    def test_audit_log_created(self, client: TestClient):
        from tests.conftest import TestingSessionLocal
        from app.models.ai_copilot import CopilotAuditLog
        db = TestingSessionLocal()
        before = db.query(CopilotAuditLog).count()
        db.close()

        client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "How many projects are active?"},
        )

        db = TestingSessionLocal()
        after = db.query(CopilotAuditLog).count()
        db.close()
        assert after > before

    def test_citation_has_required_fields(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show me project overview"},
        )
        data = resp.json()
        for cit in data["citations"]:
            assert "source_type" in cit
            assert "source_id" in cit
            assert "label" in cit


class TestConversationEndpoints:
    def test_list_conversations(self, client: TestClient):
        client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show me projects"},
        )
        resp = client.get("/api/v1/ai/conversations")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_conversation(self, client: TestClient):
        create_resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show procurement data"},
        )
        conv_id = create_resp.json()["conversation_id"]

        resp = client.get(f"/api/v1/ai/conversations/{conv_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == conv_id
        assert "title" in data

    def test_get_nonexistent_conversation_404(self, client: TestClient):
        resp = client.get("/api/v1/ai/conversations/99999999")
        assert resp.status_code == 404

    def test_list_messages(self, client: TestClient):
        create_resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "What safety events happened?"},
        )
        conv_id = create_resp.json()["conversation_id"]

        resp = client.get(f"/api/v1/ai/conversations/{conv_id}/messages")
        assert resp.status_code == 200
        messages = resp.json()
        assert isinstance(messages, list)
        assert len(messages) >= 2

    def test_messages_have_role(self, client: TestClient):
        create_resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "Show me NCRs"},
        )
        conv_id = create_resp.json()["conversation_id"]

        resp = client.get(f"/api/v1/ai/conversations/{conv_id}/messages")
        roles = {m["role"] for m in resp.json()}
        assert "user" in roles
        assert "assistant" in roles

    def test_messages_nonexistent_conversation_404(self, client: TestClient):
        resp = client.get("/api/v1/ai/conversations/99999999/messages")
        assert resp.status_code == 404

    def test_no_auth_rejected(self):
        from app.main import app as fastapi_app
        from fastapi.testclient import TestClient as DirectClient
        from app.core.deps import get_current_user
        test_app = fastapi_app
        saved = test_app.dependency_overrides.get(get_current_user)
        test_app.dependency_overrides.pop(get_current_user, None)
        try:
            with DirectClient(test_app) as c:
                resp = c.post(
                    "/api/v1/ai/copilot/query",
                    json={"question": "hello"},
                )
            assert resp.status_code == 401
        finally:
            if saved:
                test_app.dependency_overrides[get_current_user] = saved


class TestRuntimeRegressions:
    """Regression tests for bugs discovered in production.

    Bug 1 — Wrong localStorage key:
        copilot.tsx read localStorage.getItem("amad_token") but the real key
        is TOKEN_KEY = "construction_token" (auth.ts). This produced
        Authorization: Bearer null → 401, which the frontend caught as a
        generic "An error occurred" message hiding the real cause.

    Bug 2 — Wrong API URL prefix:
        copilot.tsx built URLs as ${BASE}/api/v1/... where BASE = /web, so
        the request hit /web/api/v1/... which the proxy routes to the Vite
        dev server (not the API), returning 404.
    """

    def test_bearer_null_string_rejected_401(self):
        """Regression for Bug 1: literal string 'null' as Bearer token must be rejected."""
        from app.main import app as fastapi_app
        from fastapi.testclient import TestClient as DirectClient
        from app.core.deps import get_current_user

        saved = fastapi_app.dependency_overrides.get(get_current_user)
        fastapi_app.dependency_overrides.pop(get_current_user, None)
        try:
            with DirectClient(fastapi_app) as c:
                resp = c.post(
                    "/api/v1/ai/copilot/query",
                    headers={"Authorization": "Bearer null"},
                    json={"question": "What is the status of active projects?"},
                )
            assert resp.status_code == 401, (
                f"Expected 401 for 'Bearer null' token, got {resp.status_code}. "
                "Frontend was sending this when localStorage key was wrong."
            )
        finally:
            if saved:
                fastapi_app.dependency_overrides[get_current_user] = saved

    def test_missing_auth_header_rejected_401(self):
        """Regression: no Authorization header must return 401, not 200 or 500."""
        from app.main import app as fastapi_app
        from fastapi.testclient import TestClient as DirectClient
        from app.core.deps import get_current_user

        saved = fastapi_app.dependency_overrides.get(get_current_user)
        fastapi_app.dependency_overrides.pop(get_current_user, None)
        try:
            with DirectClient(fastapi_app) as c:
                resp = c.post(
                    "/api/v1/ai/copilot/query",
                    json={"question": "What is the status of active projects?"},
                )
            assert resp.status_code == 401
        finally:
            if saved:
                fastapi_app.dependency_overrides[get_current_user] = saved

    def test_exact_failure_query_returns_200_when_authenticated(self, client: TestClient):
        """Regression: the exact query that was failing in production must succeed.

        'What is the status of active projects?' should:
        - return HTTP 200
        - route to project_overview intent
        - return real evidence from the database
        - return at least one citation
        - have confidence of medium or high
        """
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "What is the status of active projects?"},
        )
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert data["intent"] == "project_overview", f"Expected project_overview, got {data['intent']}"
        assert data["evidence_count"] > 0, "No evidence retrieved — query is not grounded"
        assert len(data["citations"]) > 0, "No citations returned"
        assert data["confidence"] in ("medium", "high"), f"Low confidence: {data['confidence']}"
        assert data["status"] == "completed", f"Unexpected status: {data['status']}"
        # Verify at least one citation has the expected project source
        source_types = {c["source_type"] for c in data["citations"]}
        assert "project" in source_types, f"No project citations found: {source_types}"

    def test_project_citations_have_href(self, client: TestClient):
        """Regression: project citations must carry ui_metadata.href for frontend links."""
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "What is the status of active projects?"},
        )
        data = resp.json()
        project_citations = [c for c in data["citations"] if c["source_type"] == "project"]
        assert project_citations, "No project citations found"
        for cit in project_citations[:3]:
            assert cit.get("ui_metadata"), f"Citation {cit['label']} missing ui_metadata"
            assert cit["ui_metadata"].get("href"), f"Citation {cit['label']} missing href"
            href: str = cit["ui_metadata"]["href"]
            assert href.startswith("/projects/"), f"Unexpected href: {href}"

    def test_conversation_persists_after_query(self, client: TestClient):
        """Regression: conversation must be retrievable after creation (persistence check)."""
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "What is the status of active projects?"},
        )
        assert resp.status_code == 200
        conv_id = resp.json()["conversation_id"]

        # Verify conversation appears in list
        list_resp = client.get("/api/v1/ai/conversations")
        assert list_resp.status_code == 200
        conv_ids = [c["id"] for c in list_resp.json()]
        assert conv_id in conv_ids, f"Conversation {conv_id} not found in list: {conv_ids[:5]}"

        # Verify messages are persisted
        msg_resp = client.get(f"/api/v1/ai/conversations/{conv_id}/messages")
        assert msg_resp.status_code == 200
        messages = msg_resp.json()
        assert len(messages) >= 2, f"Expected ≥2 messages, got {len(messages)}"
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles
