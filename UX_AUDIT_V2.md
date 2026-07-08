# AMAD Construction AI Platform
## Version 2.0 - UX Information Architecture Audit

**Phase**: UX Design & Audit (No Implementation)  
**Date**: 2024  
**Principles**: Enterprise SaaS Design (Fabric, Notion, Linear, Atlassian, ServiceNow, Oracle)

---

## EXECUTIVE SUMMARY

The current AMAD platform suffers from **information architecture fragmentation**:
- Dashboard is too heavy with analytics → should be executive-only
- Operational pages are empty tabs → should be module cards
- Multiple similar pages spread across navigation → should be consolidated
- Projects buried under sub-sections → should be primary workspace
- No clear user journeys → should be role-based and task-focused
- Tables everywhere → should be cards, summaries, and quick actions

### Key Findings
1. **Too Much Information**: Dashboard, Reports, Alerts pages overwhelm with data
2. **Too Little Information**: Operations, Documents pages are empty shells
3. **No Clear Workspace**: Employees need a single operational hub
4. **Scattered Operations**: Projects, Meetings, Procurement, Site Reports, Safety, RFIs, Claims are in 6+ pages
5. **No Global Context**: Users can't quickly search or navigate across domains
6. **AI is Secondary**: AMAD AI is treated as utility, not central to platform mission

---

## PAGE-BY-PAGE AUDIT

---

### 1. DASHBOARD — Executive Overview

#### Current State
- **Components**: 
  - Portfolio health score card (5-element)
  - Active alerts widget (5 items)
  - Project status distribution (pie chart)
  - Project health bar chart
  - Monthly project completion chart
  - Procurement performance chart
  - Safety metrics cards (6 stat cards)
  - NCR summary cards
  - Risk summary cards
  - KPI trends

- **Issues**:
  - Too many charts (4+ visualizations)
  - Too many cards (10+ stat cards)
  - 3+ pages of scrolling
  - Executive can't see what needs attention in < 5 seconds
  - Mixes strategic + operational data
  - Not designed for C-suite quick decisions

#### Purpose
**What needs executive attention today?** - Dashboard should answer this in 3 seconds.

#### Analysis: KEEP / MOVE / REMOVE

**KEEP** (Executive Focus Only):
- Portfolio Health Score (large, prominent)
- Critical Alerts widget (5-10 top issues)
- Projects "At Risk" count
- Safety critical count
- Procurement blockers count
- Key metrics (1-2 most important per category)

**MOVE** (To Operational Pages):
- Detailed charts → Reports page
- Monthly trends → Analytics dashboard
- All project lists → Projects page
- All safety details → Safety page
- All procurement details → Procurement page

**REMOVE** (Too Much Information):
- Project status distribution pie chart
- Health distribution stacked bar chart
- Monthly completion line chart
- Procurement performance breakdown
- 80% of stat cards
- Any drill-down tables
- Recommendation columns (too wordy)

#### New Layout Design

```
┌─────────────────────────────────────────────────────┐
│  EXECUTIVE DASHBOARD — At a Glance                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Portfolio Health        Critical Issues (5)       │
│  ┌─────────────────┐     ┌──────────────────────┐  │
│  │   Portfolio     │     │ Safety: 1 High       │  │
│  │   Score: 72     │     │ Schedule: 2 At Risk  │  │
│  │   /100          │     │ Budget: 1 Overrun    │  │
│  │   Good Status   │     │ Quality: 1 NCR Open  │  │
│  │                 │     │ Procurement: 1 Late  │  │
│  │ [Trend: ↓ -5]   │     └──────────────────────┘  │
│  └─────────────────┘                                 │
│                                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────┐ │
│  │ Projects      │  │ Safety        │  │ Budget  │ │
│  │ 3 At Risk    │  │ 2 High Events │  │ $2.1M   │ │
│  │ 12 Delayed   │  │ 1 Open NCR    │  │ Overrun │ │
│  │ 48 Active    │  │               │  │         │ │
│  └───────────────┘  └───────────────┘  └─────────┘ │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ Quick Actions:                              │   │
│  │ [View Alerts] [Review At Risk] [Escalate]  │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Key Changes**:
- Single view, no scrolling (max 800px height)
- Portfolio health + Critical issues only
- 3 summary cards (Projects, Safety, Budget)
- Quick action buttons
- Color coding: Red (critical), Orange (at risk), Green (good)
- ONE glance = complete picture

#### User Journey
1. User logs in
2. Sees portfolio health immediately (green/yellow/red)
3. Spots 3-5 critical issues
4. Clicks issue type (Safety) → goes to Safety page
5. Or clicks "View All Alerts" → goes to Alerts page

#### Data Flow
```
Dashboard Input: Portfolio score + Top 5 alerts + At-risk count + Critical metrics
Dashboard Output: Executive decides: escalate? review? drill into operations?
```

---

### 2. OPERATIONS — Operational Workspace

#### Current State
- **Components**: 
  - 7 empty tabs (Projects, Meetings, Procurement, Site Reports, RFIs, Change Orders, Claims)
  - Placeholder content only
  - No module cards, no data

- **Issues**:
  - This is where employees spend 80% of their time
  - Currently completely empty
  - Tabs are not scannable

#### Purpose
**Operational Hub**: Employees manage all project work from one workspace.

#### Design: MODULE CARDS

Convert tabs into a **dashboard of module cards**. Each card shows:
- Icon
- Name
- Count of records
- Status summary (e.g., "3 open, 2 overdue")
- Quick action button

```
┌─────────────────────────────────────────────────────┐
│  OPERATIONS WORKSPACE                               │
│  "Today's Work At A Glance"                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ 📁 Projects  │  │ 📅 Meetings  │  │ 🛒 Proc  │ │
│  │ 48 Active    │  │ 12 Upcoming  │  │ 23 Open  │ │
│  │ 3 delayed    │  │ 2 today      │  │ 4 late   │ │
│  │ [Open]       │  │ [Schedule]   │  │ [Review] │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ 📋 Site      │  │ ❓ RFIs      │  │ 🔄 CO    │ │
│  │ 124 Reports  │  │ 7 Pending    │  │ 3 Approx │ │
│  │ Latest: Today│  │ 2 Urgent     │  │ 1 Denied │ │
│  │ [View]       │  │ [Action]     │  │ [Manage] │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                     │
│  ┌──────────────┐                                   │
│  │ ⚖️  Claims   │                                   │
│  │ 2 Open       │                                   │
│  │ 1 resolved   │                                   │
│  │ [Review]     │                                   │
│  └──────────────┘                                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

