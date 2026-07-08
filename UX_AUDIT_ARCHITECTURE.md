# AMAD V2 Information Architecture
## Visual Guide & Navigation Hierarchy

---

## CURRENT STATE (V1)

```
┌─────────────────────────────────────────────────────────┐
│                    NAVIGATION (9 items)                 │
│  Dashboard | Operations | Documents | Reports | Admin   │
│  ┗ Projects | Meetings | Procurement | Suppliers | ... │
└─────────────────────────────────────────────────────────┘

PROBLEMS:
✗ Too many sidebar items (makes it hard to find things)
✗ Operations and Documents mostly empty
✗ Dashboard too heavy with charts
✗ No unified workspace
✗ No global search
```

---

## TARGET STATE (V2)

```
┌─────────────────────────────────────────────────────────────────┐
│ GLOBAL SEARCH (Cmd+K) [🔍 Search across platform...]           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  MAIN NAVIGATION (5 items)                                       │
│                                                                   │
│  1. 📊 DASHBOARD (Executive Focus)                              │
│     ├─ Portfolio Health Score                                    │
│     ├─ Critical Alerts (top 5)                                   │
│     ├─ Projects At Risk                                          │
│     ├─ Safety Critical                                           │
│     └─ Budget Overrun                                            │
│                                                                   │
│  2. 🏗️ OPERATIONS (Operational Workspace)                        │
│     ├─ 📁 Projects (module card → list/kanban/timeline)         │
│     ├─ 📅 Meetings (module card → list/calendar)                │
│     ├─ 🛒 Procurement (module card → PR/PO tables)              │
│     ├─ 📋 Site Reports (module card → card list)                │
│     ├─ ❓ RFIs (module card → table)                             │
│     ├─ 🔄 Change Orders (module card → list)                    │
│     └─ ⚖️ Claims (module card → list)                            │
│                                                                   │
│  3. 📚 DOCUMENTS (Repository Hub)                                │
│     ├─ 📋 Contracts (category card)                              │
│     ├─ ❓ RFIs (category card)                                   │
│     ├─ 📝 Meeting Minutes (category card)                        │
│     ├─ 📐 Drawings (category card)                               │
│     ├─ 🛒 Purchase Files (category card)                         │
│     ├─ 🛡️ Safety Docs (category card)                           │
│     ├─ ✅ Quality Docs (category card)                           │
│     └─ 📊 Other (category card)                                  │
│                                                                   │
│  4. 📈 REPORTS (Report Generation)                               │
│     ├─ Executive Report (template card)                          │
│     ├─ Weekly Update (template card)                             │
│     ├─ Portfolio Analysis (template card)                        │
│     ├─ Custom Report Builder (template card)                     │
│     └─ Scheduled Reports (recent list)                           │
│                                                                   │
│  5. ⚙️ ADMINISTRATION (System Management)                         │
│     ├─ Employees (tab)                                           │
│     ├─ Organizations (tab)                                       │
│     ├─ Roles & Permissions (tab)                                 │
│     ├─ Approvals (tab)                                           │
│     ├─ Audit Logs (tab)                                          │
│     └─ Settings (tab)                                            │
│                                                                   │
│  🧠 AMAD AI (Floating Button - Bottom Right)                     │
│     ├─ Meeting Intelligence (module)                             │
│     ├─ Site Intelligence (module)                                │
│     ├─ Procurement Intelligence (module)                         │
│     ├─ Enterprise Memory (module)                                │
│     └─ Ask Construction AI (module)                              │
│                                                                   │
│  ⚡ ALERTS (Accessible from Dashboard)                           │
│     ├─ Critical (expanded)                                       │
│     ├─ High (expanded)                                           │
│     ├─ Medium (collapsed)                                        │
│     └─ Low (collapsed)                                           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## PAGE FLOW DIAGRAMS

### Flow 1: Executive Morning

```
         [Login]
           ↓
    [Dashboard]
    ┌─────────────────────────────────┐
    │ Portfolio Score: 72/100         │
    │ Critical Alerts: 5              │
    │ Projects At Risk: 3             │
    │ Safety Events (High): 2         │
    │ Budget Overrun: $2.1M           │
    └─────────────────────────────────┘
         ↓
    Sees "3 Projects At Risk"
         ↓
    Click "Projects At Risk"
         ↓
    [Projects] Page filters to "At Risk"
         ↓
    Reviews list
         ↓
    Exit or drill into project detail
