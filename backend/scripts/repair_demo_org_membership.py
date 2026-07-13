"""Repair demo-data consistency: link admin@construction.ai to the demo
organization (slug "amad-demo") if it isn't already linked.

Root cause this repairs: the local demo organization ("Amad Demo",
slug=amad-demo) was seeded, but no seeded user was ever linked to it via
UserAccount.organization_id — so General Library (organization-scoped)
document upload fails for admin@construction.ai with "Your account is not
associated with an organization."

Usage:
    cd backend && python -m scripts.repair_demo_org_membership

Safe to re-run — idempotent:
  - never creates a second organization if "amad-demo" already exists
  - only touches admin@construction.ai; no other user is modified
  - a no-op if admin@construction.ai is already linked to the demo org
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.auth import UserAccount
from app.models.organizations import Organization

DEMO_ORG_SLUG = "amad-demo"
DEMO_ORG_NAME = "Amad Demo"
ADMIN_EMAIL = "admin@construction.ai"


def repair() -> None:
    db = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.slug == DEMO_ORG_SLUG).first()
        if org is None:
            # Defensive only — in every environment seen so far this
            # organization already exists. Never create a second one if a
            # row with this slug is already present (checked above).
            org = Organization(name=DEMO_ORG_NAME, slug=DEMO_ORG_SLUG, is_active=True)
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"  CREATE organization {DEMO_ORG_SLUG!r} (id={org.id}) — none existed yet")
        else:
            print(f"  OK     organization {DEMO_ORG_SLUG!r} already exists (id={org.id})")

        admin = db.query(UserAccount).filter(UserAccount.email == ADMIN_EMAIL).first()
        if admin is None:
            print(f"  SKIP   {ADMIN_EMAIL} not found — nothing to link")
            return

        if admin.organization_id == org.id:
            print(f"  OK     {ADMIN_EMAIL} already linked to organization id={org.id}")
            return

        previous = admin.organization_id
        admin.organization_id = org.id
        db.commit()
        print(f"  LINK   {ADMIN_EMAIL} organization_id: {previous!r} -> {org.id}")
    finally:
        db.close()


if __name__ == "__main__":
    repair()
