from fastapi import APIRouter, Depends
from . import (
    health, projects, procurement, meetings,
    site_reports, documents, claims, safety,
    subcontractors, auth, dashboard, memberships,
    ai_copilot, alerts, executive, reports,
)
from .admin import users as admin_users
from .admin import organizations as admin_orgs
from ...core.deps import get_current_user, require_roles

router = APIRouter()

# Public endpoints — no auth
router.include_router(health.router)
router.include_router(auth.router)

# All authenticated users — dashboard and project read
_any_auth = [Depends(get_current_user)]
router.include_router(dashboard.router, dependencies=_any_auth)
router.include_router(projects.router, dependencies=_any_auth)

# Procurement domain — restricted to procurement_officer, project_manager, executive
_procurement_roles = [require_roles(
    "executive", "project_manager", "procurement_officer",
)]
router.include_router(procurement.router, dependencies=_procurement_roles)

# Safety & NCR domain — restricted to safety_quality_officer, project_manager, executive
_safety_roles = [require_roles(
    "executive", "project_manager", "safety_quality_officer",
)]
router.include_router(safety.router, dependencies=_safety_roles)

# Site reports — site_engineer, project_manager, executive
_site_roles = [require_roles(
    "executive", "project_manager", "site_engineer",
)]
router.include_router(site_reports.router, dependencies=_site_roles)

# Meetings & decisions — project_manager, executive
_meetings_roles = [require_roles(
    "executive", "project_manager",
)]
router.include_router(meetings.router, dependencies=_meetings_roles)

# Documents & claims — project_manager, executive
_docs_roles = [require_roles(
    "executive", "project_manager",
)]
router.include_router(documents.router, dependencies=_docs_roles)
router.include_router(claims.router, dependencies=_docs_roles)

# Subcontractors — broad operational access
_subcontractor_roles = [require_roles(
    "executive", "project_manager", "site_engineer", "safety_quality_officer",
)]
router.include_router(subcontractors.router, dependencies=_subcontractor_roles)

# Project memberships — project_manager and above
_membership_roles = [require_roles("admin", "executive", "project_manager")]
router.include_router(memberships.router, dependencies=_membership_roles)

# Admin-only endpoints
_admin_only = [require_roles("admin")]
router.include_router(admin_users.router, dependencies=_admin_only)
router.include_router(admin_orgs.router, dependencies=_admin_only)

# AI Copilot — all authenticated users
router.include_router(ai_copilot.router, dependencies=_any_auth)

# Smart Alerts — all authenticated users
router.include_router(alerts.router, dependencies=_any_auth)

# Executive Intelligence — all authenticated users
router.include_router(executive.router, dependencies=_any_auth)

# Executive Reports — all authenticated users
router.include_router(reports.router, dependencies=_any_auth)