#### New Layout Specifications

**Cards Include**:
- **Icon** (lucide-react)
- **Name** (Projects, Meetings, Procurement, etc.)
- **Count** (large number: "48")
- **Status line** ("3 delayed, 2 urgent, 1 overdue" - max 40 chars)
- **Action button** ("Open", "Schedule", "Review", "Manage")
- **Hover effect**: Lift, shadow, scale

**Grid**:
- 3 columns on desktop
- 2 columns on tablet  
- 1 column on mobile
- Responsive gap: 16px

**Color Coding**:
- Blue: Neutral/Info (Meetings, RFIs)
- Green: Positive (Active Projects)
- Orange: Warning (Delays, Open items)
- Red: Critical (High items, Urgent)

#### User Journey
1. Login → Operations workspace (default landing for most users)
2. See all modules at a glance
3. Click card → specific module page loads
4. Example: Click "Procurement" card → Procurement page with 23 open records
5. Can drill-down or return to Operations to context-switch

#### Data Flow
```
Each card queries its endpoint:
- Projects: COUNT(active) + COUNT(delayed) + COUNT(critical)
- Meetings: COUNT(upcoming) + COUNT(today) + recently updated
- Procurement: COUNT(open) + COUNT(late) + latest PO
- Site Reports: COUNT(recent) + latest date
- RFIs: COUNT(pending) + COUNT(urgent)
- Change Orders: COUNT(pending) + COUNT(approved)
- Claims: COUNT(open) + COUNT(resolved)

Cache: 5 minutes (user can force-refresh)
```

#### Performance Note
Loading 7 endpoints in parallel → ~800ms to complete

---

### 3. PROJECTS — Execution Focus

#### Current State
- **Components**:
  - Search by name/code/client/city
  - Filter by status (dropdown)
  - Large table (Code, Name, City, Client, Status, Health)
  - Health bar chart (color-coded, percentage)
  - 100 projects displayed

- **Good**: 
  - Clean table layout
  - Good search + filter
  - Health score visualization is excellent

- **Issues**:
  - Table is too wide on desktop (7+ columns)
  - Missing bulk actions
  - No quick grouping by status
  - No project cards (alternative view)
  - No "today's work" section
  - Too detailed for scanning

#### Purpose
**Project Execution**: Users manage day-to-day project work (not strategic overview).

#### Keep
- Search functionality
- Status filter
- Health score bar (excellent visualization)
- Project table with: Code, Name, Status, Health

#### Move
- Executive summary → Dashboard
- Large charts → Reports
- Portfolio analytics → Reports
- Trend analysis → Reports

#### Remove
- Any chart showing all projects at once
- "Completed" status in main filter (archive view)
- Secondary columns (City if not in main workflow)

#### New Layout Design

```
┌─────────────────────────────────────────────────────┐
│ PROJECTS — Manage Active Work                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [Search projects...] [Filter: All Status] [+New]   │
│                                                     │
│ ┌────────────────────────────────────────────────┐ │
│ │ View: [List] [Cards] [Kanban] [Timeline]       │ │
│ └────────────────────────────────────────────────┘ │
│                                                     │
│ Quick Stats: 48 Total · 3 Delayed · 0 On Hold    │
│                                                     │
│ [TABLE - clean columns]                            │
│ Code  │ Project Name      │ Status   │ Health  [>] │
│ ─────┼──────────────────┼─────────┼─────────────── │
│ P001 │ Downtown Plaza    │ Active  │ ████░░ 82%  │
│ P002 │ Airport Terminal  │ Delayed │ ██░░░░ 35%  │
│ ...                                                 │
│                                                     │
│ [Pagination: 100 per page or Load More]           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**New Features**:
- **View toggle**: List (default), Cards, Kanban (by status), Timeline (by date)
- **Quick stats** above table
- **Bulk actions**: Select multiple → [Mark On Hold], [Escalate], [Archive]
- **Add button** to create new project

#### User Journey
1. User lands on Projects page
2. Sees all active projects (default filter: Active status)
3. Can switch view to Kanban (group by status) for quick drag-drop
4. Or switch to Timeline to see schedule conflicts
5. Search for specific project
6. Click row → Project detail page

---

### 4. PROCUREMENT — Consolidate & Simplify

#### Current State
- **Components**:
  - Two tabs: Purchase Requests + Purchase Orders
  - Search in each tab
  - Tables with 6+ columns each
  - Status badges
  - Note: ~3,000 PRs + ~2,550 POs (massive dataset)

- **Issues**:
  - Two separate tables feel disconnected
  - No summary of procurement health
  - No "what needs my attention" section
  - PR→PO flow is unclear
  - No supplier visibility
  - Late count badge is good, but buried

#### Purpose
**Procurement Operations**: Track requests through approval to delivery.

#### Keep
- PR and PO tables (separate is OK)
- Status tracking
- Late indicators
- Search functionality
- Request number/PO number as primary identifier

#### Move
- Supplier details → Suppliers page (not here)
- Budget analytics → Reports
- Spend trends → Reports

#### Remove
- Category column (add filter instead)
- Specification preview (click for full detail)
- "Display 100 most recent" limitation → use pagination

#### New Layout Design

```
┌─────────────────────────────────────────────────────┐
│ PROCUREMENT — Request to Delivery                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Procurement Health Summary:                         │
│ ┌─────────────┬─────────────┬──────────┬──────────┐ │
│ │ Open PRs: 12│ Under Review│ Approved │ Late POs │ │
│ │             │ 4           │ 8        │ 3        │ │
│ └─────────────┴─────────────┴──────────┴──────────┘ │
│                                                     │
│ [Search...] [Filter] [+New Request]               │
│                                                     │
│ ┌──────────────────────────────────────────────┐   │
│ │ PURCHASE REQUESTS (12 Open)                   │   │
│ │ Request # │ Category │ Status    │ Delivery [>] │
│ │ PR-2024-001 │ Lumber   │ Approved   │ 2024-02-15 │
│ │ PR-2024-002 │ Concrete │ Under Review │ URGENT   │
│ └──────────────────────────────────────────────┘   │
│                                                     │
│ ┌──────────────────────────────────────────────┐   │
│ │ PURCHASE ORDERS (23 Active)                   │   │
│ │ PO # │ Supplier     │ Status    │ Deliver [>] │   │
│ │ PO-0445 │ Supplier A   │ Delivered  │ 2024-02-10 │
│ │ PO-0446 │ Supplier B   │ Delayed    │ ⚠️ LATE   │
│ └──────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**New Features**:
- **Procurement health summary** (4 key counts)
- **Dual tables** with clear labels
- **Color-coded status badges**
- **Delivery date warnings** (highlighted red if late)
- **Filter by category, status, supplier**