```

### Flow 2: Project Manager Daily Work

```
         [Login]
           ↓
    [Operations Workspace]
    ┌─────────────────────────────────┐
    │  📁 Projects (48)               │
    │  📅 Meetings (12 upcoming)      │
    │  🛒 Procurement (23 open)       │
    │  📋 Site Reports (latest: today)│
    │  ❓ RFIs (7 pending)            │
    │  🔄 Change Orders (3)           │
    │  ⚖️ Claims (2 open)             │
    └─────────────────────────────────┘
         ↓
    Click "Meetings" card
         ↓
    [Meetings] Page shows today's meetings
         ↓
    Click meeting → [Meeting Detail]
         ↓
    Review decisions + attendees
         ↓
    Back to Operations
         ↓
    Click "Projects" card
         ↓
    [Projects] Page shows all projects
         ↓
    Search "Downtown" → finds Downtown Plaza
         ↓
    Click → [Project Detail]
         ↓
    Drag to [AMAD AI] → Click "Meeting Intelligence"
         ↓
    [AI Workspace] shows: "Summarize last meeting"
         ↓
    AI generates summary
         ↓
    Close AI drawer, continue work
```

### Flow 3: Document Search

```
         [Any Page]
           ↓
    Press Cmd+K → Global Search focus
           ↓
    Type "Downtown Contract"
           ↓
    Results show:
    - Downtown_Agreement.pdf (Documents > Contracts)
    - Downtown_Tender.docx (Documents > Contracts)
    - Downtown_Spec.pdf (Documents > Drawings)
           ↓
    Click first result
           ↓
    [Documents] Page → Contracts category opens
           ↓
    File highlighted + preview available
           ↓
    [Download] or [View]
```

### Flow 4: Admin User Management

```
         [Login as Admin]
           ↓
    [Administration]
    ┌─────────────────────────────────┐
    │ Tabs: Employees | Org | Roles   │
    │       Approvals | Audit | Setg  │
    └─────────────────────────────────┘
         ↓
    Click "Employees" tab
         ↓
    [Employee List] shows all users
         ↓
    Search "Jane"
         ↓
    Find "Jane Doe"
         ↓
    Click [Edit]
         ↓
    [Edit User Modal]:
    - Email: jane@company.com
    - Role: [Dropdown: Site Engineer → Project Manager]
    - Status: Active
    - [Save]
         ↓
    User updated
         ↓
    Entry appears in "Audit Logs" tab:
    "2024-02-15 14:30 - admin - Changed Jane's role"
```

### Flow 5: Creating a Report

```
         [Any Page]
           ↓
    [Reports]
    ┌─────────────────────────────────┐
    │ Select Report Type:             │
    │ ┌──────────────────────────┐   │
    │ │ Executive Report        │   │
    │ │ [Generate]              │   │
    │ └──────────────────────────┘   │
    │                                 │
    │ ┌──────────────────────────┐   │
    │ │ Weekly Update           │   │
    │ │ [Generate]              │   │
    │ └──────────────────────────┘   │
    └─────────────────────────────────┘
         ↓
    Click [Generate] on "Executive Report"
         ↓
    [Report Generation Modal]:
    - Date Range: [Last 7 Days]
    - Include: [✓ Alerts, ✓ KPIs, ✓ Risks]
    - Format: [PDF] [Excel] [Print]
    - [Generate]
         ↓
    Report renders
         ↓
    [Download] [Email] [Share]
