---
name: Copilot Phase 3C — Structured Render Blocks
description: Backend generates render_blocks[] from evidence (not text parsing); frontend renders blocks directly; critical gotcha in API endpoint construction.
---

## What was built

`backend/app/ai/render_blocks.py` — new module, `compute_render_blocks(question, evidence) -> list[dict]`.
Called in `pipeline.py` alongside `compute_analytical_answer`, result threaded to `_build_response(render_blocks=...)`.
`CopilotQueryResponse` schema has `render_blocks: Optional[list[dict[str, Any]]] = None`.
Frontend `CopilotAnswer.tsx` uses `renderBlocks[]` as primary renderer; falls back to `parseFallback(content)` for LLM/generic answers.

## Block types

`project_list`, `project_card` (with highlight + runner_up), `comparison` (metrics table with winner), `safety_summary`, `ncr_summary`, `risk_summary` (categorized), `citations` (grouped by prefix).

## Critical gotcha — API endpoint manually constructs response

`api/v1/ai_copilot.py` does NOT use `CopilotQueryResponse(**result)` — it explicitly enumerates every field. **Any new schema field must be added to this constructor call explicitly**, e.g.:
```python
render_blocks=result.get("render_blocks") or [],
```
Forgetting this causes the field to silently default to `None` in the JSON response even though the pipeline returns it correctly.

**Why:** The API was written Phase 3A-style with explicit kwargs for safety. Schema has `from __future__ import annotations` + Pydantic v2 — explicit construction is stable; `**result` with extra keys would fail validation.

## Evidence snippet format

Real project snippets: `{name} ({code}): status={status}, client={client}, city={city}, start={date}, planned_finish={date}, budget={budget:,.0f} SAR`
Delimiter is `, ` (comma-space). `parse_field` regex is `field=([^,\n]+)` — stops at comma. DO NOT test with `|` as delimiter (produces garbage results).

## Query type routing

`detect_query_type()` drives which block builder is called. Returns: `highest_budget`, `lowest_budget`, `longest_delay`, `list_by_status`, `tell_more`, `compare`, `has_safety_ncr`, `risk_summary`, or fallback `""` → empty blocks.
Safety queries phrased as "show me safety events" may not hit `has_safety_ncr` pattern — the fallback text renderer handles them correctly.

## Frontend

`RichAnswer` prop `renderBlocks?: Array<Record<string, unknown>>` (not `RenderBlock[]`) to avoid TypeScript incompatibility with `copilot.tsx` `Message.renderBlocks?: Array<Record<string, unknown>>`. Internal cast to `RenderBlock[]` inside the component.
All dynamic colors use inline `style` props — Tailwind v4 does NOT scan JS object literal values.
