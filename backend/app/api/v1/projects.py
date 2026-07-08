from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from ...core.deps import DbSession
from ...models.projects import Project, ProjectRisk, ProjectIssue
from ...schemas.projects import (
    ProjectOut, ProjectCreate, ProjectUpdate, ProjectSummary,
    ProjectRiskCreate, ProjectRiskOut, ProjectIssueCreate, ProjectIssueOut,
    HealthScoreOut,
)
from ...ai.health_score import get_project_health, get_all_projects_health

router = APIRouter(prefix="/projects", tags=["projects"])


# ── Health score endpoints (before /{project_id} to avoid route shadowing) ───

@router.get("/health-scores", response_model=list[HealthScoreOut])
def list_project_health_scores(db: DbSession):
    """Return health scores for all projects, sorted by score ascending (worst first)."""
    results = get_all_projects_health(db)
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
def get_health_score(project_id: int, db: DbSession):
    """Return the health score for a single project."""
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
    status: Optional[str] = None,
    city: Optional[str] = None,
    project_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(Project)
    if status:
        q = q.filter(Project.status == status)
    if city:
        q = q.filter(Project.city == city)
    if project_type:
        q = q.filter(Project.project_type == project_type)
    return q.offset(skip).limit(limit).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: DbSession):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: DbSession):
    project = Project(**body.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectUpdate, db: DbSession):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}/risks", response_model=list[ProjectRiskOut])
def list_project_risks(project_id: int, db: DbSession):
    return db.query(ProjectRisk).filter(ProjectRisk.project_id == project_id).all()


@router.post("/{project_id}/risks", response_model=ProjectRiskOut, status_code=201)
def create_project_risk(project_id: int, body: ProjectRiskCreate, db: DbSession):
    risk = ProjectRisk(project_id=project_id, **body.model_dump())
    db.add(risk)
    db.commit()
    db.refresh(risk)
    return risk


@router.get("/{project_id}/issues", response_model=list[ProjectIssueOut])
def list_project_issues(project_id: int, db: DbSession):
    return db.query(ProjectIssue).filter(ProjectIssue.project_id == project_id).all()


@router.post("/{project_id}/issues", response_model=ProjectIssueOut, status_code=201)
def create_project_issue(project_id: int, body: ProjectIssueCreate, db: DbSession):
    issue = ProjectIssue(project_id=project_id, **body.model_dump())
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue
