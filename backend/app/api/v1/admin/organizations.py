from fastapi import APIRouter, HTTPException, status

from ....core.deps import DbSession
from ....models.organizations import Organization
from ....schemas.organizations import OrganizationCreate, OrganizationUpdate, OrganizationOut

router = APIRouter(prefix="/admin/organizations", tags=["admin"])


@router.get("", response_model=list[OrganizationOut])
def list_organizations(db: DbSession):
    return db.query(Organization).order_by(Organization.created_at.desc()).all()


@router.post("", response_model=OrganizationOut, status_code=201)
def create_organization(body: OrganizationCreate, db: DbSession):
    existing = db.query(Organization).filter(Organization.slug == body.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slug already in use",
        )
    org = Organization(**body.model_dump())
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get("/{org_id}", response_model=OrganizationOut)
def get_organization(org_id: int, db: DbSession):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.patch("/{org_id}", response_model=OrganizationOut)
def update_organization(org_id: int, body: OrganizationUpdate, db: DbSession):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    if body.slug is not None:
        clash = db.query(Organization).filter(
            Organization.slug == body.slug,
            Organization.id != org_id,
        ).first()
        if clash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    db.commit()
    db.refresh(org)
    return org
