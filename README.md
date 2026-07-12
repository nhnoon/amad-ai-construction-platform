# AMAD — AI-Powered Construction Operations Intelligence Platform

![Status](https://img.shields.io/badge/status-active--development-blue)
![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20PostgreSQL-009688)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20TypeScript-3178C6)
![Language](https://img.shields.io/badge/i18n-Arabic%20%2F%20English-informational)
![License](https://img.shields.io/badge/license-proprietary-lightgrey)

---

## 1. Executive Overview

AMAD centralizes construction operations data — projects, procurement, safety, quality, meetings, and site activity — into a single, RBAC-scoped intelligence layer. Instead of leaving that data siloed across spreadsheets, inboxes, and disconnected systems, AMAD turns it into executive insights, project risk signals, actionable recommendations, and searchable organizational memory through a governed AI Copilot and a set of purpose-built AI agents.

The platform is built for construction executives, project managers, procurement leads, and site engineers who need a fast, trustworthy answer to "what's happening across my portfolio right now" — grounded in real operational data, not guesswork.

## 2. Problem Statement

Construction organizations generate enormous amounts of operational data, but rarely have a coherent way to reason over it:

- **Fragmented data** — projects, procurement, safety, and meetings live in disconnected tools and spreadsheets.
- **Weak organizational memory** — decisions made in meetings are rarely traceable weeks later; institutional knowledge lives in people's inboxes, not systems.
- **Manual reporting** — executive summaries and weekly reports are assembled by hand from multiple sources.
- **Procurement delays** — late purchase orders and at-risk deliveries are discovered too late to act on.
- **Meeting follow-up gaps** — decisions and action items go undocumented or unowned after the meeting ends.
- **Safety and quality risk** — safety events and non-conformance reports (NCRs) are tracked, but rarely surfaced proactively to the people who need to act.
- **Claims and change-order complexity** — financial exposure from claims and change orders is hard to see at a portfolio level until it becomes a problem.

AMAD addresses this by combining structured operational data with a governed AI layer that retrieves, grounds, and cites real records — turning raw data into decisions.

## 3. Core Capabilities

- **Executive Dashboard** — portfolio-level KPIs, health scores, and risk summaries
- **Operations Workspace** — a unified operational view across active projects
- **Project Intelligence** — per-project status, health scoring, and risk drivers
- **Procurement Intelligence Agent** — purchase orders, purchase requests, supplier risk, and delivery delay analysis
- **Meeting Intelligence Agent** — meeting and decision status, single-meeting detail, and follow-up visibility
- **Site Report Intelligence** — daily activity and site report summarization
- **AI Copilot** — a general-purpose, RBAC-scoped conversational assistant over the full operational dataset
- **Claims** — claim exposure tracking and status
- **RFIs** — request-for-information tracking
- **Change Orders** — change order value and status tracking
- **Documents** — project document register
- **Safety & NCR Monitoring** — safety event and non-conformance tracking
- **Audit and Governance** — audit logging of AI interactions and access
- **Arabic and English Support** — full bilingual UI
- **RTL Support** — right-to-left layout for Arabic
- **Role-Based Access Control (RBAC)** — Admin, Executive, Project Manager, Site Engineer, and Safety Officer roles, each scoped to authorized projects and data

## 4. AI Architecture

AMAD's AI layer is deterministic-first and LLM-assisted, not LLM-only. Every response is built on top of a controlled retrieval and grounding pipeline:

- **Intent Detection** — deterministic keyword-based routing (with Arabic and English synonyms) identifies the operational domain of a question before any LLM call is made.
- **Context Detection** — conversation state and page context (e.g. viewing a specific project or report) are resolved to disambiguate follow-up questions.
- **RBAC-Scoped Retrieval** — every data lookup is filtered by the caller's organization and accessible project set before it ever reaches the model; a user can never retrieve data outside their authorization.
- **Grounding** — generated answers are validated against the retrieved evidence; ungrounded or unsupported answers are rejected rather than shown.
- **Citations** — every completed answer is backed by structured citations pointing to the specific source records (purchase orders, meetings, decisions, projects, etc.) used to produce it.
- **OpenRouter LLM Provider** — model access is abstracted behind a provider interface, currently backed by OpenRouter, with provider/model selection controlled entirely through configuration.
- **Deterministic Fallback** — if the LLM provider is unavailable, rate-limited, or returns an ungrounded response, agents fall back to a deterministic, evidence-derived summary rather than surfacing a raw provider error or leaving the UI in a loading state.
- **Specialized Agents** — beyond the general Copilot, fixed-scope agents run their own bounded retrieval (never the general multi-domain fallback), which keeps their evidence — and their citations — scoped strictly to their domain.

## 5. Current AI Agents

### Executive / General Copilot
- **Purpose** — general-purpose, conversational answers across the full operational dataset (projects, health, procurement, suppliers, safety, NCRs, site reports, meetings, decisions, risks).
- **Inputs** — free-text question (English or Arabic), optional project context, conversation history.
- **Outputs** — grounded natural-language answer, citations, confidence level, follow-up suggestions, and structured render blocks for the UI.
- **Maturity** — working, in active refinement (intent coverage, multi-domain retrieval quality).

### Procurement Intelligence Agent
- **Purpose** — fixed-scope specialist over procurement data: purchase requests, purchase orders, supplier risk, and delivery delays.
- **Inputs** — free-text question (English or Arabic), optional project context.
- **Outputs** — structured answer (executive summary, highest-risk procurement issues, affected projects, supplier risk, recommended actions, sources) with citations limited to purchase orders, purchase requests, suppliers, and directly affected projects.
- **Maturity** — working; retrieval and evidence enrichment recently hardened.

### Meeting Intelligence Agent
- **Purpose** — meeting and decision status. Supports both a single-meeting deep dive (decisions, action items, owners, due dates) and a portfolio-wide meetings/decisions status summary.
- **Inputs** — optional `meeting_id` for single-meeting detail; otherwise a free-text status question (English or Arabic).
- **Outputs** — structured answer with total meetings, decisions, key concerns, one recommendation, and sources; falls back to a deterministic summary within seconds if the LLM provider is slow or unavailable.
- **Maturity** — working MVP for the portfolio-wide summary path; single-meeting detail is more mature.

## 6. Technology Stack

**Frontend**
- React
- Vite
- TypeScript
- Tailwind CSS
- TanStack Query
- Radix UI / shadcn-style components
- i18next (Arabic / English, RTL)

**Backend**
- FastAPI
- Python
- PostgreSQL
- SQLAlchemy
- Alembic
- JWT-based authentication
- OpenRouter (LLM provider)

## 7. System Architecture

```
Frontend (React / Vite / TypeScript)
        │
        ▼
FastAPI API Layer
        │
        ▼
Authentication / RBAC
        │
        ▼
AI Pipeline (Intent → Context → Planning)
        │
        ▼
Retrieval / Grounding / Citations
        │
        ▼
PostgreSQL  +  OpenRouter (LLM Provider)
```

## 8. Database Scope

The platform runs against a live, populated PostgreSQL dataset. Verified core operational record counts:

| Entity | Records |
|---|---|
| Projects | 60 |
| Suppliers | 80 |
| Purchase Requests | 3,000 |
| Purchase Orders | 2,550 |
| Site Reports | 1,200 |
| Meetings | 260 |
| NCRs | 739 |
| Safety Events | 449 |
| Claims | 120 |
| **Total records (all tables)** | **13,487** |

*The total spans additional supporting tables (decisions, action items, risks, change orders, RFIs, documents, users, etc.) not itemized individually above.*

## 9. Key Screens

> Screenshots to be added — placeholders below.

![Dashboard](docs/screenshots/dashboard.png)
![Operations](docs/screenshots/operations.png)
![Procurement Agent](docs/screenshots/procurement-agent.png)
![Meeting Agent](docs/screenshots/meeting-agent.png)
![Site Report Intelligence](docs/screenshots/site-report-intelligence.png)
![Copilot](docs/screenshots/copilot.png)

## 10. Installation

### Prerequisites
- Python 3.12+
- Node.js 24.x+
- PostgreSQL 15+
- pnpm 11.x+ (`npm install -g pnpm`)
- Git

### Windows Setup

```powershell
# 1. Clone the repository
git clone <repository-url>
cd amad-construction-ai-platform-main

# 2. Create the database
createdb -U postgres -E UTF8 amad_construction_ai

# 3. Backend — virtual environment
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 4. Backend — configure environment
copy .env.example .env
# edit .env: set DATABASE_URL and SESSION_SECRET (see Environment Variables below)

# 5. Backend — apply migrations
alembic upgrade head

# 6. Frontend — install dependencies
cd ..\artifacts\web
pnpm install
```

## 11. Environment Variables

Set these in `backend/.env`. Values below are placeholders — never commit real secrets.

```env
DATABASE_URL=postgresql://user:password@localhost:5432/amad_construction_ai
SESSION_SECRET=change-me-to-a-long-random-value
LLM_PROVIDER=openrouter
LLM_MODEL=change-me
LLM_API_KEY=change-me
LLM_BASE_URL=https://openrouter.ai/api/v1
```

## 12. Running the Project

**Backend**

```bash
python backend/run_server.py
# → http://127.0.0.1:8000
```

**Frontend**

```bash
cd artifacts/web
pnpm install
pnpm dev
# → http://localhost:5174
```

## 13. Demo Credentials

For local/demo environments only — never use in production:

```
Email:    demo@example.com
Password: change-me
```

## 14. API Documentation

When the backend is running, interactive API documentation is available at:

- Swagger UI — `http://127.0.0.1:8000/api/docs`
- ReDoc — `http://127.0.0.1:8000/api/redoc`
- OpenAPI schema — `http://127.0.0.1:8000/api/openapi.json`

## 15. Project Structure

```
backend/            FastAPI application, models, AI pipeline, migrations
artifacts/web/       React + TypeScript frontend
docs/                Documentation and design assets
deployment/          Deployment configuration (in progress)
README.md            This file
```

## 16. Security and Governance

- **Role-Based Access Control (RBAC)** — every user is scoped to an organization role and an explicit set of accessible projects.
- **Tenant-aware access** — all retrieval, AI and otherwise, is filtered by organization and project authorization before data leaves the database layer.
- **Grounded responses** — AI answers are validated against retrieved evidence; ungrounded answers are rejected, not shown.
- **Citations** — every completed AI answer references the specific source records used.
- **Audit logs** — AI queries, retrieval domains, and outcomes are logged for review.
- **No secret exposure** — provider credentials and internal identifiers are never surfaced in AI responses or logs.
- **Human review** — sensitive or high-impact actions are designed for human review rather than autonomous execution.

## 17. Current Status

- Working MVP with live PostgreSQL database integration
- Three AI capabilities implemented: General Copilot, Procurement Intelligence Agent, Meeting Intelligence Agent
- Full Arabic and English support, including RTL layout
- Actively under development — some modules and agent behaviors are still evolving
- Not yet hardened for production deployment (see Disclaimer)

## 18. Roadmap

- Stronger LLM reliability (timeout handling, provider redundancy)
- Meeting-level selection in the Meeting Agent UI
- Long-term memory layer across conversations
- Document intelligence (parsing and reasoning over uploaded documents)
- Mobile application
- Advanced analytics and portfolio-level forecasting
- Production deployment pipeline
- Multi-agent orchestration across specialized agents

## 19. Future Mobile App

A mobile application is planned, built on the same backend APIs and design system as the web platform, to extend field-level access to project status, safety reporting, and the AI Copilot for site teams.

## 20. Disclaimer

AMAD is a capstone / prototype platform. It demonstrates a working architecture for AI-assisted construction operations intelligence but has not yet undergone the security, performance, and operational hardening required for production deployment. Validate thoroughly — including credential rotation, environment isolation, and load testing — before any production use.

---

**Platform**: Windows, macOS, Linux · **Backend**: Python 3.12+ · **Frontend**: Node 24.x+
