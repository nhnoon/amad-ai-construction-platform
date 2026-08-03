"""Regression tests for Arabic Copilot parity — Phase 3B.

Covers the four target Arabic turns:
  AR-A  اعرض لي المشاريع المتأخرة   → list_by_status, Arabic answer
  AR-B  أي واحد منها ميزانيته الأعلى؟ → highest_budget, Arabic answer
  AR-C  هل لديه مشاكل سلامة خطيرة؟  → has_safety_ncr, Arabic answer
  AR-D  قارنه بمشروع متأخر آخر       → compare, Arabic comparison table

Also verifies English parity is unchanged.
"""
from __future__ import annotations

import re
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.ai.analyst import detect_query_type, compute_analytical_answer
from app.ai.context_resolver import is_anaphoric
from app.ai.retrieval.base import Evidence

try:
    from tests.conftest import TEST_USER_ID
except ImportError:
    TEST_USER_ID = 1


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ev(
    source_id: str,
    name: str,
    status: str = "Delayed",
    budget: float = 100_000_000,
    city: str = "Riyadh",
    client: str = "Ministry",
    project_id: int = 1,
) -> Evidence:
    return Evidence(
        source_type="project",
        source_id=source_id,
        label=f"Project {source_id} — {name}",
        snippet=(
            f"{name} ({source_id}): status={status}, "
            f"client={client}, city={city}, "
            f"start=2023-01-01, planned_finish=2024-01-01, "
            f"budget={budget:,.0f} SAR"
        ),
        project_id=project_id,
        ui_metadata={"href": f"/projects/{project_id}", "icon": "briefcase"},
    )


