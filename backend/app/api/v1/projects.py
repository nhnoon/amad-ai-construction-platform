from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from ...ai.scope import get_project_or_404
from ...ai.workflow_engine import update_project_issue, update_project_risk
from ...ai.ownership_engine import (
    apply_ownership_filters,
    assign_project_issue, unassign_project_issue,
    assign_project_risk, unassign_project_risk,
)
from ...core.deps import CurrentScope, DbSession
from ...models.projects import Project, ProjectRisk, ProjectIssue
from ...schemas.projects import (
    ProjectOut, ProjectCreate, ProjectUpdate, ProjectSummary,
    ProjectRiskCreate, ProjectRiskOut, ProjectRiskUpdate,
    ProjectIssueCreate, ProjectIssueOut, ProjectIssueUpdate,
    HealthScoreOut,
)
from ...schemas.ownership import AssignRequest, UnassignRequest
from ...ai.health_score import get_project_health, get_all_projects_health

router = APIRouter(prefix="/projects", tags=["projects"])


# ── Health score endpoints (before /{project_id} to avoid route shadowing) ───

@router.get("/health-scores", response_model=list[HealthScoreOut])
def list_project_health_scores(db: DbSession, scope: CurrentScope):
    """Return health scores for the caller's accessible projects, sorted by
    score ascending (worst first). Does not change the scoring formula
    (see app/ai/health_score.py) — only filters which projects' scores the
    caller may see, same organization/membership boundary as everywhere
    else (Phase 1 production-hardening)."""
    accessible = set(scope.accessible_project_ids)
    results = [r for r in get_all_projects_health(db) if r.project_id in accessible]
    return [
        HealthScoreOut(
            project_id=r.project_id,
            project_code=r.project_code,
            project_name=r.project_name,
            status=r.status,
            score=r.score,
            level=r.level,
            reasons=r.reasons,
            schedule_penalty=r.schedule_penalty,
            safety_penalty=r.safety_penalty,
            ncr_penalty=r.ncr_penalty,
            procurement_penalty=r.procurement_penalty,
            risk_penalty=r.risk_penalty,
        )
        for r in results
    ]


@router.get("/{project_id}/health", response_model=HealthScoreOut)
def get_health_score(project_id: int, db: DbSession, scope: CurrentScope):
    """Return the health score for a single project."""
    get_project_or_404(db, scope, project_id)
    result = get_project_health(project_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return HealthScoreOut(
        project_id=result.project_id,
        project_code=result.project_code,
        project_name=result.project_name,
        status=result.status,
        score=result.score,
        level=result.level,
        reasons=result.reasons,
        schedule_penalty=result.schedule_penalty,
        safety_penalty=result.safety_penalty,
        ncr_penalty=result.ncr_penalty,
        procurement_penalty=result.procurement_penalty,
        risk_penalty=result.risk_penalty,
    )


# ── Standard CRUD ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[ProjectSummary])
def list_projects(
    db: DbSession,
    scope: CurrentScope,
    status: Optional[str] = None,
    city: Optional[str] = None,
    project_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    ids = list(scope.accessible_project_ids)
    if not ids:
        return []
    q = db.query(Project).filter(Project.id.in_(ids))
    if status:
        q = q.filter(Project.status == status)
    if city:
        q = q.filter(Project.city == city)
    if project_type:
        q = q.filter(Project.project_type == project_type)
    return q.offset(skip).limit(limit).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: DbSession, scope: CurrentScope):
    return get_project_or_404(db, scope, project_id)


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: DbSession, scope: CurrentScope):
    # organization_id is never client-supplied — always the authenticated
    # caller's own organization, determined server-side (Phase 1
    # production-hardening quality constraint).
    if scope.organization_id is None:
        raise HTTPException(
            status_code=400,
            detail="Your account is not associated with an organization; cannot create a project.",
        )
    project = Project(organization_id=scope.organization_id, **body.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectUpdate, db: DbSession, scope: CurrentScope):
    project = get_project_or_404(db, scope, project_id)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}/risks", response_model=list[ProjectRiskOut])
