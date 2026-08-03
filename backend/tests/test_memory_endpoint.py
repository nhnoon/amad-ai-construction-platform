"""Tests for GET /api/v1/ai/memory — the read-only HTTP endpoint added in
Phase 4 (AI Center frontend integration), extended in Phase 6 with
deterministic marker-based grouping (app/ai/memory_reader.py::
group_memory_notes). No LLM/Hermes call, no memory write, no audit
mutation — this is a pure read + deterministic-format endpoint."""
import pytest
from fastapi.testclient import TestClient

from app.ai.memory import append_memory_note, clear_memory_notes, set_user_profile_memory, clear_user_profile_memory
from app.ai.scope import AIAuthScope
from tests.conftest import TEST_USER_ID, TestingSessionLocal

_USER_B = 2  # executive@construction.ai — real seeded user, distinct from TEST_USER_ID


def _scope(user_id: int = TEST_USER_ID, org_id: int = 1) -> AIAuthScope:
    return AIAuthScope(
        organization_id=org_id, user_id=user_id, user_role="admin",
        accessible_project_ids=(),
    )


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _cleanup_memory(db_session):
    for uid in (TEST_USER_ID, _USER_B):
        clear_memory_notes(db_session, _scope(uid))
        clear_user_profile_memory(db_session, _scope(uid))
    yield
    for uid in (TEST_USER_ID, _USER_B):
        clear_memory_notes(db_session, _scope(uid))
        clear_user_profile_memory(db_session, _scope(uid))


class TestReadOwnMemory:
    def test_authenticated_user_reads_own_memory(self, client: TestClient, db_session):
        append_memory_note(db_session, _scope(), "[MEETING_MEMORY:MTG-1] | MTG-1 | 2025-06-15 | PRJ-0023 | Kickoff | Decisions: approved scope")
        resp = client.get("/api/v1/ai/memory")
        assert resp.status_code == 200
        data = resp.json()
        assert "[MEETING_MEMORY:MTG-1]" in data["memory_notes"]


class TestCrossUserIsolation:
    def test_cannot_read_another_users_memory(self, client: TestClient, db_session):
        # client is always authenticated as TEST_USER_ID (see conftest) —
        # write a note for a DIFFERENT real user and confirm it never
        # appears in TEST_USER_ID's response.
        append_memory_note(db_session, _scope(_USER_B), "[MEETING_MEMORY:MTG-99] USER-B-ONLY-SECRET")
        resp = client.get("/api/v1/ai/memory")
        assert resp.status_code == 200
        assert "USER-B-ONLY-SECRET" not in resp.json()["memory_notes"]
        assert resp.json()["groups"]["meeting"] == []


class TestEmptyMemoryResponse:
    def test_empty_memory_returns_empty_groups(self, client: TestClient):
        resp = client.get("/api/v1/ai/memory")
        assert resp.status_code == 200
        data = resp.json()
        assert data["memory_notes"] == ""
        assert data["profile_memory"] == ""
        assert data["groups"] == {
            "meeting": [], "project": [], "decision": [], "supplier": [], "other": [],
        }


class TestGrouping:
    def test_meeting_marker_grouped_correctly(self, client: TestClient, db_session):
        append_memory_note(
            db_session, _scope(),
            "[MEETING_MEMORY:MTG-1] | MTG-1 | 2025-06-15 | PRJ-0023 | Kickoff Meeting | Decisions: approved scope",
        )
        resp = client.get("/api/v1/ai/memory")
        groups = resp.json()["groups"]
        assert len(groups["meeting"]) == 1
        item = groups["meeting"][0]
        assert item["title"] == "Kickoff Meeting"
        assert item["date"] == "2025-06-15"
        assert item["summary"] == "Decisions: approved scope"
        assert item["importance"] is None
        assert groups["project"] == []
        assert groups["decision"] == []
        assert groups["supplier"] == []

    def test_unknown_marker_grouped_as_other(self, client: TestClient, db_session):
        append_memory_note(db_session, _scope(), "[SOMETHING_ELSE:X-1] unrecognized marker text")
        resp = client.get("/api/v1/ai/memory")
        groups = resp.json()["groups"]
        assert groups["meeting"] == []
        assert len(groups["other"]) == 1
        assert groups["other"][0]["summary"] == "[SOMETHING_ELSE:X-1] unrecognized marker text"

    def test_plain_text_note_grouped_as_other_with_exact_text(self, client: TestClient, db_session):
        append_memory_note(db_session, _scope(), "Just a plain preference note.")
        resp = client.get("/api/v1/ai/memory")
        groups = resp.json()["groups"]
        assert len(groups["other"]) == 1
        assert groups["other"][0]["summary"] == "Just a plain preference note."
        assert groups["other"][0]["title"] is None
        assert groups["other"][0]["date"] is None
        assert groups["other"][0]["importance"] is None

    def test_no_fabricated_metadata_for_project_decision_supplier(self, client: TestClient, db_session):
        """Only Meeting Memory has a real backend writer — Project/Decision/
        Supplier must stay honestly empty, never populated with invented
        data, even when other memory exists."""
        append_memory_note(db_session, _scope(), "[MEETING_MEMORY:MTG-1] | MTG-1 | 2025-06-15 | PRJ-0023 | Kickoff | Decisions: x")
        resp = client.get("/api/v1/ai/memory")
        groups = resp.json()["groups"]
        assert groups["project"] == []
        assert groups["decision"] == []
        assert groups["supplier"] == []


class TestNoLLMCall:
    def test_read_memory_never_calls_llm_provider(self, client: TestClient, db_session, monkeypatch):
        def _fail_if_called(*args, **kwargs):
            raise AssertionError("GET /api/v1/ai/memory must never call get_llm_provider()")

        monkeypatch.setattr("app.ai.providers.factory.get_llm_provider", _fail_if_called)
        append_memory_note(db_session, _scope(), "[MEETING_MEMORY:MTG-1] | MTG-1 | 2025-06-15 | PRJ-0023 | Kickoff | Decisions: x")
        resp = client.get("/api/v1/ai/memory")
        assert resp.status_code == 200


class TestRouteCorrectness:
    def test_route_is_under_api_v1_ai_prefix(self, client: TestClient):
        # Confirms base URL / route prefix wiring: /api/v1/ai/memory (not
        # /api/ai/memory, /ai/memory, or /api/v1/memory).
        assert client.get("/api/v1/ai/memory").status_code == 200
        assert client.get("/api/ai/memory").status_code == 404
        assert client.get("/ai/memory").status_code == 404


class TestProfileMemory:
    def test_returns_stored_profile_memory(self, client: TestClient, db_session):
        set_user_profile_memory(db_session, _scope(), "Prefers concise answers.")
        resp = client.get("/api/v1/ai/memory")
        assert resp.status_code == 200
        assert resp.json()["profile_memory"] == "Prefers concise answers."
