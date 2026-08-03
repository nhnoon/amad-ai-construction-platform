"""Tests for the Meeting Memory Writer (app/ai/meeting_memory.py).

Uses real seeded meeting data via a plain SQLAlchemy session (same pattern
as test_ai_retrieval.py / test_ai_memory_layer.py). No LLM/Hermes calls are
made anywhere in this module — one test asserts that explicitly.
"""
import pytest
from fastapi import HTTPException

from app.ai.memory import clear_memory_notes, get_memory_notes
from app.ai.meeting_memory import _build_meeting_note, write_meeting_memory
from app.ai.scope import AIAuthScope
from app.config import settings
from app.models.copilot_memory import AIMemoryRecord

# Real seeded rows (see backend seed data): meeting 1 belongs to project 23
# (PRJ-0023) and has decisions but no action items.
_REAL_MEETING_ID = 1
_REAL_MEETING_PROJECT_ID = 23

_USER_A = 1  # admin@construction.ai — global read access


def _global_scope(user_id: int = _USER_A, org_id: int = 1) -> AIAuthScope:
    """Phase 1 regression fix: build via the real build_ai_scope() against
    a transient admin user linked to org_id, so accessible_project_ids
    reflects that organization's real seeded projects instead of relying
    on the since-removed has_global_read bypass."""
    from datetime import datetime, timezone
    from app.ai.scope import build_ai_scope
    from app.models.auth import UserAccount
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        user = UserAccount(
            id=user_id, email=f"scope-test-{user_id}@test.local", full_name="Scope Test",
            role="admin", is_active=True, hashed_password="x", organization_id=org_id,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        return build_ai_scope(user, db)
    finally:
        db.close()


def _restricted_scope(user_id: int = _USER_A, org_id: int = 1) -> AIAuthScope:
    """A non-global-read scope with no access to project 23."""
    return AIAuthScope(
        organization_id=org_id,
        user_id=user_id,
        user_role="site_engineer",
        accessible_project_ids=(999,),
    )


@pytest.fixture
def db_session():
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _cleanup_memory(db_session):
    clear_memory_notes(db_session, _global_scope())
    db_session.query(AIMemoryRecord).filter(AIMemoryRecord.source == "meeting").delete()
    db_session.commit()
    yield
    clear_memory_notes(db_session, _global_scope())
    db_session.query(AIMemoryRecord).filter(AIMemoryRecord.source == "meeting").delete()
    db_session.commit()


class TestWriteMeetingMemorySuccess:
    def test_successful_write_creates_note(self, db_session):
        result = write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)
        assert result.created is True
        assert result.meeting_code == f"MTG-{_REAL_MEETING_ID}"
        assert result.memory_note_id is not None
        assert result.reason is None

    def test_note_contains_marker_and_confirmed_fields(self, db_session):
        write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)
        content = get_memory_notes(db_session, _global_scope())
        assert f"[MEETING_MEMORY:MTG-{_REAL_MEETING_ID}]" in content
        assert "PRJ-0023" in content
        assert "Technical Coordination Meeting" in content

    def test_note_has_no_embedded_newlines(self, db_session):
        write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)
        content = get_memory_notes(db_session, _global_scope())
        # Single-line by design (see meeting_memory.py docstring) so a later
        # append's FIFO line-trim in memory.py can't split it apart.
        assert "\n" not in content.strip()

    def test_also_writes_structured_memory_record(self, db_session):
        write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)
        rec = (
            db_session.query(AIMemoryRecord)
            .filter(AIMemoryRecord.source == "meeting", AIMemoryRecord.citation == f"MTG-{_REAL_MEETING_ID}")
            .first()
        )
        assert rec is not None
        assert rec.project_id == _REAL_MEETING_PROJECT_ID
        assert rec.category == "meeting_summary"
        assert "PRJ-0023" in rec.summary or "PRJ-0023" in rec.keywords


