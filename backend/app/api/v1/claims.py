from fastapi import APIRouter, HTTPException, Query
from ...core.deps import DbSession
from ...models.claims import Claim, ChangeOrder, ClaimEvidence
from ...schemas.claims import ClaimOut, ChangeOrderOut, ClaimEvidenceOut

router = APIRouter(tags=["claims"])


@router.get("/projects/{project_id}/claims", response_model=list[ClaimOut])
def list_claims(
    project_id: int,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return (
        db.query(Claim)
        .filter(Claim.project_id == project_id)
        .offset(skip).limit(limit).all()
    )


@router.get("/projects/{project_id}/claims/{claim_id}", response_model=ClaimOut)
def get_claim(project_id: int, claim_id: int, db: DbSession):
    claim = (
        db.query(Claim)
        .filter(Claim.id == claim_id, Claim.project_id == project_id)
        .first()
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.get("/projects/{project_id}/claims/{claim_id}/evidence", response_model=list[ClaimEvidenceOut])
def list_claim_evidence(project_id: int, claim_id: int, db: DbSession):
    claim = db.query(Claim).filter(Claim.id == claim_id, Claim.project_id == project_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return db.query(ClaimEvidence).filter(ClaimEvidence.claim_id == claim_id).all()


@router.get("/projects/{project_id}/change-orders", response_model=list[ChangeOrderOut])
def list_change_orders(
    project_id: int,
    db: DbSession,
    status: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(ChangeOrder).filter(ChangeOrder.project_id == project_id)
    if status:
        q = q.filter(ChangeOrder.status == status)
    return q.offset(skip).limit(limit).all()