```

---

## LAYOUT TEMPLATES

### Template 1: Dashboard (Executive)

```
┌─────────────────────────────────────────────────┐
│ EXECUTIVE DASHBOARD                             │
├─────────────────────────────────────────────────┤
│                                                 │
│  Portfolio Health        │  Critical Alerts     │
│  ┌─────────────────┐    │  ┌──────────────────┐│
│  │  Portfolio      │    │  │ 🏥 Health Down  ││
│  │  Score: 72     │    │  │ 🛡️  Safety (High)││
│  │  /100          │    │  │ 🛒 Late (3 POs)  ││
│  │  Good Status   │    │  │ ⚠️  Budget (2.1M)││
│  │                │    │  │ ⏰ Schedule Risk ││
│  │ [Trend: ↓ -5]  │    │  └──────────────────┘│
│  └─────────────────┘    │                      │
│                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────┐│
│  │ Projects     │ │ Safety       │ │ Budget  ││
│  │ At Risk: 3   │ │ Events (H): 2│ │ Overrun:││
│  │ Delayed: 12  │ │ Open NCRs: 1 │ │ $2.1M   ││
│  └──────────────┘ └──────────────┘ └─────────┘│
│                                                 │
│  ┌────────────────────────────────────────────┐│
│  │ [View Alerts] [Review At-Risk] [Escalate] ││
│  └────────────────────────────────────────────┘│
│                                                 │
└─────────────────────────────────────────────────┘
```

### Template 2: Operations (Module Cards)

```
┌─────────────────────────────────────────────────┐
│ OPERATIONS WORKSPACE — Manage Your Work         │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────┐ ┌──────────────────────┐│
│  │ 📁 PROJECTS      │ │ 📅 MEETINGS         ││
│  │                  │ │                      ││
│  │ 48 Active       │ │ 12 Upcoming        ││
│  │ 3 Delayed       │ │ 2 Today            ││
│  │ [Open Projects] │ │ [Schedule]          ││
│  └──────────────────┘ └──────────────────────┘│
│                                                 │
│  ┌──────────────────┐ ┌──────────────────────┐│
│  │ 🛒 PROCUREMENT   │ │ 📋 SITE REPORTS     ││
│  │                  │ │                      ││
│  │ 23 Open         │ │ 124 Reports        ││
│  │ 4 Late          │ │ Latest: Today      ││
│  │ [Review]        │ │ [View]              ││
│  └──────────────────┘ └──────────────────────┘│
│                                                 │
│  ┌──────────────────┐ ┌──────────────────────┐│
│  │ ❓ RFIs          │ │ 🔄 CHANGE ORDERS    ││
│  │                  │ │                      ││
│  │ 7 Pending       │ │ 3 In Progress      ││
│  │ 2 Urgent        │ │ 1 Denied           ││
│  │ [Action]        │ │ [Manage]            ││
│  └──────────────────┘ └──────────────────────┘│
│                                                 │
│  ┌──────────────────┐                          │
│  │ ⚖️  CLAIMS       │                          │
│  │                  │                          │
│  │ 2 Open          │                          │
│  │ 1 Resolved      │                          │
│  │ [Review]        │                          │
│  └──────────────────┘                          │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Template 3: Documents (Category Hub)

