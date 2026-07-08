---
name: Copilot Analytical Layer
description: Deterministic pre-LLM engine (analyst.py) that computes specific, data-grounded answers from evidence before calling the LLM. Key design decisions and pitfalls.
---

## What it is

`backend/app/ai/analyst.py` — called in the pipeline BEFORE `get_llm_provider()`.  
Returns a specific answer string (or None to fall through to the LLM).

Supports: highest/lowest budget, longest delay, list by status, tell me more, compare two projects, safety/NCR check, attention ranking, count.

## Where it sits in the pipeline

`pipeline.py` step 7 (inserted before the old step 7 "Provider + LLM"):
```python
analytical_answer = compute_analytical_answer(
    question=resolved_ctx.original_question,  # NOT resolved_query — see below
    evidence=all_evidence,
)
if analytical_answer is not None:
    grounding = self._validator.validate(...)
    if grounding.is_grounded:
        return self._build_response(...)
```

## Critical: use original_question, NOT resolved_query

**Why:** The context resolver enriches `resolved_query` with prior-turn text (e.g. "… which has the highest budget at 784,000,000 SAR"). If `resolved_query` is passed to `detect_query_type`, follow-up turns like "Tell me more about that project" falsely match `_HIGHEST_BUDGET` (because the enriched query contains "highest budget"). Using `original_question` gives the raw user utterance with no injected context.

**How to apply:** Always pass `resolved_ctx.original_question` to `compute_analytical_answer`, and pass `resolved_ctx.resolved_query` to `self._validator.validate` and `provider.generate`.

## Pattern detection order matters

In `detect_query_type`, `_COUNT` must be checked BEFORE `_LIST_STATUS`.  
**Why:** "How many delayed projects" contains "delayed projects" which matches `_LIST_STATUS`'s alternative pattern `\b(delayed)\s+projects?\b`. Checking count first prevents misclassification.

## Plural NCR matching

`_HAS_SAFETY_NCR` uses `ncrs?` not `ncr` to match both "NCR" and "NCRs".

## Rate limiter in tests

Add the reset fixture in `conftest.py` (not per-file) so it applies across all test files:
```python
@pytest.fixture(autouse=True)
def reset_rate_limiter_global():
    from app.ai.ratelimit import get_ai_rate_limiter
    get_ai_rate_limiter().reset(TEST_USER_ID)
    yield
```
**Why:** Test files run alphabetically (analyst → copilot → phase3b). Without a global reset, rate-limit state from one file bleeds into the next, causing 429s in `test_ai_copilot.py::TestRuntimeRegressions`.

## Provider failure test requires double-patch

`test_provider_failure_returns_200_with_error_status` mocks `get_llm_provider`. But the analytical layer now intercepts questions before the provider is called. The test must also patch the analyst:
```python
with patch("app.ai.pipeline.get_llm_provider") as mock_get, \
     patch("app.ai.pipeline.compute_analytical_answer", return_value=None):
```
**Why:** Without the second patch, a known-intent question gets answered by the analyst (status="completed"), never reaching the mocked unavailable provider.

## FakeLLMProvider

Rewritten to return evidence-grounded summaries (mentions real labels/codes) rather than the old boilerplate "Based on the provided evidence, here is a summary…". The analytical layer now handles specific analytical questions, so FakeLLM only sees synthesis/executive-summary questions.

`is_available()` must return `bool` (not raise); pipeline checks `if not provider.is_available()`.

## Comparison evidence expansion (pipeline step 6.5)

When `detect_query_type(original_question) == "compare"` and fewer than 2 project evidence items are present, the pipeline calls `get_additional_project_for_comparison` from `app.ai.retrieval.projects`. This retrieves one more authorized project (preferred status: Delayed, excluding already-cited codes) and appends it to `all_evidence` before the analyst runs.

