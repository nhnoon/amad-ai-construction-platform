from fastapi import APIRouter, HTTPException, status

from ....core.deps import CurrentScope, DbSession
from ....models.organizations import Organization
from ....schemas.organizations import OrganizationUpdate, OrganizationOut

router = APIRouter(prefix="/admin/organizations", tags=["admin"])

# NOTE (RC1 Phase 0 — Security Remediation, Finding 1): every handler below
# is scoped to the calling admin's own organization, mirroring the identical
# fix already applied to app/api/v1/admin/users.py. Before this fix, none of
# these routes took the caller's scope into account at all — an admin in
# one organization could list, read, rename, re-slug, or deactivate ANY
# organization on the platform purely by knowing or guessing its id.
# "admin" is an organization-scoped role in this app (see app/ai/scope.py)
# — there is no platform-level super-admin — so this endpoint family needs
# the identical treatment as admin/users.py. 404 (not 403) for an
# organization that isn't the caller's own, matching the standardized
# hide-cross-tenant-existence policy used everywhere else
# (app/ai/scope.py::get_project_or_404, admin/users.py::_get_user_or_404).
#
# Organization CREATION is intentionally not exposed on this router at all
# (not merely scoped down): onboarding a brand-new tenant is an operator-run
# action today (see backend/scripts/seed_organizations.py and
# backend/scripts/seed_demo_data.py), never something one tenant's admin
# should be able to trigger over the API. Removing the route — rather than
# scoping it to "creates only for my own org", which is meaningless for a
# create — closes the "tenant admin creates/enumerates another tenant"
# vector entirely, without inventing a new platform-super-admin role in
# this sprint.


def _get_own_organization_or_404(db, scope, org_id: int) -> Organization:
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org is None or scope.organization_id is None or org.id != scope.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.get("", response_model=list[OrganizationOut])
def list_organizations(db: DbSession, scope: CurrentScope):
    # A tenant admin has exactly one organization to see — their own.
    # Returns an empty list (not an error) for the edge case of an admin
    # account with no organization_id at all, rather than leaking every
    # tenant on the platform.
    if scope.organization_id is None:
        return []
    return (
        db.query(Organization)
        .filter(Organization.id == scope.organization_id)
        .order_by(Organization.created_at.desc())
        .all()
    )


@router.get("/{org_id}", response_model=OrganizationOut)
def get_organization(org_id: int, db: DbSession, scope: CurrentScope):
    return _get_own_organization_or_404(db, scope, org_id)


@router.patch("/{org_id}", response_model=OrganizationOut)
def update_organization(org_id: int, body: OrganizationUpdate, db: DbSession, scope: CurrentScope):
    org = _get_own_organization_or_404(db, scope, org_id)
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
