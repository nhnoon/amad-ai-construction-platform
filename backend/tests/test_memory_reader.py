"""Tests for the Safe Memory Reader (app/ai/memory_reader.py).

Pure unit tests — no DB, no HTTP, no LLM/Hermes call anywhere. Deterministic
relevance detection and bounded selection only.
"""
from app.ai.memory_reader import (
    build_memory_context_block,
    build_user_preferences_block,
    is_memory_relevant,
    select_relevant_memory,
)


class TestIsMemoryRelevant:
    def test_relevant_meeting_history_question_enables_memory(self):
        assert is_memory_relevant("What happened in the last meeting?") is True

    def test_relevant_previous_decisions_question_enables_memory(self):
        assert is_memory_relevant("What decisions were made previously?") is True

    def test_relevant_pending_action_items_question_enables_memory(self):
        assert is_memory_relevant("What action items are still pending?") is True

    def test_relevant_project_discussion_question_enables_memory(self):
        assert is_memory_relevant("What did we discuss about PRJ-0005?") is True

    def test_simple_current_count_question_does_not_enable_memory(self):
        assert is_memory_relevant("How many projects are delayed?") is False

    def test_simple_list_question_does_not_enable_memory(self):
        assert is_memory_relevant("Show late purchase orders.") is False

    def test_simple_current_score_question_does_not_enable_memory(self):
        assert is_memory_relevant("What is the current portfolio score?") is False

    def test_arabic_historical_question_supplier_delay_is_detected(self):
        assert is_memory_relevant("هل سبق أن ناقشنا تأخر هذا المورد؟") is True

    def test_arabic_historical_question_previous_meeting_is_detected(self):
        assert is_memory_relevant("ماذا حدث في الاجتماع السابق؟") is True

    def test_arabic_historical_question_previous_decisions_is_detected(self):
        assert is_memory_relevant("ما القرارات السابقة المتعلقة بهذا المشروع؟") is True

    def test_arabic_historical_question_remembered_context_is_detected(self):
        assert is_memory_relevant("ما الذي أتذكره عن هذا المشروع؟") is True

    def test_arabic_current_count_question_does_not_enable_memory(self):
        assert is_memory_relevant("كم عدد أوامر الشراء المتأخرة؟") is False

    def test_empty_question_is_not_relevant(self):
        assert is_memory_relevant("") is False

    def test_continuation_question_after_meeting_intent_is_relevant(self):
        assert (
            is_memory_relevant(
                "What about the owners?", intent="unknown", previous_intent="meetings",
            )
            is True
        )

    def test_continuation_question_without_prior_memory_intent_is_not_relevant(self):
        assert (
            is_memory_relevant(
                "What about the owners?", intent="unknown", previous_intent="procurement",
            )
            is False
        )


