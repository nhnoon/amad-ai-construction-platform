"""Regression tests for AMAD AI-001 Phase 2 — Language Intelligence.

Bug: execute_procurement_agent() / execute_meeting_agent() /
_execute_meeting_agent_summary() (app/ai/pipeline.py) decided response
language solely from the `language` request field, which the frontend
populates from the application's current UI-language toggle
(AIDrawer.tsx: `language: isRTL ? "ar" : "en"`) — never from the text of
the actual question the user typed. A user with an Arabic UI asking an
English question via these agent endpoints got an Arabic answer anyway,
and vice versa.

Fix: when a real `question` is supplied, response language is now
detected from that question's own text (the same `_detect_arabic()` the
general Copilot pipeline already used correctly). The `language` field is
used only as a fallback when no question text is given at all (a bare
quick-action trigger click with no free text).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _arabic_ratio(text: str) -> float:
    if not text:
        return 0.0
    arabic_chars = sum(1 for c in text if "؀" <= c <= "ۿ")
    return arabic_chars / len(text)


class TestProcurementAgentLanguage:
    def test_english_question_gets_english_answer_even_with_arabic_ui_language(
        self, client: TestClient
    ):
        """The core bug: UI language must never override an actual typed question."""
        resp = client.post(
            "/api/v1/ai/agents/procurement",
            json={"language": "ar", "question": "What are the current procurement risks?"},
        )
        assert resp.status_code == 200
        answer = resp.json()["answer"]
        assert _arabic_ratio(answer) < 0.2, f"expected English answer, got: {answer[:200]!r}"

    def test_arabic_question_gets_arabic_answer_even_with_english_ui_language(
        self, client: TestClient
    ):
        resp = client.post(
            "/api/v1/ai/agents/procurement",
            json={"language": "en", "question": "ما هي مخاطر المشتريات الحالية؟"},
        )
        assert resp.status_code == 200
        answer = resp.json()["answer"]
        assert _arabic_ratio(answer) > 0.2, f"expected Arabic answer, got: {answer[:200]!r}"

    def test_no_question_falls_back_to_ui_language(self, client: TestClient):
        """A bare quick-action trigger (no free text) has no message to detect
        language from — the UI-language field is the only reasonable signal
        here, and this must keep working."""
        resp = client.post("/api/v1/ai/agents/procurement", json={"language": "ar"})
        assert resp.status_code == 200
        answer = resp.json()["answer"]
        assert _arabic_ratio(answer) > 0.2, f"expected Arabic fallback answer, got: {answer[:200]!r}"


class TestMeetingAgentLanguage:
    def test_english_question_gets_english_answer_even_with_arabic_ui_language(
        self, client: TestClient
    ):
        resp = client.post(
            "/api/v1/ai/agents/meeting",
            json={"meeting_id": 1, "language": "ar", "question": "What happened in this meeting?"},
        )
        assert resp.status_code == 200
        answer = resp.json()["answer"]
        assert _arabic_ratio(answer) < 0.2, f"expected English answer, got: {answer[:200]!r}"

    def test_arabic_question_gets_arabic_answer_even_with_english_ui_language(
        self, client: TestClient
    ):
        resp = client.post(
            "/api/v1/ai/agents/meeting",
            json={"meeting_id": 1, "language": "en", "question": "ماذا حدث في هذا الاجتماع؟"},
        )
        assert resp.status_code == 200
        answer = resp.json()["answer"]
        assert _arabic_ratio(answer) > 0.2, f"expected Arabic answer, got: {answer[:200]!r}"

    def test_portfolio_summary_no_question_falls_back_to_ui_language(self, client: TestClient):
        """meeting_id omitted → portfolio-wide summary path
        (_execute_meeting_agent_summary); same fallback contract as procurement."""
        resp = client.post("/api/v1/ai/agents/meeting", json={"language": "ar"})
        assert resp.status_code == 200
        answer = resp.json()["answer"]
        assert _arabic_ratio(answer) > 0.2, f"expected Arabic fallback answer, got: {answer[:200]!r}"


class TestFollowUpSuggestionsMatchAnswerLanguage:
    def setup_method(self):
        from app.ai.providers.factory import reset_provider
        reset_provider()

    def teardown_method(self):
        from app.ai.providers.factory import reset_provider
        reset_provider()

    def test_arabic_question_gets_arabic_follow_ups(self, client: TestClient, monkeypatch):
        monkeypatch.setattr("app.config.settings.LLM_PROVIDER", "mock")
        from app.ai.providers.factory import reset_provider
        reset_provider()

        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "ما هو وضع المشاريع النشطة؟"},
        )
        assert resp.status_code == 200
        data = resp.json()
        suggestions = data.get("follow_up_suggestions") or []
        if suggestions:
            all_text = " ".join(suggestions)
            assert _arabic_ratio(all_text) > 0.2, (
                f"expected Arabic follow-ups to match an Arabic answer, got: {suggestions}"
            )