---

### 5. SITE REPORTS — Streamline Project Selection

#### Current State
- **Components**:
  - Project dropdown selector (required)
  - On selection, shows table of reports for that project
  - Report Date, Weather, Summary columns
  - Weather badges (color-coded)
  - ~50 reports per project

- **Good**:
  - Clean table
  - Project context is clear
  - Weather badges are useful

- **Issues**:
  - Project selector is clunky (dropdown in header)
  - Empty state says "Select project" (no suggestion)
  - No recent/latest reports highlighted
  - No cross-project reporting
  - No report templates or quick entry

#### Purpose
**Site Intelligence**: Daily activity tracking and weather documentation.

#### Keep
- Report date + weather + summary
- Project selector
- Recent reports first (sorted by date DESC)
- Weather badges

#### Move
- Multi-project trend analytics → Reports page
- Weather historical analysis → Reports

#### Remove
- Project must load before showing reports (show recent by default)

#### New Layout Design

```
┌─────────────────────────────────────────────────────┐
│ SITE REPORTS — Daily Activity Log                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [Select Project] [Filter by date range] [+New]    │
│                                                     │
│ Recent Reports:                                     │
│                                                     │
│ ┌───────────────────────────────────────────────┐  │
│ │ 2024-02-15 (Today) — Clear                    │  │
│ │ "Concrete pour completed on Level 3. Weather │  │
│ │  clear. Crew completed 2,000 SqM. Next: ..."  │  │
│ │ [View] [Edit]                                  │  │
│ └───────────────────────────────────────────────┘  │
│                                                     │
│ ┌───────────────────────────────────────────────┐  │
│ │ 2024-02-14 — Light Rain                       │  │
│ │ "Foundation reinforcement ongoing. Light rain │  │
│ │  in afternoon. Work paused 2-4pm. ..."        │  │
│ │ [View] [Edit]                                  │  │
│ └───────────────────────────────────────────────┘  │
│                                                     │
│ [Pagination or infinite scroll]                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**New Features**:
- **Card-based layout** instead of table (summary is readable)
- **Date highlighted** (Today, Yesterday, etc.)
- **Weather badge** inline
- **Expandable summaries** with [View Full] button
- **+New Report** button for quick entry
- **Date range filter** (last 7 days default)

---

### 6. MEETINGS — Project-Scoped with Card View

#### Current State
- **Components**:
  - Project selector (same pattern as Site Reports)
  - Two tabs: Meetings + Decisions
  - Tables for each
  - Meeting Type badges (Weekly, Technical, Safety, Commercial)
  - Decisions table with decision text

- **Issues**:
  - Same project selector clunkiness
  - Decisions tab is too detailed (Decision Text in table is long)
  - No meeting templates
  - No decision tracking integration
  - Can't see meeting schedule (calendar view missing)

#### Purpose
**Meeting Management**: Track meetings, decisions, and action items.

#### Keep
- Meeting date + type + decisions
- Decision tracking
- Meeting list (with date sorting)

#### Move
- Decision trends → Reports
- Meeting analytics → Reports
- Multi-project meeting schedule → Calendar view (NEW)

#### Remove
- Decision detailed text from table (show summary, click for full)
- Meeting type choices (standardize to: Kickoff, Daily, Weekly, Safety, Review)

#### New Layout Design

```
┌─────────────────────────────────────────────────────┐
│ MEETINGS — Coordination & Decisions                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [Select Project] [View: List / Calendar] [+New]   │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Feb 15, 2024 (Today) — Weekly Meeting          │ │
│ │ 10:00 AM - 11:00 AM                            │ │
│ │ Owner: Project Manager - John Smith            │ │
│ │ Attendees: 8 people                            │ │
│ │ Decisions: 3 made, 0 pending                   │ │
│ │ [View Details]                                  │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Feb 10, 2024 — Safety Meeting                  │ │
│ │ 09:00 AM - 09:30 AM                            │ │
│ │ Owner: Safety Officer - Jane Doe               │ │
│ │ Attendees: 12 people                           │ │
│ │ Decisions: 2 made, 1 pending                   │ │
│ │ [View Details]                                  │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**New Features**:
- **Card-based meetings** (date, time, type, attendees, decision count)
- **Calendar view toggle** (see meeting schedule visually)
- **Decision counter** on each meeting
- **+New Meeting** button
- **Inline decision preview** (click to expand decisions)