```
┌─────────────────────────────────────────────────┐
│ DOCUMENTS — Project Repository                  │
├─────────────────────────────────────────────────┤
│                                                 │
│ [Search...] [+Upload] [Filter by date]        │
│                                                 │
│ Document Categories:                            │
│                                                 │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐ │
│  │ 📋        │  │ ❓        │  │ 📝       │ │
│  │ Contracts │  │ RFIs      │  │ Minutes  │ │
│  │ 24 docs   │  │ 12 docs   │  │ 56 docs  │ │
│  │ [Browse]  │  │ [Browse]  │  │ [Browse] │ │
│  └────────────┘  └────────────┘  └──────────┘ │
│                                                 │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐ │
│  │ 📐        │  │ 🛒        │  │ 🛡️      │ │
│  │ Drawings  │  │ Purchase  │  │ Safety   │ │
│  │ 89 docs   │  │ 45 docs   │  │ 23 docs  │ │
│  │ [Browse]  │  │ [Browse]  │  │ [Browse] │ │
│  └────────────┘  └────────────┘  └──────────┘ │
│                                                 │
│  ┌────────────┐  ┌────────────┐                 │
│  │ ✅        │  │ 📊        │                 │
│  │ Quality   │  │ Other     │                 │
│  │ 15 docs   │  │ 8 docs    │                 │
│  │ [Browse]  │  │ [Browse]  │                 │
│  └────────────┘  └────────────┘                 │
│                                                 │
│ Recent Uploads:                                 │
│ ┌──────────────────────────────────────────┐  │
│ │ Tender_Phase3.pdf — 2h ago — John       │  │
│ │ Spec_v2.docx — 5h ago — Jane            │  │
│ │ Meeting_022424.pdf — 1d ago — Admin     │  │
│ └──────────────────────────────────────────┘  │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Template 4: Operations Module (Projects Example)

```
┌────────────────────────────────────────────────┐
│ PROJECTS — Manage Active Work                   │
├────────────────────────────────────────────────┤
│                                                │
│ [Search...] [Status ↓] [+New Project]        │
│                                                │
│ View: [List ◉] [Cards] [Kanban] [Timeline]  │
│                                                │
│ Quick Stats: 48 Total · 3 Delayed · 0 On Hold│
│                                                │
│ ┌──────────────────────────────────────────┐ │
│ │ Code    │ Project        │ Status  │ [>]│ │
│ │─────────┼────────────────┼─────────┼────│ │
│ │ P001    │ Downtown Plaza │ Active  │ ✓  │ │
│ │ P002    │ Airport Term   │ Delayed │ ⚠️  │ │
│ │ P003    │ Harbor Park    │ Active  │ ✓  │ │
│ │ P004    │ Tech Hub       │ On Hold │ ⏸️  │ │
│ └──────────────────────────────────────────┘ │
│                                                │
│ [Previous] 1 of 5 pages [Next]               │
│                                                │
└────────────────────────────────────────────────┘
```

### Template 5: Alert Management

```
┌────────────────────────────────────────────────┐
│ ALERTS — Active Issues                          │
├────────────────────────────────────────────────┤
│                                                │
│ Summary:                                        │
│ ┌────────┬────────┬───────┬────────┬────────┐ │
│ │ Health │ Safety │ Proc. │ Qual.  │ Sched. │ │
│ │ 3      │ 2      │ 1     │ 1      │ 2      │ │
│ └────────┴────────┴───────┴────────┴────────┘ │
│                                                │
│ [Filter by Category] [Sort: Newest]          │
│                                                │
│ CRITICAL (3):                                  │
│ ┌──────────────────────────────────────────┐ │
│ │ 🏥 Health Score Dropped                  │ │
│ │ "Portfolio health dropped 12% this week" │ │
│ │ Affects: 5 projects | 2h ago             │ │
│ │ [Acknowledge] [Assign] [Snooze] [Details]│ │
│ └──────────────────────────────────────────┘ │
│                                                │
│ ┌──────────────────────────────────────────┐ │
│ │ 🛡️  Safety Event — High Severity          │ │
│ │ "Near miss on scaffold inspection"       │ │
│ │ Project: Downtown Plaza | 1h ago         │ │
│ │ [Acknowledge] [Assign] [Details]         │ │
│ └──────────────────────────────────────────┘ │
│                                                │
│ HIGH (2): [+Show 2 High alerts]               │
│ MEDIUM (4): [+Show 4 Medium alerts]           │
│ LOW (5): [+Show 5 Low alerts]                 │
│                                                │
└────────────────────────────────────────────────┘
```

---

## INFORMATION HIERARCHY

### Level 1: What Needs Attention?
**Audience**: Executives, Team Leads  
**Pages**: Dashboard, Alerts  
**Data**: Exceptions, critical status, scores

### Level 2: What's My Work?
**Audience**: Project Teams  
**Pages**: Operations (workspace), Projects, Meetings, Procurement, Site Reports, Safety  
**Data**: Lists, statuses, recent activity

### Level 3: What's the Full Context?
**Audience**: Detailed work, documentation  
**Pages**: Project Detail, Meeting Detail, Document view  
**Data**: Full records, history, files

### Level 4: What Happened?
**Audience**: Reporting, analysis  
**Pages**: Reports, Audit Logs  
**Data**: Historical trends, compliance

### Level 5: How Do I Manage This?
**Audience**: Administrators, system config  
**Pages**: Administration  
**Data**: Users, roles, permissions, approvals

---

## SEARCH PATTERNS

### Scenario 1: Find a Document
```
User needs: "Find the Downtown Plaza tender document"

Search: Cmd+K → "Downtown tender"
Results:
├─ Downtown_Tender.pdf (Documents > Contracts) ← Click
├─ Tender_Downtown_v2.docx (Documents > Contracts)
└─ Meeting_Downtown_Tender_Discussion.pdf (Documents > Minutes)

Clicks first result → Lands on Documents > Contracts category
```

### Scenario 2: Find a Project
```
User needs: "Find Airport Terminal project"

Search: Cmd+K → "Airport"
Results:
├─ Airport Terminal (Projects > List) ← Click
├─ Airport_Terminal_Spec.pdf (Documents > Drawings)
└─ John Smith - Airport PM (People)

