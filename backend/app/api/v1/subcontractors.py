from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from sqlalchemy import func
from ...core.deps import DbSession
from ...models.subcontractors import Subcontractor, SubcontractorEvaluation
from ...schemas.subcontractors import SubcontractorOut, SubcontractorEvaluationOut

router = APIRouter(tags=["subcontractors"])


@router.get("/subcontractors", response_model=list[SubcontractorOut])
def list_subcontractors(
    db: DbSession,
    trade: Optional[str] = None,
    status: Optional[str] = None,
    city: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(Subcontractor)
    if trade:
        q = q.filter(Subcontractor.trade == trade)
    if status:
        q = q.filter(Subcontractor.status == status)
    if city:
        q = q.filter(Subcontractor.city == city)
    return q.offset(skip).limit(limit).all()


@router.get("/subcontractors/{subcontractor_id}", response_model=SubcontractorOut)
def get_subcontractor(subcontractor_id: int, db: DbSession):
    sub = db.query(Subcontractor).filter(Subcontractor.id == subcontractor_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subcontractor not found")
    return sub


@router.get("/subcontractors/{subcontractor_id}/evaluations", response_model=list[SubcontractorEvaluationOut])
def list_evaluations(
    subcontractor_id: int,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return (
        db.query(SubcontractorEvaluation)
        .filter(SubcontractorEvaluation.subcontractor_id == subcontractor_id)
        .offset(skip).limit(limit).all()
    )


@router.get("/subcontractors/{subcontractor_id}/performance")
def get_subcontractor_performance(subcontractor_id: int, db: DbSession):
    sub = db.query(Subcontractor).filter(Subcontractor.id == subcontractor_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subcontractor not found")

    evals = db.query(SubcontractorEvaluation).filter(
        SubcontractorEvaluation.subcontractor_id == subcontractor_id
    ).all()

    if not evals:
        return {"subcontractor_id": subcontractor_id, "name": sub.name, "evaluations": 0}

    avg_quality = sum(e.quality_score for e in evals) / len(evals)
    avg_safety = sum(e.safety_score for e in evals) / len(evals)
    avg_schedule = sum(e.schedule_score for e in evals) / len(evals)
    avg_overall = sum(e.overall_rating for e in evals) / len(evals)

    return {
        "subcontractor_id": subcontractor_id,
        "name": sub.name,
        "trade": sub.trade,
        "classification": sub.classification,
        "evaluations": len(evals),
        "avg_quality_score": round(avg_quality, 1),
        "avg_safety_score": round(avg_safety, 1),
        "avg_schedule_score": round(avg_schedule, 1),
        "avg_overall_rating": round(avg_overall, 2),
    }


@router.get("/projects/{project_id}/subcontractor-evaluations", response_model=list[SubcontractorEvaluationOut])
def list_project_evaluations(
    project_id: int,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return (
        db.query(SubcontractorEvaluation)
        .filter(SubcontractorEvaluation.project_id == project_id)
        .offset(skip).limit(limit).all()
    )