---

### 7. SAFETY — Combine Events + NCRs with Risk View

#### Current State
- **Components**:
  - Project selector
  - Two tabs: Safety Events + NCRs
  - Tables for each
  - Severity badges (High, Medium, Low)
  - Alert banners for critical counts

- **Issues**:
  - Two separate tabs feels disconnected
  - No unified safety dashboard
  - No trend visibility
  - Event severity != NCR status (confusing)
  - No safety score or risk assessment

#### Purpose
**Safety & Quality Management**: Track incidents and corrective actions.

#### Keep
- Safety events (date, severity, description)
- NCRs (status, description, corrective action)
- Severity/Status badges
- Project scoping

#### Move
- Safety trends → Reports
- Safety analytics → Reports
- Incident history → Archive

#### Remove
- Redundant fields (severity/status shown twice)
- Detailed descriptions from table (summary only, click for full)

#### New Layout Design

```
┌─────────────────────────────────────────────────────┐
│ SAFETY & QUALITY — Incidents & Corrective Actions   │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [Select Project]                                    │
│                                                     │
│ Safety Summary:                                     │
│ ┌────────────┬────────────┬────────────┬─────────┐ │
│ │ High Events│ Open NCRs  │ At Risk    │ Score   │ │
│ │ 2          │ 5          │ 3          │ 68/100  │ │
│ └────────────┴────────────┴────────────┴─────────┘ │
│                                                     │
│ RECENT INCIDENTS (All statuses):                    │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 2024-02-15 — Near Miss — High                  │ │
│ │ "Improper scaffold setup detected during..."    │ │
│ │ NCR: NCR-2024-142 — Open — [View]              │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 2024-02-10 — Slip & Fall — Medium              │ │
│ │ "Worker slipped on wet stairs..."                │ │
│ │ NCR: NCR-2024-139 — In Progress — [View]        │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**New Features**:
- **Safety score** (visual indicator of project safety status)
- **Combined incidents + NCRs** (one unified view)
- **Card layout** (readable, with linked NCR reference)
- **Status badge** (High/Medium, Open/In Progress, etc.)
- **Filter by severity or status**

---

### 8. SUPPLIERS — Master Data Management

#### Current State
- **Components**:
  - Search by name, city, category
  - Filter by category dropdown
  - Filter by status dropdown
  - Large table (Supplier Name, City, Category, Status)
  - 100+ suppliers

- **Good**:
  - Clean search + filters
  - Good categorization
  - Status badges

- **Issues**:
  - No supplier performance metrics
  - No active/inactive toggle
  - No supplier cards (alternative view)
  - No "top suppliers" or "at risk" indicators
  - Contact info hidden (need quick access)

#### Purpose
**Supplier Management**: Master data and vendor relationships.

#### Keep
- Supplier list with name, city, category, status
- Search + filter functionality
- Status badges

#### Move
- Supplier performance trends → Reports
- Spend by supplier → Reports

#### Remove
- Redundant status filter if using tabs (Active/Inactive)

#### New Layout Design

```
┌─────────────────────────────────────────────────────┐
│ SUPPLIERS — Vendor Management                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [Search suppliers...] [Category] [Status] [+Add]  │
│                                                     │
│ ┌──────────────────────────────────────────────┐   │
│ │ View: [List] [Cards] [Map] [Performance]    │   │
│ └──────────────────────────────────────────────┘   │
│                                                     │
│ ┌────────────────────────────────────────────────┐ │
│ │ Supplier Name    │ Category │ Status    │ POs │ │
│ │ Supplier A       │ Concrete │ Active    │ 45  │ │
│ │ Supplier B       │ Steel    │ Active    │ 32  │ │
│ │ Supplier C       │ Lumber   │ Inactive  │ 12  │ │
│ └────────────────────────────────────────────────┘ │
│                                                     │
│ Cards View (Alternative):                          │
│                                                     │
│ ┌─────────────────┐  ┌─────────────────┐           │
│ │ Supplier A      │  │ Supplier B      │           │
│ │ Concrete        │  │ Steel           │           │
│ │ Active ✓        │  │ Active ✓        │           │
│ │ 45 POs          │  │ 32 POs          │           │
│ │ ★★★★☆ 4.2      │  │ ★★★☆☆ 3.8      │           │
│ │ [View Contact]  │  │ [View Contact]  │           │
│ └─────────────────┘  └─────────────────┘           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**New Features**:
- **View toggle**: List, Cards, Map (location), Performance
- **Contact quick view** (phone, email in tooltip or modal)
- **Performance rating** (5-star or numeric)
- **PO count** (frequency indicator)
- **Active/Inactive tabs** at top

---

### 9. REPORTS — Report Generation Only

#### Current State
- **Components**:
  - Executive Weekly Report (very complex, 50+ lines of sections)
  - Sections: Alerts, Summary, KPIs, Blockers, Risks, Recommendations, Quality, Sources

- **Issues**:
  - Too long and detailed
  - Mixes operational + strategic
  - Not clearly scannable
  - No report builder/template selection
  - No export options visible

#### Purpose
**Report Generation**: Create reports for executives, stakeholders, or record-keeping.

#### Keep
- Report generation functionality
- Alert summaries
- KPI sections
- Recommendations

#### Move
- Operational data → operational pages
- Detailed analytics → respective pages
- Live dashboards → Dashboard

#### Remove
- 70% of the detail (make reports summaries, not encyclopedias)
- Recommendation text paragraphs (use bullet points)
- Redundant sections

#### New Layout Design

