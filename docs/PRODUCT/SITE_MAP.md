# AMAD Site Map

Reflects `components/layout.tsx` (sidebar structure) and `App.tsx` (routes)
exactly as they exist today. Drill-down pages that have no direct sidebar
entry are shown nested under the list page they're reached from, marked
`(drill-down)`. A page linked from two places in the sidebar is shown once
in its primary group with a `(cross-listed as ...)` note.

Status shorthand after each leaf: `[C]` Complete · `[P]` Partial ·
`[ ]` Placeholder · `[?]` Planned.

```
Dashboard                                                     /            [C]

Documents                                                     /documents   [C]

My Workspace
    Tasks                                                     /tasks       [ ]
    Requests & Approvals                                      /requests    [ ]
    Alerts                                                    /alerts      [C]
    Notifications                                             /notifications [ ]

Operations
    Overview                                                  /operations  [C]
    Projects                                                  /projects    [C]
        Project Detail (drill-down)                           /projects/:id [C]
    Procurement                                                /procurement [C]
    Site Reports                                               /site-reports [C]
        Site Report Detail (drill-down)     /projects/:projectId/site-reports/:reportId [C]
    Meetings                                                   /meetings    [C]
        Meeting Detail (drill-down)         /meetings/:projectId/:meetingId [C]
    RFIs                                                       /rfis        [P]
    Change Orders                                              /change-orders [C]
    Claims                                                     /claims      [C]
    Suppliers                                                  /suppliers   [C]
    Safety                                                     /safety      [C]
    Risk Register                                              /risks       [?]

AI Center                                              /ai-center/:workspace?
    Workspace
        Overview                                               ?workspace=overview  [C]  (approved v2 design benchmark)
        AI Copilot                                             ?workspace=copilot   [C]  (also standalone at /copilot)
        Memory Center                                          ?workspace=memory    [C]
    Per-Entity Intelligence
        Project Intelligence                                   ?workspace=projects       [P]
        Site Report Intelligence                                ?workspace=site-reports  [P]
        Meeting Intelligence                                    ?workspace=meetings      [P]
        Contract Intelligence                                   ?workspace=contracts     [P]
        Executive Intelligence (cross-listed under Analytics as "Insights") ?workspace=executive [C]
        Intelligent Search                                      ?workspace=search        [?]
        Email Intelligence                                      ?workspace=email         [?]
    Flagship Modules
        Project Memory                                          ?workspace=project-memory            [C]
        Predictive Intelligence                                 ?workspace=predictive-intelligence   [C]
        Supplier Risk Intelligence                              ?workspace=supplier-risk             [C]
        Material Intelligence                                   ?workspace=material-intelligence     [C]
        Cross-Project Learning                                  ?workspace=cross-project-learning    [C]
        Executive Decision Center                               ?workspace=executive-decision-center [C]

Analytics
    Reports                                                    /reports     [C]
    Insights  →  same page as AI Center → Executive Intelligence

Administration  (admin role only)
    Users                                                      /admin/users        [C]
    Settings (page itself is titled "Organizations")           /admin/organization [C]
    Audit Log                                                  /admin/audit-log    [ ]
    Integrations                                                /admin/integrations [ ]
    Billing & Subscription                                      /admin/billing      [ ]

Client Portal
    Overview                                                   /client-portal            [ ]
    Requests                                                   /client-portal/requests   [ ]
    Documents                                                  /client-portal/documents  [ ]

Auth / System  (no sidebar — outside the Layout shell)
    Login                                                      /login            [C]
    Change Password                                            /change-password  [C]
    Not Found (404)                                             (catch-all)      [C]
```

## Notes on structure, not proposals

- **AI Center is one route, sixteen components.** `/ai-center/:workspace?`
  renders a single `AICenter` page component that switches between 16
  workspace components based on the `:workspace` URL segment
  (`pages/ai-center/index.tsx`). Each still has its own sidebar entry and
  is independently bookmarkable/linkable — it just isn't 16 separate
  top-level `<Route>` entries in `App.tsx`.
- **AI Copilot has two entry points to the same component.** The sidebar's
  "AI Copilot" item links to `/ai-center/copilot` (embedded, compact,
  side-by-side with Recent Memories). A separate standalone route,
  `/copilot`, renders the same `CopilotPage` component full-height — linked
  from the Dashboard's Quick Actions and other in-app "Ask AI" entry
  points, not from the sidebar directly.
- **Executive Intelligence is genuinely cross-listed**, not duplicated —
  the sidebar's "Analytics → Insights" item and "AI Center → Executive
  Intelligence" item both point at the exact same route and component.
- **Three drill-down pages have no sidebar entry**: Project Detail, Site
  Report Detail, and Meeting Detail are reached only by clicking into a
  row on their respective list page (Projects, Site Reports, Meetings).
- **No "Quality" page exists.** Grepped for confirmation — "quality"
  appears only as a data field on Safety/Site Report pages
  (`quality_indicator`, `quality_observations`), never as a dedicated
  route or sidebar entry.