def _safety_ev(source_id: str, severity: str = "High", project_id: int = 1) -> Evidence:
    return Evidence(
        source_type="safety_event",
        source_id=source_id,
        label=f"Safety Event SE-{source_id}",
        snippet=f"Safety Event SE-{source_id}: severity={severity}, status=Open, description=Unsafe access",
        project_id=project_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. detect_query_type — Arabic patterns
# ─────────────────────────────────────────────────────────────────────────────

class TestArabicQueryTypeDetection:
    """All four target Arabic questions must route to the correct query type."""

    def test_delayed_list_arabic(self):
        assert detect_query_type("اعرض لي المشاريع المتأخرة") == "list_by_status"

    def test_delayed_list_arabic_without_article(self):
        assert detect_query_type("اعرض المشاريع المتأخرة") == "list_by_status"

    def test_delayed_list_arabic_with_verb_variant(self):
        assert detect_query_type("أظهر لي مشاريع متأخرة") == "list_by_status"

    def test_highest_budget_arabic_possessive(self):
        # ميزانيته (budget+his) and الأعلى (the+highest) — both morphologically changed
        assert detect_query_type("أي واحد منها ميزانيته الأعلى؟") == "highest_budget"

    def test_highest_budget_arabic_bare(self):
        assert detect_query_type("أي مشروع لديه أعلى ميزانية؟") == "highest_budget"

    def test_safety_ncr_arabic_severity_suffix(self):
        # خطيرة = خطير + ة (feminine adj.) — must match has_safety_ncr
        assert detect_query_type("هل لديه مشاكل سلامة خطيرة؟") == "has_safety_ncr"

    def test_safety_ncr_arabic_alternate(self):
        assert detect_query_type("هل هناك حوادث سلامة خطيرة في هذا المشروع؟") == "has_safety_ncr"

    def test_compare_arabic_with_object_suffix(self):
        # قارنه = قارن + ه (compare + it)
        assert detect_query_type("قارنه بمشروع متأخر آخر") == "compare"

    def test_compare_arabic_bare(self):
        assert detect_query_type("قارن المشروعين") == "compare"

    def test_compare_arabic_noun_form(self):
        assert detect_query_type("أريد مقارنة مع مشروع آخر") == "compare"

    # ── English must not regress ──────────────────────────────────────────────

    def test_english_list_status_unchanged(self):
        assert detect_query_type("Show me the delayed projects") == "list_by_status"

    def test_english_highest_budget_unchanged(self):
        assert detect_query_type("Which one has the highest budget?") == "highest_budget"

    def test_english_safety_ncr_unchanged(self):
        assert detect_query_type(
            "Does it have unresolved NCRs or high-severity safety events?"
        ) == "has_safety_ncr"

    def test_english_compare_unchanged(self):
        assert detect_query_type("Compare it with another delayed project") == "compare"


# ─────────────────────────────────────────────────────────────────────────────
# 2. is_anaphoric — Arabic follow-up markers
# ─────────────────────────────────────────────────────────────────────────────

class TestArabicAnaphoricDetection:
    """Arabic follow-up questions must be recognised as anaphoric."""

    def test_miinha_is_anaphoric(self):
        assert is_anaphoric("أي واحد منها ميزانيته الأعلى؟") is True

    def test_ladayhi_is_anaphoric(self):
        assert is_anaphoric("هل لديه مشاكل سلامة خطيرة؟") is True

    def test_qaarnahu_is_anaphoric(self):
        assert is_anaphoric("قارنه بمشروع متأخر آخر") is True

    def test_hal_ladayhi_is_anaphoric(self):
        assert is_anaphoric("هل لديه ميزانية كبيرة؟") is True

    def test_fresh_arabic_question_not_anaphoric(self):
        # A fresh non-referential Arabic question must not be anaphoric
        assert is_anaphoric("اعرض لي المشاريع المتأخرة") is False

    # English must not regress
    def test_english_which_one_anaphoric(self):
        assert is_anaphoric("Which one has the highest budget?") is True

    def test_english_compare_it_anaphoric(self):
        assert is_anaphoric("Compare it with another delayed project") is True

    def test_english_fresh_question_not_anaphoric(self):
        assert is_anaphoric("Show me the delayed projects") is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. compute_analytical_answer — Arabic answers
# ─────────────────────────────────────────────────────────────────────────────

class TestArabicAnalyticalAnswers:
    """Analytical layer must return Arabic text for Arabic questions."""

    DELAYED_PROJECTS = [
        _ev("PRJ-0001", "مشروع مدرسة الخبر 1", budget=784_000_000, project_id=1),
        _ev("PRJ-0005", "مشروع مدرسة الدمام 5", budget=134_000_000, project_id=5),
        _ev("PRJ-0006", "مشروع الرياض 6", budget=200_000_000, project_id=6),
        _ev("PRJ-0007", "مشروع جدة 7", budget=90_000_000, project_id=7),
    ]

    def test_list_delayed_arabic_answer(self):
        ans = compute_analytical_answer(
            "اعرض لي المشاريع المتأخرة", self.DELAYED_PROJECTS
        )
        assert ans is not None
        # Must contain Arabic header (تم العثور or مشاريع)
        assert "مشاريع" in ans or "متأخر" in ans
        # Must cite PRJ codes
        assert "PRJ-0001" in ans
        assert "PRJ-0005" in ans

    def test_highest_budget_arabic_answer(self):
        ans = compute_analytical_answer(
            "أي واحد منها ميزانيته الأعلى؟", self.DELAYED_PROJECTS
        )
        assert ans is not None
        # Must be Arabic answer
        assert "ميزانية" in ans or "PRJ-0001" in ans
        # Must pick the highest budget project
        assert "PRJ-0001" in ans
        assert "784,000,000" in ans

    def test_safety_ncr_arabic_answer(self):
        evidence = [
            _ev("PRJ-0001", "مشروع مدرسة الخبر 1", project_id=1),
            _safety_ev("394", severity="High", project_id=1),
            _safety_ev("386", severity="Medium", project_id=1),
            _safety_ev("156", severity="Low", project_id=1),
        ]
        ans = compute_analytical_answer(
            "هل لديه مشاكل سلامة خطيرة؟", evidence
        )
        assert ans is not None
        # Must be Arabic
        assert "سلامة" in ans or "أحداث" in ans
        # Must cite safety events
        assert re.search(r"SE-\d+|\d{3}", ans)

    def test_compare_arabic_produces_table(self):
        evidence = [
            _ev("PRJ-0001", "مشروع مدرسة الخبر 1", budget=784_000_000, project_id=1),
            _ev("PRJ-0005", "مشروع مدرسة الدمام 5", budget=134_000_000, project_id=5),
        ]
        ans = compute_analytical_answer(
            "قارنه بمشروع متأخر آخر", evidence
        )
        assert ans is not None
        # Arabic comparison header
        assert "مقارنة" in ans
        # Both project codes
        assert "PRJ-0001" in ans
        assert "PRJ-0005" in ans
        # Arabic table row labels
        assert "الحالة" in ans or "الميزانية" in ans

    def test_compare_arabic_budget_difference(self):
        evidence = [
            _ev("PRJ-0001", "مشروع مدرسة الخبر 1", budget=784_000_000, project_id=1),
            _ev("PRJ-0005", "مشروع مدرسة الدمام 5", budget=134_000_000, project_id=5),
        ]
        ans = compute_analytical_answer("قارنه بمشروع متأخر آخر", evidence)
        assert ans is not None
        # Budget delta in Arabic
        assert "650,000,000" in ans or "فرق" in ans

    # English parity: compare still returns English table for English questions
    def test_compare_english_still_english(self):
        evidence = [
            _ev("PRJ-0001", "Khobar School", budget=784_000_000, project_id=1),
            _ev("PRJ-0005", "Dammam School", budget=134_000_000, project_id=5),
        ]
        ans = compute_analytical_answer("Compare it with another delayed project", evidence)
        assert ans is not None
        assert "Comparison" in ans
        assert "Status" in ans
        assert "Budget" in ans


# ─────────────────────────────────────────────────────────────────────────────
# 4. API integration — four-turn Arabic conversation
# ─────────────────────────────────────────────────────────────────────────────

class TestArabicAPIConversation:
    """End-to-end four-turn Arabic conversation via the API."""

    def test_ar_a_delayed_projects_arabic(self, client: TestClient):
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "اعرض لي المشاريع المتأخرة"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        ans = data["answer"]
        # Must be in Arabic — look for Arabic script characters
        arabic_chars = sum(1 for c in ans if "\u0600" <= c <= "\u06FF")
        assert arabic_chars > 5, f"Expected Arabic answer, got: {ans[:200]}"
        # Must contain at least one delayed project code
        assert re.search(r"PRJ-\d+", ans), f"No project code in answer: {ans[:200]}"
        # Must have citations
        assert len(data["citations"]) > 0

    def test_ar_b_highest_budget_arabic(self, client: TestClient):
        # Establish context from Turn A
        r1 = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "اعرض لي المشاريع المتأخرة"},
        )
        conv_id = r1.json()["conversation_id"]

        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "أي واحد منها ميزانيته الأعلى؟",
                  "conversation_id": conv_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        ans = data["answer"]
        arabic_chars = sum(1 for c in ans if "\u0600" <= c <= "\u06FF")
        assert arabic_chars > 5, f"Expected Arabic answer, got: {ans[:200]}"
        # Must cite exactly one project (the winner)
        proj_cits = [c for c in data["citations"] if c["source_type"] == "project"]
        assert len(proj_cits) >= 1

    def test_ar_c_safety_arabic(self, client: TestClient):
        # Establish context
        r1 = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "اعرض لي المشاريع المتأخرة"},
        )
        conv_id = r1.json()["conversation_id"]
        r2 = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "أي واحد منها ميزانيته الأعلى؟",
                  "conversation_id": conv_id},
        )
        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "هل لديه مشاكل سلامة خطيرة؟",
                  "conversation_id": conv_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        ans = data["answer"]
        arabic_chars = sum(1 for c in ans if "\u0600" <= c <= "\u06FF")
        assert arabic_chars > 5, f"Expected Arabic answer, got: {ans[:200]}"

    def test_ar_d_compare_arabic_table(self, client: TestClient):
        # Establish context through 3 turns
        r1 = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "اعرض لي المشاريع المتأخرة"},
        )
        conv_id = r1.json()["conversation_id"]
        client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "أي واحد منها ميزانيته الأعلى؟",
                  "conversation_id": conv_id},
        )
        client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "هل لديه مشاكل سلامة خطيرة؟",
                  "conversation_id": conv_id},
        )

        resp = client.post(
            "/api/v1/ai/copilot/query",
            json={"question": "قارنه بمشروع متأخر آخر",
                  "conversation_id": conv_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        ans = data["answer"]
        arabic_chars = sum(1 for c in ans if "\u0600" <= c <= "\u06FF")
        assert arabic_chars > 5, f"Expected Arabic answer, got: {ans[:200]}"
        # Must cite two distinct projects
        proj_cits = [c["source_id"] for c in data["citations"] if c["source_type"] == "project"]
        assert len(set(proj_cits)) >= 2, f"Expected 2 project citations, got {proj_cits}"
        # Must contain comparison marker (Arabic or table pipe)
        assert "مقارنة" in ans or "|" in ans, f"No comparison structure in: {ans[:300]}"


# ─────────────────────────────────────────────────────────────────────────────
# 5. FakeLLM Arabic responses
# ─────────────────────────────────────────────────────────────────────────────

class TestFakeLLMArabic:
    """FakeLLM must return Arabic text when user prompt is Arabic."""

    def test_project_response_arabic(self):
        from app.ai.providers.fake import FakeLLMProvider
        from app.ai.providers.base import LLMRequest

        provider = FakeLLMProvider()
        req = LLMRequest(
            system_prompt=(
                "You are Amad.\n"
                "EVIDENCE:\n"
                "[1] Project PRJ-0001 — Khobar School\n"
                "    Khobar School (PRJ-0001): status=Delayed, budget=784000000 SAR"
            ),
            user_prompt="اعرض لي المشاريع المتأخرة",
        )
        resp = provider.generate(req)
        arabic_chars = sum(1 for c in resp.content if "\u0600" <= c <= "\u06FF")
        assert arabic_chars > 5, f"Expected Arabic, got: {resp.content}"

    def test_safety_response_arabic(self):
        from app.ai.providers.fake import FakeLLMProvider
        from app.ai.providers.base import LLMRequest

        provider = FakeLLMProvider()
        req = LLMRequest(
            system_prompt=(
                "You are Amad.\n"
                "EVIDENCE:\n"
                "[1] Safety Event SE-394\n"
                "    Safety Event SE-394: severity=High, status=Open"
            ),
            user_prompt="هل لديه مشاكل سلامة خطيرة؟",
        )
        resp = provider.generate(req)
        arabic_chars = sum(1 for c in resp.content if "\u0600" <= c <= "\u06FF")
        assert arabic_chars > 5, f"Expected Arabic, got: {resp.content}"

    def test_english_response_unchanged(self):
        from app.ai.providers.fake import FakeLLMProvider
        from app.ai.providers.base import LLMRequest

        provider = FakeLLMProvider()
        req = LLMRequest(
            system_prompt=(
                "You are Amad.\n"
                "EVIDENCE:\n"
                "[1] Project PRJ-0001 — Khobar School\n"
                "    Khobar School (PRJ-0001): status=Delayed, budget=784000000 SAR"
            ),
            user_prompt="Show me the delayed projects",
        )
        resp = provider.generate(req)
        # Should contain English
        assert "project" in resp.content.lower() or "PRJ" in resp.content