```
┌─────────────────────────────────────────────────────┐
│ REPORTS — Generate & Export                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Select Report Type:                                 │
│                                                     │
│ ┌──────────────────┐  ┌──────────────────┐         │
│ │ 📄 Executive     │  │ 📊 Weekly Update │         │
│ │ Summary Report   │  │ Key Metrics &    │         │
│ │ For leadership   │  │ Alerts           │         │
│ │ [Generate]       │  │ [Generate]       │         │
│ └──────────────────┘  └──────────────────┘         │
│                                                     │
│ ┌──────────────────┐  ┌──────────────────┐         │
│ │ 📈 Portfolio     │  │ 📋 Custom        │         │
│ │ Analysis Report  │  │ Build Your Own   │         │
│ │ All metrics      │  │ Report           │         │
│ │ [Generate]       │  │ [Builder]        │         │
│ └──────────────────┘  └──────────────────┘         │
│                                                     │
│ ┌──────────────────┐  ┌──────────────────┐         │
│ │ 🎯 AI Analysis   │  │ 📑 Compliance    │         │
│ │ (Coming Soon)    │  │ Report           │         │
│ │ AI Insights      │  │ Safety, Quality  │         │
│ │ [Coming Soon]    │  │ [Generate]       │         │
│ └──────────────────┘  └──────────────────┘         │
│                                                     │
│ ─────────────────────────────────────────────────  │
│                                                     │
│ Recent Reports:                                     │
│ ┌──────────────────────────────────────────────┐  │
│ │ Executive Report — 2024-02-15 — [View] [PDF]│  │
│ │ Weekly Update — 2024-02-14 — [View] [PDF]   │  │
│ │ Portfolio Analysis — 2024-02-10 — [View]    │  │
│ └──────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**New Features**:
- **Report templates** as cards (not forms)
- **Generate button** on each template
- **Quick export** to PDF/Excel
- **Recent reports** list
- **Custom report builder** for power users
- **Schedule reports** (email weekly, etc.)

---

### 10. ALERTS — Exception Management Dashboard

#### Current State
- **Components**:
  - 5 summary cards (Health, Safety, Procurement, Quality, Schedule)
  - Alert list with:
    - Category icon
    - Title + severity badge
    - Description (1-2 lines)
    - Expandable details
  - Filter by category
  - Filter by severity

- **Good**:
  - Summary cards are useful
  - Expandable alerts are scannable
  - Category icons help scanning
  - Severity badges

- **Issues**:
  - No sorting options
  - No "mark as read" or "snooze" functionality
  - No grouping by category
  - No alert rules (configurable notifications)
  - No "assign to" capability

#### Purpose
**Exception Management**: See what needs attention, take action.

#### Keep
- Summary cards (Health, Safety, Procurement, Quality, Schedule)
- Alert list with expandable details
- Category + severity filtering
- Severity badges

#### Move
- Nothing really to move

#### Remove
- Excessive detail in alert descriptions (keep to 50 chars)
- "Alert ID" if not useful

#### New Layout Design

```
┌─────────────────────────────────────────────────────┐
│ ALERTS — Active Issues                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Summary:                                            │
│ ┌────────┬────────┬─────────┬────────┬──────────┐  │
│ │ Health │ Safety │ Procure │ Quality│ Schedule │  │
│ │ 3      │ 2      │ 1       │ 1      │ 2        │  │
│ └────────┴────────┴─────────┴────────┴──────────┘  │
│                                                     │
│ [Filter by Category] [Sort: Newest/Severity]      │
│ [View: List / Groups]                              │
│                                                     │
│ CRITICAL (3):                                       │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 🏥 High Severity — Health Score Dropped         │ │
│ │ "Portfolio health dropped 12% this week"         │ │
│ │ Affects: 5 projects  Updated: 2h ago           │ │
│ │ [Acknowledge] [Assign] [Snooze] [Details]      │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ HIGH (2):                                           │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 🛡️  High Severity — Safety Event Reported       │ │
│ │ "Near miss during scaffold inspection"           │ │
│ │ Project: Downtown Plaza  Updated: 1h ago       │ │
│ │ [Acknowledge] [Assign] [Details]                │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ MEDIUM (4):                                         │
│ [Collapsed by default]                              │
│ [Show 4 Medium alerts]                              │
│                                                     │
│ LOW (5):                                            │
│ [Collapsed by default]                              │
│ [Show 5 Low alerts]                                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**New Features**:
- **Group by severity** (Critical/High expanded, Medium/Low collapsed)
- **Acknowledge alert** (mark as "seen")
- **Snooze alert** (hide for N hours)
- **Assign to team member**
- **View details** modal
- **Auto-resolve** (when underlying issue fixed)
- **Alert history** (past alerts)

---

### 11. ADMINISTRATION — System & People Management

#### Current State
- **Components**:
  - Admin Users page: User list, roles, status, action buttons
  - Admin Organization page: Organization cards, edit/create
  - Both are separate pages

- **Issues**:
  - No unified admin dashboard
  - No audit logs visible
  - No permission management UI
  - No approval workflows visible
  - Too scattered

#### Purpose
**System Administration**: Manage system configuration, users, organizations, permissions, audit trails.

#### Keep
- User management (create, edit, delete, roles)
- Organization management
- Role assignments

#### Move
- Audit logs → new "Audit" page under Admin
- Approval workflows → new "Approvals" page
- System settings → new "Settings" page

#### Remove
- Any operational data from admin

#### New Layout Design

