---
name: Project-scoped query hooks — queryKey required
description: Generated hooks for project-scoped routes require explicit queryKey in UseQueryOptions
---

Generated hooks like `useListProjectSiteReports(projectId, params?, options?)` require an explicit `queryKey` in the `options.query` object — TypeScript will error without it.

**Why:** The orval-generated `UseQueryOptions` type for these hooks has `queryKey` as a required field (not optional like simple list hooks).

**How to apply:**
```tsx
useListProjectSiteReports(
  selectedProjectId ?? 0,
  { limit: 30 },
  { query: { enabled: !!selectedProjectId, queryKey: ["site-reports", selectedProjectId] } }
)
```
Same pattern for `useListProjectSafetyEvents`, `useListProjectNcrs`, `useListProjectMeetings`, `useListProjectDecisions`.