class TestSelectRelevantMemory:
    def test_exact_mtg_code_selects_matching_line(self):
        memory = (
            "[MEETING_MEMORY:MTG-1] MTG-1 | 2026-01-05 | PRJ-0023 | Kickoff | "
            "Decisions: None recorded | Action items: None recorded\n"
            "[MEETING_MEMORY:MTG-2] MTG-2 | 2026-02-01 | PRJ-0099 | Review | "
            "Decisions: None recorded | Action items: None recorded"
        )
        selected = select_relevant_memory(memory, "What happened in meeting MTG-1?")
        assert len(selected) == 1
        assert "MTG-1" in selected[0]
        assert "MTG-2" not in selected[0]

    def test_exact_prj_code_selects_matching_project_line(self):
        memory = (
            "[MEETING_MEMORY:MTG-1] MTG-1 | 2026-01-05 | PRJ-0023 | Kickoff meeting\n"
            "[MEETING_MEMORY:MTG-2] MTG-2 | 2026-02-01 | PRJ-0099 | Review meeting"
        )
        selected = select_relevant_memory(memory, "What did we discuss about PRJ-0099?")
        assert len(selected) == 1
        assert "PRJ-0099" in selected[0]

    def test_irrelevant_notes_are_excluded(self):
        memory = (
            "User prefers concise Arabic answers.\n"
            "[MEETING_MEMORY:MTG-7] MTG-7 | 2026-03-01 | PRJ-0050 | Safety review"
        )
        selected = select_relevant_memory(memory, "What happened with PRJ-0050 safety review?")
        assert len(selected) == 1
        assert "PRJ-0050" in selected[0]

    def test_no_matching_lines_returns_empty_list(self):
        memory = "User prefers concise Arabic answers.\nUnrelated note about weather."
        selected = select_relevant_memory(memory, "What happened with PRJ-0050?")
        assert selected == []

    def test_selection_respects_max_lines(self):
        memory = "\n".join(f"[MEETING_MEMORY:MTG-{i}] project PRJ-0001 note {i}" for i in range(20))
        selected = select_relevant_memory(memory, "Tell me about PRJ-0001", max_lines=3)
        assert len(selected) == 3

    def test_selection_respects_max_chars(self):
        memory = "\n".join(f"[MEETING_MEMORY:MTG-{i}] project PRJ-0001 note {i}" * 3 for i in range(20))
        selected = select_relevant_memory(memory, "Tell me about PRJ-0001", max_chars=100, max_lines=20)
        total_chars = sum(len(line) for line in selected) + max(0, len(selected) - 1)
        assert total_chars <= 100

    def test_duplicate_notes_are_removed(self):
        memory = (
            "[MEETING_MEMORY:MTG-3] project PRJ-0002 note\n"
            "[MEETING_MEMORY:MTG-3] project PRJ-0002 note\n"
            "[MEETING_MEMORY:MTG-3] project PRJ-0002 note"
        )
        selected = select_relevant_memory(memory, "Tell me about PRJ-0002")
        assert len(selected) == 1

    def test_empty_lines_are_ignored(self):
        memory = "\n\n[MEETING_MEMORY:MTG-9] project PRJ-0003 note\n\n\n"
        selected = select_relevant_memory(memory, "Tell me about PRJ-0003")
        assert selected == ["[MEETING_MEMORY:MTG-9] project PRJ-0003 note"]

    def test_meeting_memory_marker_preserved_in_selected_line(self):
        memory = "[MEETING_MEMORY:MTG-11] project PRJ-0004 note"
        selected = select_relevant_memory(memory, "Tell me about PRJ-0004")
        assert selected[0].startswith("[MEETING_MEMORY:MTG-11]")

    def test_entity_code_match_outranks_keyword_only_match(self):
        memory = (
            "General note mentioning project discussion topics broadly\n"
            "[MEETING_MEMORY:MTG-5] PRJ-0007 discussion topics"
        )
        selected = select_relevant_memory(memory, "What discussion topics for PRJ-0007?", max_lines=1)
        assert selected == ["[MEETING_MEMORY:MTG-5] PRJ-0007 discussion topics"]

    def test_empty_memory_text_returns_empty_list(self):
        assert select_relevant_memory("", "What happened in meeting MTG-1?") == []


class TestBuildMemoryContextBlock:
    def test_empty_selection_returns_empty_string(self):
        assert build_memory_context_block([]) == ""

    def test_block_is_clearly_labelled_non_authoritative(self):
        block = build_memory_context_block(["[MEETING_MEMORY:MTG-1] note"])
        assert "MEMORY CONTEXT" in block
        assert "NOT AUTHORITATIVE" in block
        assert "[MEETING_MEMORY:MTG-1] note" in block

    def test_arabic_question_uses_arabic_warning(self):
        block = build_memory_context_block(["[MEETING_MEMORY:MTG-1] note"], is_arabic=True)
        assert "سياق الذاكرة" in block
        assert "MEMORY CONTEXT" not in block


class TestBuildUserPreferencesBlock:
    def test_empty_profile_returns_empty_string(self):
        assert build_user_preferences_block("") == ""

    def test_profile_block_is_labelled_non_authoritative(self):
        block = build_user_preferences_block("Prefers Arabic answers.")
        assert "USER PREFERENCES" in block
        assert "NON-AUTHORITATIVE" in block
        assert "Prefers Arabic answers." in block

    def test_profile_block_respects_max_chars(self):
        huge = "x" * 2000
        block = build_user_preferences_block(huge, max_chars=800)
        # header + newline + truncated body must stay reasonably bounded
        body = block.split("\n", 1)[1]
        assert len(body) <= 800

    def test_arabic_profile_uses_arabic_header(self):
        block = build_user_preferences_block("Prefers Arabic answers.", is_arabic=True)
        assert "تفضيلات المستخدم" in block


class TestNoLLMCall:
    def test_memory_reader_module_never_imports_llm_providers(self):
        import app.ai.memory_reader as mod
        import inspect

        source = inspect.getsource(mod)
        assert "get_llm_provider" not in source
        assert "providers" not in source

    def test_selection_functions_work_without_llm_provider_available(self, monkeypatch):
        def _fail_if_called(*args, **kwargs):
            raise AssertionError("memory_reader must never call get_llm_provider()")

        monkeypatch.setattr(
            "app.ai.providers.factory.get_llm_provider", _fail_if_called
        )
        assert is_memory_relevant("What happened in the last meeting?") is True
        selected = select_relevant_memory("[MEETING_MEMORY:MTG-1] PRJ-0001 note", "PRJ-0001")
        assert selected
        assert build_memory_context_block(selected)
