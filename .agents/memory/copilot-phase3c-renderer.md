---
name: Copilot Phase 3C — Rich Answer Renderer
description: New CopilotAnswer.tsx component that parses backend markdown-like answers into structured visual sections. No backend changes.
---

## What was built
- `artifacts/web/src/components/CopilotAnswer.tsx` — new 400-line parser + renderer
- `artifacts/web/src/pages/copilot.tsx` — 3 minimal edits: import RichAnswer, replace <p> in MessageBubble, widen assistant bubble to `w-full sm:max-w-[92%]`

## Parser rules (order matters)
1. Empty line → flush current section
2. Boilerplate regex → skip line
3. Risk emoji header `**🔴/🟠/🟡/⚠️/📦 Title** — metadata` → RiskCard section
4. `Sources:` / `المصادر:` prefix → sources section
5. `[CODE] [CODE]` only line → sources section
6. `**Title**` or `**Title** — metadata` or `**Title (CODE)**` (full-line bold) → title section
7. `N. content` → numbered section (renders as ProjectCard)
8. `- item` / `  - item` → list item (appended to current section or new list section)
9. Else → paragraph (with bold support via InlineText)

## RTL fix
Use `border-s-[3px]` and `border-s-{color}` (logical inline-start) for risk card left stripe, NOT `border-l-`. This makes Arabic (RTL) show the stripe on the right.

## Key design decisions
- Risk cards: colored `border-s-[3px]` left stripe + tinted background; 5 colors (red/orange/yellow/amber/blue)
- ProjectCard parser: `**Name** (CODE) — Status | budget: X | City | Client` pipe-delimited format
- ItemRenderer: detects `SE-XX:`, `NCR-XX:` prefixes, `Label: PRJ-XX, PRJ-YY` patterns → renders as source chips
- SourcesRow: groups citations by prefix (PRJ-=Projects, SE-=Safety, NCR-=NCR, PO-=PO) with bilingual labels
- ComparisonTable: renders `{headers, rows}` or key-value dict from `comparison_data` API field
- Boilerplate patterns: "Based on retrieved evidence", "Please refer to", "I found the following"

**Why:** Backend answers have consistent markdown-like structure but were rendered as raw whitespace-pre-wrap text. The parser avoids any LLM/backend changes while delivering card-based executive UI.

## What NOT to change
- Backend analyst.py, pipeline.py — no backend changes in 3C
- All API calls, state management, auth in copilot.tsx — untouched
- CitationsSection (expandable API citations) — still present below RichAnswer
- KeyFindingsList, ConfidenceBadge, FollowUpChips, ClarificationChips — untouched

## Test coverage
- 25/25 parser unit tests (Node.js inline)
- TypeScript typecheck: 0 errors
- Playwright E2E: structured cards verified in English + Arabic RTL