```
┌─────────────────────────────────────────────────────┐
│ ADMINISTRATION — System Management                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ┌────────────┬────────────┬──────────┬────────────┐ │
│ │ Employees  │ Org        │ Roles &  │ Audit      │ │
│ │ (234)      │ (2)        │ Perms    │ Logs       │ │
│ │ [Manage]   │ [Manage]   │ [Config] │ [View]     │ │
│ └────────────┴────────────┴──────────┴────────────┘ │
│                                                     │
│ ─────────────────────────────────────────────────── │
│                                                     │
│ EMPLOYEES (Tab View):                               │
│                                                     │
│ [Search...] [Filter: All / Roles] [+Add Employee] │
│                                                     │
│ ┌──────────────────────────────────────────────┐   │
│ │ Email             │ Role        │ Status     │   │
│ │ john@mail.com     │ Admin       │ Active     │   │
│ │ jane@mail.com     │ Executive   │ Active     │   │
│ │ bob@mail.com      │ PM          │ Inactive   │   │
│ └──────────────────────────────────────────────┘   │
│                                                     │
│ ─────────────────────────────────────────────────── │
│                                                     │
│ AUDIT LOG (Scrollable):                             │
│                                                     │
│ 2024-02-15 14:30 — john.admin — Edited User bob   │
│                    Changed Role: PM → Site Engineer │
│                                                     │
│ 2024-02-15 12:00 — jane.exec — Approved PO-0445   │
│                    Amount: $15,000                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**New Features**:
- **Admin dashboard** with tabs
- **Unified employee management**
- **Role configuration** UI
- **Audit log viewer** (read-only)
- **Approval queue** (pending approvals)
- **System settings** (company-wide config)

---

### 12. DOCUMENTS — Document Hub

#### Current State
- **Components**:
  - Search bar
  - Upload button
  - Empty state

- **Issues**:
  - Completely empty
  - No document organization
  - No categories
  - No filtering

#### Purpose
**Document Repository**: Centralized project document storage and retrieval.

#### Design

```
┌─────────────────────────────────────────────────────┐
│ DOCUMENTS — Project Repository                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [Search documents...] [+Upload] [Filter]          │
│                                                     │
│ Document Categories:                                │
│                                                     │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│ │ 📋 Contracts│  │ ❓ RFIs     │  │ 📝 Minutes  │ │
│ │ 24 docs     │  │ 12 docs     │  │ 56 docs     │ │
│ │ [Browse]    │  │ [Browse]    │  │ [Browse]    │ │
│ └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                     │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│ │ 📐 Drawings │  │ 🛒 Purchase │  │ 🛡️ Safety   │ │
│ │ 89 docs     │  │ 45 docs     │  │ 23 docs     │ │
│ │ [Browse]    │  │ [Browse]    │  │ [Browse]    │ │
│ └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                     │
│ ┌─────────────┐  ┌─────────────┐                   │
│ │ ✅ Quality  │  │ 📊 Other    │                   │
│ │ 15 docs     │  │ 8 docs      │                   │
│ │ [Browse]    │  │ [Browse]    │                   │
│ └─────────────┘  └─────────────┘                   │
│                                                     │
│ ─────────────────────────────────────────────────── │
│                                                     │
│ Recent Documents:                                   │
│ ┌──────────────────────────────────────────────┐   │
│ │ Tender_Phase3.pdf — Feb 15 — John Smith     │   │
│ │ Specification_v2.docx — Feb 14 — Jane Doe   │   │
│ │ Meeting_Minutes_022424.pdf — Feb 14 — Admin │   │
│ └──────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Categories**:
- Contracts
- RFIs
- Meeting Minutes
- Drawings
- Purchase Files (POs, PRs)
- Safety Documents
- Quality Documents
- Other

**Features**:
- Upload from computer or cloud
- Drag-and-drop upload
- Category auto-detection
- Full-text search
- Recent uploads list
- Bulk download

---

### 13. OPERATIONS WORKSPACE — Module Cards (Already Described)

See Section 2 above.

---

### 14. AMAD AI — AI Workspace

#### Current State
- **Components**:
  - AI Home with 5 premium cards
  - Workspace view for each card (placeholder)
  - Glassmorphism floating button

- **Good**:
  - Professional card design
  - Color-coded cards
  - Clear icons

- **Issues**:
  - No actual AI functionality yet (placeholders only)
  - Workspace views are empty
  - No chat interface
  - No session history
  - No workflow templates

#### Purpose
**Enterprise AI Assistant**: Not a chatbot, but an AI workspace for construction intelligence.

#### Keep
- Card-based home screen
- Floating button access
- Color-coded AI modules
- Workspace isolation

#### Move
- Chat to card workspaces (not global)
- AI settings → Administration

#### Remove
- Generic "ask AI" unless scoped to a domain

#### Redesigned AMAD AI Workspace