Clicks first result → Lands on Projects list, Airport Terminal highlighted
```

### Scenario 3: Find a Person
```
User needs: "Find John (PM)"

Search: Cmd+K → "John PM"
Results:
├─ John Smith - Project Manager (People) ← Click
├─ john@company.com (People)
└─ John's Meetings - Downtown Plaza Team (Meetings)

Clicks first result → Lands on People profile (future: could be modal)
```

---

## COLOR SCHEME

### Module Colors (Operations)

| Module | Icon Color | Background | Text |
|--------|-----------|-----------|------|
| Projects | #3B82F6 (Blue) | #EFF6FF | #1E40AF |
| Meetings | #A855F7 (Purple) | #FAF5FF | #6B21A8 |
| Procurement | #10B981 (Green) | #F0FDF4 | #065F46 |
| Site Reports | #F59E0B (Amber) | #FFFBEB | #92400E |
| RFIs | #06B6D4 (Cyan) | #ECFDF5 | #0E7490 |
| Change Orders | #EC4899 (Pink) | #FCE7F3 | #831843 |
| Claims | #EF4444 (Red) | #FEF2F2 | #7F1D1D |

### Status Colors (Universal)

| Status | Color | Hex |
|--------|-------|-----|
| Active / Good | Green | #10B981 |
| At Risk / Warning | Amber | #F59E0B |
| Delayed / Danger | Red | #EF4444 |
| On Hold / Neutral | Gray | #6B7280 |
| Critical | Red | #DC2626 |

---

## ACCESSIBILITY NOTES

### Keyboard Navigation
- [ ] All cards: Tab to focus, Enter/Space to activate
- [ ] All modals: ESC to close, Tab to navigate
- [ ] Search: Cmd+K or Ctrl+K to focus
- [ ] Alerts: Enter to expand, Space to acknowledge

### Screen Reader Support
- [ ] All icons have aria-labels
- [ ] All card counts announced as "48 projects"
- [ ] Status badges have semantic meaning
- [ ] Expandable content announced as "collapsed" / "expanded"

### Color Contrast
- [ ] Text meets WCAG AA (4.5:1)
- [ ] Module cards have icon + text (not color-only)
- [ ] Status badges have icons (not badge color only)

### Mobile Accessibility
- [ ] Touch targets minimum 44px
- [ ] No hover-required interactions
- [ ] Vertical scrolling only (no horizontal scroll)
- [ ] Font size minimum 16px on mobile

---

## RESPONSIVE GRID EXAMPLES

### Desktop (3 columns)

```
[Card 1] [Card 2] [Card 3]
[Card 4] [Card 5] [Card 6]
[Card 7]
```

### Tablet (2 columns)

```
[Card 1] [Card 2]
[Card 3] [Card 4]
[Card 5] [Card 6]
[Card 7]
```

### Mobile (1 column)

```
[Card 1]
[Card 2]
[Card 3]
[Card 4]
[Card 5]
[Card 6]
[Card 7]
```

---

## RTL LAYOUT (Arabic)

### LTR (English)

```
┌──────────────────────────────────┐
│ [Icon] Title [Count]             │
│ Subtitle →                        │
└──────────────────────────────────┘
```

### RTL (Arabic)

```
┌──────────────────────────────────┐
│             [Count] العنوان [Icon]│
│ ← الوصف                           │
└──────────────────────────────────┘
```

- Flexbox `flex-row-reverse` for header
- Text alignment: `text-right`
- Margins mirrored: `mr-4` → `ml-4`
- No hardcoded left/right (use start/end)

---

## SUMMARY

**V2 transforms AMAD from scattered dashboard to professional enterprise platform:**

- ✅ **Clear purpose** for each page
- ✅ **Reduced cognitive load** (5 main nav items)
- ✅ **Task-focused workflows** (Operations workspace)
- ✅ **Scannable layouts** (cards instead of tables)
- ✅ **Quick navigation** (global search)
- ✅ **Executive-focused** (Dashboard for C-suite)
- ✅ **Operator-focused** (Operations for teams)
- ✅ **System-managed** (Admin isolated)

**Result**: Feels like Fabric, Linear, or ServiceNow — professional enterprise SaaS.

**Next**: Implementation Phase (after stakeholder approval)
