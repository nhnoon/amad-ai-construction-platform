# B2B SaaS Foundation — Architecture Reference

## Overview

Phase 2 adds multi-tenant B2B SaaS primitives on top of the Phase 1 backend: organizations, admin-controlled user management, and per-project memberships. The admin user is the only gateway for provisioning users (no self-registration).

## Database Schema (migration 0003)

### `organizations`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | auto-increment |
| name | VARCHAR(255) | UNIQUE, NOT NULL |
| slug | VARCHAR(100) | UNIQUE, lowercase, URL-safe |
| is_active | BOOLEAN | default TRUE |
| created_at | VARCHAR(50) | ISO timestamp |

### `user_accounts` (additions)
| Column | Type | Notes |
|---|---|---|
| organization_id | INTEGER FK → organizations.id | nullable |
| last_login | VARCHAR(50) | updated on each /auth/token |

### `project_memberships`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| project_id | INTEGER FK → projects.id | |
| user_id | INTEGER FK → user_accounts.id | |
| role | VARCHAR(50) | default "member" |
| added_at | VARCHAR(50) | ISO timestamp |
| UNIQUE(project_id, user_id) | | no duplicate members |

## API Endpoints

### Admin — Users (`/api/v1/admin/users`)
All endpoints require `Authorization: Bearer <jwt>` where the token belongs to a user with `role = "admin"`.

| Method | Path | Description |
|---|---|---|
| GET | `/admin/users` | List all users (with optional `org_id` filter) |
| POST | `/admin/users` | Create a user (sets hashed password, role, org) |
| GET | `/admin/users/{id}` | Get user by ID |
| PATCH | `/admin/users/{id}` | Update role / is_active / org_id |
| POST | `/admin/users/{id}/reset-password` | Generate new temp password (returns plaintext once) |

### Admin — Organizations (`/api/v1/admin/organizations`)
Same admin-only access requirement.

| Method | Path | Description |
|---|---|---|
| GET | `/admin/organizations` | List all organizations |
| POST | `/admin/organizations` | Create organization |
| GET | `/admin/organizations/{id}` | Get by ID |
| PATCH | `/admin/organizations/{id}` | Update name/slug/is_active |

### Project Memberships (`/api/v1/projects/{project_id}/members`)
Requires authentication. Only admins and project managers may add/remove members.

| Method | Path | Description |
|---|---|---|
| GET | `/projects/{id}/members` | List project members |
| POST | `/projects/{id}/members` | Add a member (body: `{user_id, role}`) |
| DELETE | `/projects/{id}/members/{user_id}` | Remove a member |

## Auth Changes

- `POST /auth/register` is now **admin-only** (requires valid admin JWT). Team members are provisioned exclusively via `POST /admin/users`.
- `POST /auth/token` updates `user_accounts.last_login` on each successful login.

## RBAC Matrix

| Role | Admin APIs | Create Projects | View Data |
|---|---|---|---|
| admin | ✓ full access | ✓ | ✓ |
| executive | ✗ | ✗ | ✓ |
| project_manager | ✗ | ✗ | ✓ own projects |
| site_engineer | ✗ | ✗ | ✓ site data |
| procurement_officer | ✗ | ✗ | ✓ procurement |
| safety_quality_officer | ✗ | ✗ | ✓ safety/NCR |
| viewer | ✗ | ✗ | ✓ read-only |

## Frontend (artifacts/web)

Two admin-only pages, accessible only when `user.role === "admin"`:

- `/admin/users` — user list with role badges, activate/deactivate toggle, reset-password dialog (copies new temp password to clipboard)
- `/admin/organization` — organization cards with create/edit/toggle-active actions

The sidebar's "Administration" section is hidden for non-admin users. Attempting to navigate to an admin route redirects non-admins back to `/`.

## Seed Data

Run once after migration:
```bash
cd backend && python -m scripts.seed_organizations
```
Creates `Amad Demo Construction Co.` and links all existing users to it (idempotent on org creation, re-links users on re-run).