**Key rule:** `get_additional_project_for_comparison` is imported lazily inside the pipeline function. To patch it in tests, always patch at the source module:  
`patch("app.ai.retrieval.projects.get_additional_project_for_comparison", ...)` or `patch.object(projects_module, "get_additional_project_for_comparison", ...)`.  
Patching `app.ai.pipeline.get_additional_project_for_comparison` fails (it's not a module-level attribute).

**Testing the expansion call:** A cold "compare" question routes to `intent=unknown` → early return → expansion never reached. To verify the expansion is called, use a 3-turn conversation (list delayed → highest budget → compare) so the compare turn has project context and routes to `project_overview`.

## Intent override + multi-domain routing interaction (critical)

Pipeline steps 5a/5b override `intent` (e.g. to "health" or "risks") AFTER `route_intent` runs. But `routed.is_multi_domain` and `routed.secondary_intents` still reflect the ORIGINAL routing. If the override fires but `routed.is_multi_domain=True`, the pipeline takes the `execute_multi_domain_plan` path instead of `_dispatch_single_retrieval`.

**Why this matters:** `execute_multi_domain_plan(domains=["risks","risks"])` calls `domain_retrieval_map["risks"]` = `get_project_risks()` (sparse formal register), NOT the richer multi-source `_dispatch_single_retrieval("risks")` (project_overview + project_risks + safety_summary + open_ncrs). This returns near-zero evidence → LLM says "1 سجل".

**Fix:** When an intent override fires, ALSO clear `routed.is_multi_domain = False` and `routed.secondary_intents = []` so `_dispatch_single_retrieval` is used.

**Detection symptom:** Arabic query returns mock LLM answer ("تم العثور على 1 سجل") while the same English query works correctly. Root cause: English query routed `intent=risks` (same as override target, step 5b condition checks `intent not in ("risks",...)`) while Arabic query routed `intent=project_overview` → override fires → but multi-domain routing was already set.

## Arabic copula هو/هي ≠ pronoun (context_resolver)

In `_ANAPHORIC_PATTERNS`, standalone `هو|هي|هم` is matched as a pronoun reference. But "ما هو المشروع؟" ("what is the project?") uses "هو" as an Arabic copula (not a reference to prior context).

**Fix:** Use a negative lookbehind in the pattern:
```python
re.compile(r"(?<!ما )(هو|هي|هم)|(?:هذا|هذه|تلك|ذلك|نفسه|نفسها|نفسهم)"),
```
This excludes هو/هي/هم only when preceded by "ما " (interrogative+space), preserving detection for all other cases. هذا/هذه/ذلك/etc. always indicate prior reference and are NOT excluded.

**Do NOT** use a broad guard like `if detect_query_type(q) != "unknown": anaphoric = False` — it breaks legitimate anaphoric follow-ups like "Which of them has the highest budget?" (qtype=highest_budget, but genuinely anaphoric).

## Arabic best_performing pattern — tanwin forms

`_BEST_PERFORMING` regex must match `أداءً` (with tanwin ً) not just `أداء`. Use `أداء[ًً]?` to cover both. Also add `(?:الأكثر).{0,20}(?:أداء[ًً]?|نجاح[اًً]?)` for "الأكثر أداءً" pattern.

## Test files

- `backend/tests/test_ai_analyst.py` — 56 tests for the analytical engine
- `backend/tests/test_ai_comparison_expansion.py` — 24 tests for comparison expansion

Both use the global `autouse` rate-limiter reset from `conftest.py` (no per-file duplicate needed).

## Running tests in batches (Replit resource limit)

Running the full 523-test suite in one `pytest tests/` call sometimes exits with code -1 (OOM/timeout). Split into two batches:
```bash
# Batch 1: non-AI-heavy tests (306 tests)
pytest tests/ --ignore=tests/test_ai_phase3b.py --ignore=tests/test_ai_risk_summary.py --ignore=tests/test_ai_copilot.py --ignore=tests/test_ai_analyst.py

# Batch 2: AI-heavy tests (83 + 134 = 217 tests)
pytest tests/test_ai_copilot.py tests/test_ai_analyst.py tests/test_ai_phase3b.py tests/test_ai_risk_summary.py
```
