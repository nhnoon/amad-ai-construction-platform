"""Phase 1 production-hardening — add Project.organization_id (root
tenant-ownership column) and backfill both projects and any still-unlinked
users onto the existing organization.

Verified state at authoring time (real dev database): exactly ONE
organization exists ("Amad Demo", slug=amad-demo), all 60 existing projects
have no organization_id (column is new), and 28 of 29 seeded/test user
accounts have no organization_id despite the column existing since
migration 0003 — only admin@construction.ai was ever linked (see
scripts/repair_demo_org_membership.py, which this migration generalizes to
every user, not just the admin account).

Because exactly one organization exists, backfilling every unlinked
project/user to it is not an arbitrary choice — it is the only
organization in the system. This migration refuses to guess if that
precondition doesn't hold in some other environment (more than one
organization present with unlinked rows): it raises instead of silently
assigning tenant ownership incorrectly.

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-19
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sole_organization_id(bind) -> int:
    org_count = bind.execute(sa.text("SELECT COUNT(*) FROM organizations")).scalar()
    if org_count != 1:
        raise RuntimeError(
            f"Refusing to backfill: expected exactly 1 organization for an "
            f"unambiguous backfill, found {org_count}. Assign "
            f"organization_id manually for the affected rows, then re-run "
            f"this migration — see the Phase 1 production-hardening report "
            f"for the reasoning behind this guard."
        )
    return bind.execute(sa.text("SELECT id FROM organizations LIMIT 1")).scalar()


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. Add the column nullable first (existing rows need a value
    #      before NOT NULL can be enforced) ────────────────────────────────
    op.add_column("projects", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])
    op.create_foreign_key(
        "fk_projects_organization_id_organizations", "projects", "organizations",
        ["organization_id"], ["id"], ondelete="RESTRICT",
    )

    # ── 2. Backfill existing projects ──────────────────────────────────────
    unassigned_projects = bind.execute(
        sa.text("SELECT COUNT(*) FROM projects WHERE organization_id IS NULL")
    ).scalar()
    if unassigned_projects and unassigned_projects > 0:
        sole_org_id = _sole_organization_id(bind)
        bind.execute(
            sa.text(
                "UPDATE projects SET organization_id = :org_id "
                "WHERE organization_id IS NULL"
            ),
            {"org_id": sole_org_id},
        )

    # ── 3. Now safe to enforce NOT NULL on projects.organization_id ────────
    op.alter_column("projects", "organization_id", nullable=False)

    # ── 4. Backfill any still-unlinked users onto the same organization.
    #      user_accounts.organization_id has existed since migration 0003,
    #      but only ever got populated for admin@construction.ai (via
    #      scripts/repair_demo_org_membership.py). Every other seeded/demo
    #      account — executive, project_manager, site_engineer,
    #      procurement_officer, safety_quality_officer, and any ad hoc test
    #      accounts — was left unlinked. Left as-is, Phase 1's organization
    #      scoping would make every one of those accounts lose access to
    #      all project data the moment it's enforced, which would silently
    #      break the existing demo rather than preserve it. This column
    #      stays NULLABLE (unlike projects.organization_id) — a user with
    #      no organization is a valid, if functionally limited, state (see
    #      app/ai/scope.py's build_ai_scope), so there is no NOT NULL step
    #      here, only a backfill of what's currently unset. ─────────────────
    unassigned_users = bind.execute(
        sa.text("SELECT COUNT(*) FROM user_accounts WHERE organization_id IS NULL")
    ).scalar()
    if unassigned_users and unassigned_users > 0:
        sole_org_id = _sole_organization_id(bind)
        bind.execute(
            sa.text(
                "UPDATE user_accounts SET organization_id = :org_id "
                "WHERE organization_id IS NULL"
            ),
            {"org_id": sole_org_id},
        )


def downgrade() -> None:
    op.drop_constraint("fk_projects_organization_id_organizations", "projects", type_="foreignkey")
    op.drop_index("ix_projects_organization_id", table_name="projects")
    op.drop_column("projects", "organization_id")
    # Deliberately NOT reversing the user_accounts.organization_id backfill
    # (step 4) — that column pre-dates this migration (0003) and downgrading
    # this revision should not un-link users that were already correctly
    # linked before this migration ran (e.g. admin@construction.ai).