class TestUnauthorizedAccess:
    def test_unauthorized_meeting_access_blocked(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            write_meeting_memory(db_session, _restricted_scope(), _REAL_MEETING_ID)
        assert exc_info.value.status_code == 403

    def test_unauthorized_access_writes_nothing(self, db_session):
        with pytest.raises(HTTPException):
            write_meeting_memory(db_session, _restricted_scope(), _REAL_MEETING_ID)
        # The restricted scope shares the same user_id as the global scope
        # in this test, so this also proves a blocked attempt never reaches
        # the append step.
        assert get_memory_notes(db_session, _global_scope()) == ""


class TestMissingMeeting:
    def test_missing_meeting_raises_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            write_meeting_memory(db_session, _global_scope(), 999_999_999)
        assert exc_info.value.status_code == 404


class TestUpsertOnRewrite:
    """Default behavior (upsert=True): re-writing a meeting's memory
    refreshes it in place rather than being silently skipped — a meeting
    recorded once, before its decisions/action items existed, must not
    stay stale forever once they're added. See write_meeting_memory's
    docstring for the rationale."""

    def test_second_write_refreshes_rather_than_skips(self, db_session):
        first = write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)
        second = write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)

        assert first.created is True
        assert second.created is True
        assert second.meeting_code == first.meeting_code

    def test_rewrite_does_not_duplicate_marker_text(self, db_session):
        write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)
        write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)
        content = get_memory_notes(db_session, _global_scope())
        marker = f"[MEETING_MEMORY:MTG-{_REAL_MEETING_ID}]"
        assert content.count(marker) == 1

    def test_rewrite_does_not_duplicate_structured_record(self, db_session):
        write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)
        write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)
        count = (
            db_session.query(AIMemoryRecord)
            .filter(AIMemoryRecord.source == "meeting", AIMemoryRecord.citation == f"MTG-{_REAL_MEETING_ID}")
            .count()
        )
        assert count == 1

    def test_upsert_false_preserves_strict_skip_behavior(self, db_session):
        first = write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID, upsert=False)
        second = write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID, upsert=False)

        assert first.created is True
        assert second.created is False
        assert second.reason == "already_recorded"


class TestMissingFieldsHandledWithoutInvention:
    def test_missing_owner_and_due_date_use_not_recorded(self):
        data = {
            "meeting_id": 42,
            "meeting_title": "Synthetic Meeting",
            "meeting_date": "2026-01-01",
            "project_id": 1,
            "decisions": [
                {"id": 1, "decision_text": "Some decision", "owner": None, "decision_date": "2026-01-01"},
            ],
            "action_items": [
                {"id": 1, "description": "Some action", "owner": None, "due_date": None, "status": "open", "priority": "medium"},
            ],
        }
        note = _build_meeting_note(
            data, "MTG-42", "[MEETING_MEMORY:MTG-42]", "PRJ-9999"
        )
        assert "not recorded" in note
        # No invented owner name or date must appear.
        assert "None" not in note.replace("None recorded", "")

    def test_no_decisions_or_action_items_says_none_recorded(self):
        data = {
            "meeting_id": 43,
            "meeting_title": "Empty Meeting",
            "meeting_date": "2026-01-02",
            "project_id": 1,
            "decisions": [],
            "action_items": [],
        }
        note = _build_meeting_note(
            data, "MTG-43", "[MEETING_MEMORY:MTG-43]", "PRJ-9999"
        )
        assert "Decisions: None recorded" in note
        assert "Action items: None recorded" in note
        assert "Unresolved: None recorded" in note


class TestBoundedMemory:
    def test_memory_stays_within_configured_limit(self, db_session):
        write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)
        content = get_memory_notes(db_session, _global_scope())
        assert len(content) <= settings.AI_MEMORY_NOTE_CHAR_LIMIT


class TestNoLLMCall:
    def test_write_meeting_memory_never_calls_llm_provider(self, db_session, monkeypatch):
        def _fail_if_called(*args, **kwargs):
            raise AssertionError("write_meeting_memory must never call get_llm_provider()")

        monkeypatch.setattr(
            "app.ai.providers.factory.get_llm_provider", _fail_if_called
        )
        # Should complete without touching the LLM provider at all.
        result = write_meeting_memory(db_session, _global_scope(), _REAL_MEETING_ID)
        assert result.created is True