```
┌─────────────────────────────────────────────────────┐
│ AMAD AI — Enterprise Intelligence                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Good afternoon! How can AMAD AI help?              │
│                                                     │
│ Recent Sessions (Today):                            │
│ ┌────────────────────────────────────────────────┐ │
│ │ Meeting Analysis — Downtown Plaza Team Meeting │ │
│ │ Completed 30 min ago — [Resume]                │ │
│ └────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────┐ │
│ │ Site Report Summary — Airport Terminal         │ │
│ │ Completed 2h ago — [Resume]                    │ │
│ └────────────────────────────────────────────────┘ │
│                                                     │
│ Pinned Workflows:                                   │
│ ┌──────────────┐  ┌──────────────┐  ┌────────────┐│
│ │ 🎯 Weekly    │  │ 📊 Risk      │  │ ⚠️  Alert  ││
│ │ Brief        │  │ Analysis     │  │ Response   ││
│ │ [Start]      │  │ [Start]      │  │ [Start]    ││
│ └──────────────┘  └──────────────┘  └────────────┘│
│                                                     │
│ Quick Actions:                                      │
│ [Summarize Latest Meeting]                          │
│ [Analyze Site Report]                              │
│ [Review At-Risk Projects]                           │
│ [Check Safety Incidents]                            │
│                                                     │
│ ─────────────────────────────────────────────────── │
│                                                     │
│ All Intelligence Modules:                           │
│                                                     │
│ ┌────────────────┐  ┌────────────────┐            │
│ │ 👥 Meeting     │  │ 📋 Site        │            │
│ │ Intelligence   │  │ Intelligence   │            │
│ │ [Access]       │  │ [Access]       │            │
│ └────────────────┘  └────────────────┘            │
│                                                     │
│ ┌────────────────┐  ┌────────────────┐            │
│ │ 🛒 Procurement │  │ 🧠 Enterprise  │            │
│ │ Intelligence   │  │ Memory         │            │
│ │ [Access]       │  │ [Access]       │            │
│ └────────────────┘  └────────────────┘            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Not a Chatbot**:
- Meeting Intelligence: Structured analysis, not chat
- Site Intelligence: Report summarization, not chat
- Procurement Intelligence: Policy checking, not chat
- Enterprise Memory: Knowledge base search, not chat
- Ask Construction AI: Guided Q&A, not free-form chat

---

### 15. GLOBAL SEARCH — Design

#### Current State
- **Missing**: No global search exists

#### Purpose
**Quick Navigation**: Find anything across the platform in 2 seconds.

#### Design

```
Search Box (Top Navigation Bar):
┌──────────────────────────────────────────────┐
│ 🔍 Search across projects, docs, people...  │
└──────────────────────────────────────────────┘

On focus, shows:
- Recent searches
- Quick suggestions (trending)
- Search scope (All / Projects / Documents / People / etc.)

Typing "downtown":
- Projects: Downtown Plaza (P001)
- Documents: Downtown_Spec.pdf, Tender_Downtown.docx
- Meetings: Downtown Plaza Team Meeting — Feb 15
- People: John (Downtown PM)

Results shown with:
- Type icon
- Title
- Metadata (status, date, owner)
- [Open] button
```

**Search Scope**:
- Projects (name, code, client)
- Documents (name, content preview)
- Meetings (title, attendees, date)
- Procurement (request #, supplier)
- People (name, email, role)
- Site Reports (project, date)
- Safety Events (incident type, project)
- Organizations (name)
- Memory (knowledge base search)

**Keyboard Shortcut**: `Cmd+K` or `Ctrl+K` to focus search

---

## V2 INFORMATION ARCHITECTURE

### Navigation Hierarchy

```
┌─ MAIN NAVIGATION (5 items) ─────────────────────────┐
│                                                     │
│  1. DASHBOARD — Executive Overview (home)           │
│     └─ Alerts → Full alert management              │
│                                                     │
│  2. OPERATIONS — Operational Workspace             │
│     ├─ Projects → Project list & detail            │
│     ├─ Meetings → Meeting management               │
│     ├─ Procurement → PR/PO management              │
│     ├─ Site Reports → Daily reports               │
│     ├─ RFIs → Request management                   │
│     ├─ Change Orders → CO tracking                │
│     └─ Claims → Claims management                  │
│                                                     │
│  3. DOCUMENTS — Repository Hub                     │
│     ├─ Contracts                                   │
│     ├─ RFIs                                        │
│     ├─ Meeting Minutes                             │
│     ├─ Drawings                                    │
│     ├─ Purchase Files                              │
│     ├─ Safety Docs                                 │
│     ├─ Quality Docs                                │
│     └─ Other                                       │
│                                                    │
│  4. REPORTS — Report Generation                    │
│     ├─ Executive Report                            │
│     ├─ Weekly Update                               │
│     ├─ Portfolio Analysis                          │
│     ├─ Custom Report Builder                       │
│     └─ Scheduled Reports                           │
│                                                     │
│  5. ADMINISTRATION — System Management              │
│     ├─ Employees                                   │
│     ├─ Organizations                               │
│     ├─ Roles & Permissions                         │
│     ├─ Approvals (workflow queue)                  │
│     ├─ Audit Logs                                  │
│     └─ Settings                                    │
│                                                     │
│  [+] AMAD AI — Floating Button (side drawer)      │
│      ├─ Meeting Intelligence                       │
│      ├─ Site Intelligence                          │
│      ├─ Procurement Intelligence                   │
│      ├─ Enterprise Memory                          │
│      └─ Ask Construction AI                        │
│                                                     │
└─ GLOBAL SEARCH (top bar, always visible) ──────────┘
```

### User Journeys

#### Journey 1: Executive Morning Briefing
```
1. Login
2. See Dashboard (portfolio health + top 5 critical alerts)
3. See "Projects At Risk" → Click → Goes to Projects, filtered to "Delayed"
4. See "Safety High" → Click → Goes to Safety, filtered to "High"
5. Quickly assess → No escalation needed
6. Exit

Time: 3-5 minutes
```

#### Journey 2: Project Manager Daily Work
```
1. Login
2. See Operations workspace (all modules at a glance)
3. Click "Projects" card → Project list loads
4. Search for "Downtown Plaza"
5. Click project → Project detail (not fully scoped yet)
6. Check Status: Active ✓
7. Go back to Operations
8. Click "Meetings" card → Meeting list
9. See meeting scheduled for today
10. Click meeting → Meeting details
11. Review notes from last meeting
12. Return to Operations to context-switch
13. Click "Procurement" card
14. Review pending PRs
15. Approve one PR
16. Go back to Operations
17. Click on AMAD AI (bottom-right button)
18. Select "Meeting Intelligence"
19. Request: "Summarize today's meeting" (data will feed from meeting)
20. Read summary
21. Close AI drawer

Time: 20-30 minutes (full work session)
```

#### Journey 3: Finding a Document
```
1. Need to find a specific document (TBD)
2. Use Global Search (Cmd+K)
3. Type "Tender Downtown"
4. See: "Tender_Downtown.pdf" → Documents: Contracts
5. Click result
6. Go to Documents > Contracts
7. Document loads in viewer or download
8. Done

