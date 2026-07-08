"""
Seed B2B foundation data: demo organization + link all existing users.

Run once after alembic upgrade head:
    cd backend && python -m scripts.seed_organizations
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.organizations import Organization
from app.models.auth import UserAccount


DEMO_ORG = {
    "name": "Amad Demo Construction Co.",
    "slug": "amad-demo",
    "is_active": True,
}


def seed():
    db = SessionLocal()
    try:
        existing = db.query(Organization).filter(Organization.slug == DEMO_ORG["slug"]).first()
        if existing:
            print(f"Demo organization already exists (id={existing.id}). Skipping creation.")
            org = existing
        else:
            org = Organization(**DEMO_ORG)
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"Created organization: '{org.name}' (id={org.id}, slug={org.slug})")

        unlinked = (
            db.query(UserAccount)
            .filter(UserAccount.organization_id.is_(None))
            .all()
        )
        if unlinked:
            for user in unlinked:
                user.organization_id = org.id
            db.commit()
            print(f"Linked {len(unlinked)} existing user(s) to '{org.name}'.")
        else:
            print("All users already linked to an organization.")

        total_users = db.query(UserAccount).filter(UserAccount.organization_id == org.id).count()
        print(f"\nSummary: org_id={org.id}, users_in_org={total_users}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