def list_project_risks(
    project_id: int, db: DbSession, scope: CurrentScope,
    assigned_to_me: bool = False, assigned_to: Optional[int] = None, unassigned: bool = False,
):
    scope.enforce_project_access(project_id)
    q = db.query(ProjectRisk).filter(ProjectRisk.project_id == project_id)
    q = apply_ownership_filters(q, ProjectRisk, scope, assigned_to_me=assigned_to_me, assigned_to=assigned_to, unassigned=unassigned)
    return q.all()


@router.post("/{project_id}/risks", response_model=ProjectRiskOut, status_code=201)
def create_project_risk(project_id: int, body: ProjectRiskCreate, db: DbSession, scope: CurrentScope):
    scope.enforce_project_access(project_id)
    risk = ProjectRisk(project_id=project_id, **body.model_dump())
    db.add(risk)
    db.commit()
    db.refresh(risk)
    return risk


@router.patch("/{project_id}/risks/{risk_id}", response_model=ProjectRiskOut)
def update_project_risk_route(project_id: int, risk_id: int, body: ProjectRiskUpdate, db: DbSession, scope: CurrentScope):
    """Core Workflow Engine (Sprint 2) — see app/ai/workflow_engine.py for
    the status transition matrix and close-out rules."""
    return update_project_risk(db, scope, project_id, risk_id, body)


@router.post("/{project_id}/risks/{risk_id}/assign", response_model=ProjectRiskOut)
def assign_project_risk_route(project_id: int, risk_id: int, body: AssignRequest, db: DbSession, scope: CurrentScope):
    """Ownership Engine (Sprint 3) — see app/ai/ownership_engine.py.
    Self-assignment is always allowed; assigning to someone else requires
    manager authority (admin/executive/project_manager, globally or on
    this project)."""
    return assign_project_risk(db, scope, project_id, risk_id, body.user_id, body.expected_updated_at)


@router.post("/{project_id}/risks/{risk_id}/unassign", response_model=ProjectRiskOut)
def unassign_project_risk_route(project_id: int, risk_id: int, body: UnassignRequest, db: DbSession, scope: CurrentScope):
    return unassign_project_risk(db, scope, project_id, risk_id, body.expected_updated_at)


@router.get("/{project_id}/issues", response_model=list[ProjectIssueOut])
def list_project_issues(
    project_id: int, db: DbSession, scope: CurrentScope,
    assigned_to_me: bool = False, assigned_to: Optional[int] = None, unassigned: bool = False,
):
    scope.enforce_project_access(project_id)
    q = db.query(ProjectIssue).filter(ProjectIssue.project_id == project_id)
    q = apply_ownership_filters(q, ProjectIssue, scope, assigned_to_me=assigned_to_me, assigned_to=assigned_to, unassigned=unassigned)
    return q.all()


@router.post("/{project_id}/issues", response_model=ProjectIssueOut, status_code=201)
def create_project_issue(project_id: int, body: ProjectIssueCreate, db: DbSession, scope: CurrentScope):
    scope.enforce_project_access(project_id)
    issue = ProjectIssue(project_id=project_id, **body.model_dump())
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@router.patch("/{project_id}/issues/{issue_id}", response_model=ProjectIssueOut)
def update_project_issue_route(project_id: int, issue_id: int, body: ProjectIssueUpdate, db: DbSession, scope: CurrentScope):
    return update_project_issue(db, scope, project_id, issue_id, body)


@router.post("/{project_id}/issues/{issue_id}/assign", response_model=ProjectIssueOut)
def assign_project_issue_route(project_id: int, issue_id: int, body: AssignRequest, db: DbSession, scope: CurrentScope):
    return assign_project_issue(db, scope, project_id, issue_id, body.user_id, body.expected_updated_at)


@router.post("/{project_id}/issues/{issue_id}/unassign", response_model=ProjectIssueOut)
def unassign_project_issue_route(project_id: int, issue_id: int, body: UnassignRequest, db: DbSession, scope: CurrentScope):
    return unassign_project_issue(db, scope, project_id, issue_id, body.expected_updated_at)