Time: 30 seconds
```

#### Journey 4: Admin Managing Users
```
1. Login as Admin
2. Go to Administration
3. Click "Employees" tab
4. See user list
5. Search for "Jane"
6. Find Jane Doe
7. Click [Edit]
8. Change role from "Site Engineer" → "Project Manager"
9. Click [Save]
10. See audit log entry recorded
11. Done

Time: 2-3 minutes
```

---

## KEY PRINCIPLES IMPLEMENTED

### 1. **Executive Dashboard — Distraction-Free**
- Only what executives need: Portfolio score + Top 5 issues + Quick stats
- No scrolling
- Color-coded severity
- 5-second rule: Can executive understand status in 5 seconds? YES

### 2. **Operations Workspace — Single Entry Point**
- Employees see all their work in one place (module cards)
- No searching through 6 different pages
- Summary cards show status without clicking
- Reduces cognitive load

### 3. **Module Consolidation**
- Projects, Meetings, Procurement, etc. not in sidebar → in Operations
- Cleaner navigation
- Logical grouping
- Easy to find related work

### 4. **Document Hub — Organized Categorization**
- 8 categories (not a flat list of 1000 documents)
- Scannable
- Easy to drill into specific category
- Recent uploads highlighted

### 5. **Reports — Not Operational**
- Reports page is ONLY for generating/exporting
- No live dashboards
- No drill-down tables
- Keeps Reports isolated from Operations

### 6. **Administration — Separated from Operations**
- No operational data in Admin
- System config only
- Clear boundary between "managing my work" and "managing the system"

### 7. **Alerts — Exception Management**
- Not a buried widget on Dashboard
- Dedicated Alerts page
- Grouped by severity
- Actionable (acknowledge, assign, snooze)

### 8. **Global Search — Quick Navigation**
- Keyboard shortcut (Cmd+K)
- Searches all domains
- Result preview
- Direct navigation

### 9. **AI Workspace — Not a Chatbot**
- Structured workflows (Meeting Intelligence, Site Intelligence, etc.)
- Each AI module has a specific purpose
- Not free-form chat
- Accessible from floating button or AI section

### 10. **Card-Based UI — Scannable**
- Site Reports: Cards instead of table
- Meetings: Cards instead of table
- Documents: Category cards + recent list
- Operations: Module cards
- Easier to scan, better UX

---

## IMPLEMENTATION PHASES

### Phase 1: Dashboard (Simplify)
- Remove 80% of content
- Keep: Portfolio score + 5 critical alerts + 3 summary cards
- Keep: Quick action buttons

### Phase 2: Operations Workspace (Enhance)
- Convert tabs to module cards
- Add counts and status
- Link to specific pages

### Phase 3: Operational Pages (Redesign)
- Projects: Add view toggles (List/Cards/Kanban/Timeline)
- Procurement: Add summary cards
- Site Reports: Convert to card layout
- Meetings: Convert to card layout + calendar view
- Safety: Add score card, combine events + NCRs

### Phase 4: Documents (Build)
- Create category cards
- Upload functionality
- Search
- Recent uploads

### Phase 5: Reports (Simplify)
- Remove operational details
- Focus on generation
- Add export

### Phase 6: Administration (Consolidate)
- Tabs: Employees, Organizations, Roles, Approvals, Audit, Settings
- Audit log viewer
- Approval workflow queue

### Phase 7: Global Search (Implement)
- Search bar in top navigation
- Scope selector (All / Projects / Documents / People / etc.)
- Results formatting
- Keyboard shortcut

### Phase 8: AI Workspace (Finalize)
- Session history
- Pinned workflows
- Quick actions
- Module separation

---

## SUMMARY: BEFORE & AFTER

| Aspect | Before | After |
|--------|--------|-------|
| Navigation | Cluttered, many items | Clean, 5 main + Operations modules |
| Dashboard | Overwhelming (10 cards + 4 charts) | Executive-only: Portfolio + 5 alerts |
| Operations | Scattered across 6+ pages | Unified workspace with module cards |
| Modules | Tables everywhere | Mix of tables, cards, and card layouts |
| Documents | Empty placeholder | Organized hub with 8 categories |
| Reports | Operational data embedded | Separate page for generation only |
| Alerts | Buried in Dashboard | Dedicated Alerts page with grouping |
| Admin | Mixed operational/system | Separate, system-only, with audit log |
| Search | Missing | Global search with Cmd+K |
| AI | Card drawer with placeholders | AI workspace with 5 modules + sessions |
| User Journey | Complex, multi-page hops | Simple, context-aware, task-focused |

---

## TECHNICAL NOTES

### No Backend Changes Required
All changes are **frontend layout only**. No API changes needed.

### No Database Changes Required
Using existing data structures.

### No AI Workflow Implementation
All AI components remain placeholders (ready for later implementation).

### Responsive Design Maintained
All new layouts use Tailwind CSS breakpoints:
- Mobile (sm): 1 column cards
- Tablet (md): 2 column cards
- Desktop (lg/xl): 3+ column cards

### Internationalization Maintained
All new strings added to i18n.ts (English + Arabic)

### RTL Support Maintained
All layouts work in RTL mode (Arabic)

---

## CONCLUSION

This V2 information architecture transforms AMAD from a scattered dashboard into a **professional enterprise platform** where:
- **Executives** see what needs attention (Dashboard)
- **Operators** see their daily work (Operations)
- **Administrators** manage the system (Administration)
- **Everyone** finds anything globally (Search)
- **AI** provides focused intelligence (AMAD AI modules)

The platform feels like **Fabric, Linear, or Atlassian** — professional, clear, purposeful.

Next Phase: **Implementation** (when approved)
