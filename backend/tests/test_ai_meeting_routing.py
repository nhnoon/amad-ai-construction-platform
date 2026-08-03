"""Regression tests for meeting-code intent routing (MTG-N references).

Bug: questions naming a specific meeting (e.g. "MTG-1") that don't happen to
also contain a domain keyword ("meeting", "decision") fell through to
intent=unknown -> a full 10-domain open-domain retrieval (~52 evidence
items), producing an oversized Hermes prompt and frontend timeouts.
Separately, "Summarize meeting MTG-1" was misrouted to executive_summary
because "summarize" is an executive_summary keyword checked before anything
else, even though the question names one specific meeting.

Fix: route_intent() (app/ai/intent.py) now short-circuits to intent=
"meetings" whenever an explicit "MTG-<id>" code is present in the question,
ahead of both the executive_summary check and generic keyword scoring — an
explicit entity reference is a stronger signal than any keyword match.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.ai.intent import route_intent

MEETING_QUESTIONS = [
    "What happened in MTG-1?",
    "Summarize meeting MTG-1",
    "What decisions were made in MTG-1?",
    "What are the action items from MTG-1?",
]


class TestMeetingIntentRouting:
    """Unit-level: route_intent() is a pure function — no DB/LLM needed,
    so these run in milliseconds."""

    @pytest.mark.parametrize("question", MEETING_QUESTIONS)
    def test_routes_to_meetings_intent(self, question):
        routed = route_intent(question)
        assert routed.intent == "meetings", f"{question!r} routed to {routed.intent!r}"

    @pytest.mark.parametrize("question", MEETING_QUESTIONS)
    def test_resolves_meeting_id(self, question):
        routed = route_intent(question)
        assert routed.meeting_id == 1

    @pytest.mark.parametrize("question", MEETING_QUESTIONS)
    def test_not_multi_domain(self, question):
        routed = route_intent(question)
        assert routed.is_multi_domain is False

    @pytest.mark.parametrize("question", MEETING_QUESTIONS)
    def test_not_unsupported(self, question):
        routed = route_intent(question)
        assert routed.unsupported is False
        assert routed.confidence == 1.0

    def test_meeting_code_beats_executive_summary_keyword(self):
        """Regression: 'summarize' alone would route to executive_summary;
        an explicit MTG-N code must win."""
        routed = route_intent("Summarize meeting MTG-1")
        assert routed.intent == "meetings"
        assert routed.intent != "executive_summary"

    def test_no_meeting_code_still_routes_normally(self):
        """The short-circuit must not fire for unrelated questions with no
        meeting code — normal keyword routing still applies."""
        routed = route_intent("What is the status of active projects?")
        assert routed.meeting_id is None
        assert routed.intent == "project_overview"

    def test_different_meeting_id_resolved(self):
        routed = route_intent("What happened in MTG-42?")
        assert routed.meeting_id == 42
        assert routed.intent == "meetings"

    def test_meeting_code_case_insensitive(self):
        routed = route_intent("what happened in mtg-1?")
        assert routed.meeting_id == 1
        assert routed.intent == "meetings"


class TestMeetingEvidenceScope:
    """Verify retrieval is scoped to the one named meeting, not the whole
    portfolio — the actual root cause of the oversized-prompt/timeout bug."""

    @pytest.mark.parametrize("question", MEETING_QUESTIONS)
    def test_evidence_scoped_to_single_meeting(self, question):
        from app.database import SessionLocal
        from app.models.auth import UserAccount
        from app.ai.scope import build_ai_scope
        from app.ai.pipeline import _dispatch_single_retrieval

        db = SessionLocal()
        try:
            user = db.query(UserAccount).filter(
                UserAccount.email == "admin@construction.ai"
            ).first()
            scope = build_ai_scope(user, db)
            routed = route_intent(question)
            result = _dispatch_single_retrieval(
                intent=routed.intent,
                db=db,
                scope=scope,
                project_id=routed.project_id,
                meeting_id=routed.meeting_id,
                ncr_id=routed.ncr_id,
                question=question,
            )
            # Regression guard: this was ~52 items (10 unrelated domains)
            # before the fix. One meeting's detail (meeting + decisions +
            # action items + attendees), plus its own project context and
            # up to 5 of its project's risks, is always a small, bounded set.
            assert len(result.evidence) < 15, (
                f"Evidence not scoped to one meeting: {len(result.evidence)} items "
                f"for {question!r}"
            )
            source_types = {e.source_type for e in result.evidence}
            allowed = {
                "meeting", "project_decision", "meeting_action_item",
                "meeting_attendee", "project", "project_risk",
            }
            assert source_types <= allowed, (
                f"Unrelated evidence domains leaked in for {question!r}: {source_types}"
            )
        finally:
            db.close()


class TestMeetingCopilotEndToEnd:
    """End-to-end through /api/v1/ai/copilot/query, with the LLM provider
    forced to the fake/mock provider (same pattern as
    tests/test_hermes_provider.py) so these run fast and deterministically.
    Real Hermes calls are exactly the slow path this fix addresses — hitting
    it here would defeat the purpose of a fast regression test."""

    def setup_method(self):
        from app.ai.providers.factory import reset_provider
        reset_provider()

    def teardown_method(self):
        from app.ai.providers.factory import reset_provider
        reset_provider()

    @pytest.mark.parametrize("question", MEETING_QUESTIONS)
    def test_meeting_question_returns_meetings_intent(
        self, question, client: TestClient, monkeypatch
    ):
        monkeypatch.setattr("app.config.settings.LLM_PROVIDER", "mock")
        from app.ai.providers.factory import reset_provider
        reset_provider()

        resp = client.post("/api/v1/ai/copilot/query", json={"question": question})
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "meetings", f"{question!r} -> intent={data['intent']!r}"
        assert data["is_multi_domain"] is False
        assert data["domains_used"] == ["meetings"]
        # Regression guard: evidence_count used to balloon to ~50+ for these
        # exact phrasings via the open-domain (intent=unknown) fallback.
        assert data["evidence_count"] < 15, f"evidence_count={data['evidence_count']}"

    def test_unrelated_question_still_uses_open_domain(
        self, client: TestClient, monkeypatch
    ):
        """Sanity check: genuinely ambiguous questions with no explicit
        entity reference must still fall through to the broad open-domain
        path — the fix narrows routing only for explicit MTG-N references,
        not routing generally."""
        monkeypatch.setattr("app.config.settings.LLM_PROVIDER", "mock")
        from app.ai.providers.factory import reset_provider
        reset_provider()

        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "asdkfj qwoeiru zzxcv"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "unknown"
        assert data["is_multi_domain"] is True
        assert len(data["domains_used"]) >= 5
