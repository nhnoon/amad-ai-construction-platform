"""Tests for the Copilot Memory Layer (app/ai/memory.py).

All tests hit the real local Postgres test DB via a plain SQLAlchemy
session (same pattern as test_ai_retrieval.py) — no LLM/provider calls.
"""
import pytest

from app.ai.memory import (
    MemoryContentRejected,
    append_memory_note,
    clear_memory_notes,
    clear_user_profile_memory,
    get_memory_notes,
    get_user_profile_memory,
    set_memory_notes,
    set_user_profile_memory,
)
from app.ai.scope import AIAuthScope
from app.config import settings


def _scope(user_id: int, org_id: int = 1) -> AIAuthScope:
    return AIAuthScope(
        organization_id=org_id,
        user_id=user_id,
        user_role="admin",
        accessible_project_ids=(),
    )


# user_id has a real FK to user_accounts (Postgres enforces it), so these
# must be existing seeded user ids. The autouse cleanup fixture below wipes
# any memory rows for them before and after every test in this file.
_USER_A = 1  # admin@construction.ai
_USER_B = 2  # executive@construction.ai


@pytest.fixture
def db_session():
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _cleanup_memory_rows(db_session):
    """Every test starts and ends with no rows for the test user ids."""
    clear_user_profile_memory(db_session, _scope(_USER_A))
    clear_memory_notes(db_session, _scope(_USER_A))
    clear_user_profile_memory(db_session, _scope(_USER_B))
    clear_memory_notes(db_session, _scope(_USER_B))
    yield
    clear_user_profile_memory(db_session, _scope(_USER_A))
    clear_memory_notes(db_session, _scope(_USER_A))
    clear_user_profile_memory(db_session, _scope(_USER_B))
    clear_memory_notes(db_session, _scope(_USER_B))


class TestUserProfileMemory:
    def test_empty_when_unset(self, db_session):
        assert get_user_profile_memory(db_session, _scope(_USER_A)) == ""

    def test_set_then_get_round_trips(self, db_session):
        set_user_profile_memory(db_session, _scope(_USER_A), "Prefers Arabic answers.")
        assert get_user_profile_memory(db_session, _scope(_USER_A)) == "Prefers Arabic answers."

    def test_set_is_idempotent_upsert(self, db_session):
        set_user_profile_memory(db_session, _scope(_USER_A), "First preference.")
        set_user_profile_memory(db_session, _scope(_USER_A), "Updated preference.")
        assert get_user_profile_memory(db_session, _scope(_USER_A)) == "Updated preference."

    def test_content_truncated_to_char_limit(self, db_session):
        huge = "x" * (settings.AI_USER_PROFILE_CHAR_LIMIT + 500)
        stored = set_user_profile_memory(db_session, _scope(_USER_A), huge)
        assert len(stored) <= settings.AI_USER_PROFILE_CHAR_LIMIT
        assert get_user_profile_memory(db_session, _scope(_USER_A)) == stored

    def test_clear_removes_row(self, db_session):
        set_user_profile_memory(db_session, _scope(_USER_A), "Something.")
        clear_user_profile_memory(db_session, _scope(_USER_A))
        assert get_user_profile_memory(db_session, _scope(_USER_A)) == ""

    def test_scoped_per_user(self, db_session):
        set_user_profile_memory(db_session, _scope(_USER_A), "User A's preference.")
        set_user_profile_memory(db_session, _scope(_USER_B), "User B's preference.")
        assert get_user_profile_memory(db_session, _scope(_USER_A)) == "User A's preference."
        assert get_user_profile_memory(db_session, _scope(_USER_B)) == "User B's preference."

    def test_rejects_evidence_marker(self, db_session):
        with pytest.raises(MemoryContentRejected):
            set_user_profile_memory(
                db_session, _scope(_USER_A), "EVIDENCE:\n[1] Project PRJ-001"
            )

    def test_rejects_bulk_entity_codes(self, db_session):
        codes = " ".join(f"PRJ-{i:04d}" for i in range(10))
        with pytest.raises(MemoryContentRejected):
            set_user_profile_memory(db_session, _scope(_USER_A), codes)


class TestMemoryNotes:
    def test_empty_when_unset(self, db_session):
        assert get_memory_notes(db_session, _scope(_USER_A)) == ""

    def test_set_then_get_round_trips(self, db_session):
        set_memory_notes(db_session, _scope(_USER_A), "User tends to ask about safety trends.")
        assert get_memory_notes(db_session, _scope(_USER_A)) == (
            "User tends to ask about safety trends."
        )

    def test_append_accumulates_notes(self, db_session):
        append_memory_note(db_session, _scope(_USER_A), "Note one.")
        append_memory_note(db_session, _scope(_USER_A), "Note two.")
        content = get_memory_notes(db_session, _scope(_USER_A))
        assert "Note one." in content
        assert "Note two." in content

    def test_append_trims_oldest_lines_when_over_limit(self, db_session):
        limit = settings.AI_MEMORY_NOTE_CHAR_LIMIT
        # Each note ~40 chars; enough repeats to exceed the bound many times over.
        note_template = "Recurring note about topic number {i} here."
        for i in range(limit // 20):
            append_memory_note(db_session, _scope(_USER_A), note_template.format(i=i))

        content = get_memory_notes(db_session, _scope(_USER_A))
        assert len(content) <= limit
        # The earliest note must have been trimmed (FIFO), the latest kept.
        assert note_template.format(i=0) not in content
        assert note_template.format(i=(limit // 20) - 1) in content

    def test_clear_removes_row(self, db_session):
        set_memory_notes(db_session, _scope(_USER_A), "Something.")
        clear_memory_notes(db_session, _scope(_USER_A))
        assert get_memory_notes(db_session, _scope(_USER_A)) == ""

    def test_scoped_per_user(self, db_session):
        set_memory_notes(db_session, _scope(_USER_A), "A's notes.")
        set_memory_notes(db_session, _scope(_USER_B), "B's notes.")
        assert get_memory_notes(db_session, _scope(_USER_A)) == "A's notes."
        assert get_memory_notes(db_session, _scope(_USER_B)) == "B's notes."

    def test_rejects_evidence_marker_on_set(self, db_session):
        with pytest.raises(MemoryContentRejected):
            set_memory_notes(db_session, _scope(_USER_A), "EVIDENCE:\n[1] PO-1042")

    def test_rejects_evidence_marker_on_append(self, db_session):
        with pytest.raises(MemoryContentRejected):
            append_memory_note(db_session, _scope(_USER_A), "EVIDENCE:\n[1] PO-1042")

    def test_append_does_not_reject_legitimate_long_history(self, db_session):
        """Accumulated history may exceed the guard's per-write entity-code
        threshold across many appends without any single append being a dump."""
        for i in range(8):
            append_memory_note(db_session, _scope(_USER_A), f"Asked about PRJ-{i:04d} once.")
        # Should not raise — each individual append had exactly one code.
        content = get_memory_notes(db_session, _scope(_USER_A))
        assert content
