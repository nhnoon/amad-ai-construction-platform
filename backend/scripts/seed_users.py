"""Seed default users for all roles.

Usage:
    cd backend && python -m scripts.seed_users

Safe to re-run — skips existing emails.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.auth import UserAccount
from app.core.security import hash_password

SEED_USERS = [
    {
        "email": "admin@construction.ai",
        "password": "Admin123!",
        "full_name": "System Administrator",
        "role": "admin",
    },
    {
        "email": "executive@construction.ai",
        "password": "Admin123!",
        "full_name": "Ahmad Al-Rashidi",
        "role": "executive",
    },
    {
        "email": "pm@construction.ai",
        "password": "Admin123!",
        "full_name": "Khalid Al-Mansouri",
        "role": "project_manager",
    },
    {
        "email": "engineer@construction.ai",
        "password": "Admin123!",
        "full_name": "Mohammed Al-Zahrani",
        "role": "site_engineer",
    },
    {
        "email": "procurement@construction.ai",
        "password": "Admin123!",
        "full_name": "Fatima Al-Otaibi",
        "role": "procurement_officer",
    },
    {
        "email": "safety@construction.ai",
        "password": "Admin123!",
        "full_name": "Omar Al-Ghamdi",
        "role": "safety_quality_officer",
    },
]


def seed():
    db = SessionLocal()
    try:
        created = 0
        skipped = 0
        for u in SEED_USERS:
            existing = db.query(UserAccount).filter(UserAccount.email == u["email"]).first()
            if existing:
                print(f"  SKIP  {u['email']} (already exists, role={existing.role})")
                skipped += 1
                continue
            user = UserAccount(
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                is_active=True,
            )
            db.add(user)
            created += 1
            print(f"  CREATE {u['email']} (role={u['role']})")
        db.commit()
        print(f"\nDone: {created} created, {skipped} skipped.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
