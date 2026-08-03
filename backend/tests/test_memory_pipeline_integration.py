"""Integration tests for the Safe Memory Reader wired into app/ai/pipeline.py.

Exercises the real /api/v1/ai/copilot/query endpoint (same TestClient/db
pattern as test_ai_copilot.py) with LLM_PROVIDER=mock (FakeLLMProvider,
already the default — see app/config.py). A capturing wrapper around the
fake provider lets tests inspect the exact system_prompt the pipeline built,
without ever hitting a real LLM/Hermes.
"""
import pytest

import app.ai.pipeline as pipeline_module
from app.ai.memory import (
    append_memory_note,
    clear_memory_notes,
    clear_user_profile_memory,
    set_user_profile_memory,
)
from app.ai.providers.fake import FakeLLMProvider
from app.ai.scope import AIAuthScope
from tests.conftest import TEST_USER_ID, TestingSessionLocal

_USER_B = 2  # executive@construction.ai — real seeded user, distinct from TEST_USER_ID


def _scope(user_id: int, org_id: int = 1) -> AIAuthScope:
    return AIAuthScope(
        organization_id=org_id,
        user_id=user_id,
        user_role="admin",
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
    clear_memory_notes(db_session, _scope(TEST_USER_ID))
    clear_user_profile_memory(db_session, _scope(TEST_USER_ID))
    clear_memory_notes(db_session, _scope(_USER_B))
    clear_user_profile_memory(db_session, _scope(_USER_B))
    yield
    clear_memory_notes(db_session, _scope(TEST_USER_ID))
    clear_user_profile_memory(db_session, _scope(TEST_USER_ID))
    clear_memory_notes(db_session, _scope(_USER_B))
    clear_user_profile_memory(db_session, _scope(_USER_B))


class _CapturingProvider:
    """Wraps the real FakeLLMProvider and records the last LLMRequest sent,
    so tests can inspect the exact prompt without a real LLM/Hermes call."""

    def __init__(self):
        self._inner = FakeLLMProvider()
        self.last_request = None
        self.call_count = 0

    @property
    def provider_name(self):
        return self._inner.provider_name

    @property
    def model_name(self):
        return self._inner.model_name

    def is_available(self):
        return True

    def generate(self, request):
        self.last_request = request
        self.call_count += 1
        return self._inner.generate(request)


@pytest.fixture
def capturing_provider(monkeypatch):
    provider = _CapturingProvider()
    monkeypatch.setattr(pipeline_module, "get_llm_provider", lambda: provider)
    return provider


def _post(client, question: str, **kwargs):
    return client.post("/api/v1/ai/copilot/query", json={"question": question, **kwargs})


class TestMemoryInjectionOnRelevantQuestion:
    def test_relevant_meeting_question_injects_memory_block(
        self, client, db_session, capturing_provider
    ):
        append_memory_note(
            db_session, _scope(TEST_USER_ID),
            "[MEETING_MEMORY:MTG-1] MTG-1 | 2026-01-05 | PRJ-0023 | "
            "Technical Coordination Meeting | Decisions: Approved design change",
        )

        resp = _post(client, "What happened in meeting MTG-1?")
        assert resp.status_code == 200

        prompt = capturing_provider.last_request.system_prompt
        assert "MEMORY CONTEXT" in prompt
        assert "MTG-1" in prompt

    def test_memory_block_appears_before_evidence_label(
        self, client, db_session, capturing_provider
    ):
        append_memory_note(
            db_session, _scope(TEST_USER_ID),
            "[MEETING_MEMORY:MTG-1] MTG-1 | 2026-01-05 | PRJ-0023 | Kickoff",
        )
        resp = _post(client, "What happened in meeting MTG-1?")
        assert resp.status_code == 200

        prompt = capturing_provider.last_request.system_prompt
        memory_idx = prompt.index("MEMORY CONTEXT")
        # "\nEVIDENCE:\n" (not bare "EVIDENCE:") to avoid matching the rule-3
        # phrase "INSUFFICIENT_EVIDENCE:" earlier in the same prompt.
        evidence_idx = prompt.index("\nEVIDENCE:\n")
        assert memory_idx < evidence_idx


class TestMemoryNotInjectedOnSimpleQuestion:
    def test_simple_current_question_does_not_inject_memory(
        self, client, db_session, capturing_provider
    ):
        append_memory_note(
            db_session, _scope(TEST_USER_ID),
            "[MEETING_MEMORY:MTG-1] MTG-1 | 2026-01-05 | PRJ-0023 | Kickoff",
        )
        resp = _post(client, "What is the current portfolio score?")
        assert resp.status_code == 200

        prompt = capturing_provider.last_request.system_prompt
        assert "MEMORY CONTEXT" not in prompt


class TestMemoryDoesNotBecomeEvidence:
    def test_memory_does_not_create_citations(self, client, db_session, capturing_provider):
        append_memory_note(
            db_session, _scope(TEST_USER_ID),
            "[MEETING_MEMORY:MTG-1] MTG-1 | 2026-01-05 | PRJ-0023 | Kickoff",
        )
        resp = _post(client, "What happened in meeting MTG-1?")
        assert resp.status_code == 200
        data = resp.json()

        for citation in data["citations"]:
            assert "MEETING_MEMORY" not in (citation.get("evidence_snippet") or "")
            assert "MEETING_MEMORY" not in (citation.get("label") or "")

    def test_memory_does_not_change_evidence_count(self, client, db_session, capturing_provider):
        question = "What happened in meeting MTG-1?"

        resp_without_memory = _post(client, question)
        assert resp_without_memory.status_code == 200
        count_without_memory = resp_without_memory.json()["evidence_count"]

        append_memory_note(
            db_session, _scope(TEST_USER_ID),
            "[MEETING_MEMORY:MTG-1] MTG-1 | 2026-01-05 | PRJ-0023 | Kickoff",
        )
        resp_with_memory = _post(client, question)
        assert resp_with_memory.status_code == 200
        count_with_memory = resp_with_memory.json()["evidence_count"]

        assert count_with_memory == count_without_memory


class TestEmptyMemoryUnchangedBehavior:
    def test_empty_memory_leaves_behavior_unchanged(self, client, db_session, capturing_provider):
        # No memory notes seeded — cleanup fixture guarantees a clean slate.
        resp = _post(client, "What happened in meeting MTG-1?")
        assert resp.status_code == 200

        prompt = capturing_provider.last_request.system_prompt
        assert "MEMORY CONTEXT" not in prompt


class TestMemoryServiceFailureIsNonFatal:
    def test_memory_read_failure_does_not_fail_request(
        self, client, db_session, capturing_provider, monkeypatch
    ):
        def _boom(db, scope):
            raise RuntimeError("simulated memory service failure")

        monkeypatch.setattr(pipeline_module, "get_memory_notes", _boom)

        resp = _post(client, "What happened in meeting MTG-1?")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("completed", "insufficient_evidence")

        prompt = capturing_provider.last_request.system_prompt
        assert "MEMORY CONTEXT" not in prompt


class TestLiveEvidenceRemainsAuthoritative:
    def test_system_prompt_instructs_evidence_over_memory(
        self, client, db_session, capturing_provider
    ):
        append_memory_note(
            db_session, _scope(TEST_USER_ID),
            "[MEETING_MEMORY:MTG-1] MTG-1 | 2026-01-05 | PRJ-0023 | Kickoff",
        )
        resp = _post(client, "What happened in meeting MTG-1?")
        assert resp.status_code == 200

        prompt = capturing_provider.last_request.system_prompt
        assert "EVIDENCE always wins" in prompt
        assert "cite it as a source" in prompt

    def test_evidence_block_reflects_live_data_not_memory(
        self, client, db_session, capturing_provider
    ):
        # Memory claims something stale; live retrieval must still be the
        # thing that populates EVIDENCE:, independent of memory content.
        append_memory_note(
            db_session, _scope(TEST_USER_ID),
            "[MEETING_MEMORY:MTG-1] MTG-1 | STALE-DATE | STALE-PROJECT | Stale summary",
        )
        resp = _post(client, "What happened in meeting MTG-1?")
        assert resp.status_code == 200

        prompt = capturing_provider.last_request.system_prompt
        # "\nEVIDENCE:\n" (not bare "EVIDENCE:") to avoid splitting on the
        # rule-3 phrase "INSUFFICIENT_EVIDENCE:" earlier in the prompt.
        evidence_section = prompt.split("\nEVIDENCE:\n", 1)[1]
        assert "STALE-PROJECT" not in evidence_section


class TestMemoryUserIsolation:
    def test_different_user_cannot_read_another_users_memory(
        self, client, db_session, capturing_provider
    ):
        append_memory_note(
            db_session, _scope(_USER_B),
            "[MEETING_MEMORY:MTG-1] MTG-1 | USER-B-ONLY-SECRET-NOTE",
        )
        # Client authenticates as TEST_USER_ID (see conftest.override_get_current_user).
        resp = _post(client, "What happened in meeting MTG-1?")
        assert resp.status_code == 200

        prompt = capturing_provider.last_request.system_prompt
        assert "USER-B-ONLY-SECRET-NOTE" not in prompt


class TestNoExtraLLMCallFromMemory:
    def test_memory_injection_does_not_add_an_extra_provider_call(
        self, client, db_session, capturing_provider
    ):
        append_memory_note(
            db_session, _scope(TEST_USER_ID),
            "[MEETING_MEMORY:MTG-1] MTG-1 | 2026-01-05 | PRJ-0023 | Kickoff",
        )
        resp = _post(client, "What happened in meeting MTG-1?")
        assert resp.status_code == 200
        assert capturing_provider.call_count == 1


class TestDeterministicAnalystShortcutUnaffected:
    def test_count_question_still_bypasses_llm_provider(
        self, client, db_session, capturing_provider
    ):
        # "how many" is a deterministic analyst.py shortcut (app/ai/analyst.py) —
        # answered directly from live evidence, no LLM/provider call at all.
        # Memory integration must not change this.
        resp = _post(client, "How many projects are delayed?")
        assert resp.status_code == 200
        assert capturing_provider.call_count == 0


class TestUserPreferenceMemoryInjection:
    def test_profile_memory_injected_as_separate_non_authoritative_block(
        self, client, db_session, capturing_provider
    ):
        set_user_profile_memory(db_session, _scope(TEST_USER_ID), "Prefers concise answers.")
        append_memory_note(
            db_session, _scope(TEST_USER_ID),
            "[MEETING_MEMORY:MTG-1] MTG-1 | 2026-01-05 | PRJ-0023 | Kickoff",
        )
        resp = _post(client, "What happened in meeting MTG-1?")
        assert resp.status_code == 200

        prompt = capturing_provider.last_request.system_prompt
        assert "USER PREFERENCES" in prompt
        assert "Prefers concise answers." in prompt
