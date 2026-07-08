# Dataset Migration Report

## Source
- Format: SQLite (SQL dump file)
- File: `attached_assets/sql_dataset/construction_ai_dataset_full_dump.sql`
- Total rows: ~13,487

## Destination
- Database: PostgreSQL (Replit managed)
- ORM: SQLAlchemy 2.0
- Migration tool: Alembic (revision 0001)

## Migration Process

1. **Schema creation**: Alembic revision `0001_initial_schema` creates all 27 tables (18 original + 9 new) and enables the `pgvector` extension.

2. **Data loading**: `scripts/migrate_sqlite.py` loads the SQL dump into an in-memory SQLite database, reads each table in FK dependency order, and bulk-inserts into PostgreSQL using `psycopg2.extras.execute_batch`.

3. **Sequence reset**: PostgreSQL sequences for all `id` columns are reset to `MAX(id)` after migration to prevent PK conflicts on new inserts.

## FK Dependency Order

```
projects
suppliers
subcontractors
meetings              → projects
project_decisions     → projects, meetings
purchase_requests     → projects
purchase_orders       → purchase_requests, projects, suppliers
site_reports          → projects
daily_activities      → projects, subcontractors, site_reports
documents             → projects
generated_documents   → projects
correspondence        → projects
safety_events         → projects, subcontractors
ncrs                  → projects, suppliers, subcontractors
claims                → projects
change_orders         → projects
subcontractor_evaluations → subcontractors, projects, safety_events, ncrs, daily_activities
claim_evidence        → claims, change_orders, project_decisions, documents, correspondence
```

## Type Conversions

| Column | SQLite Type | PostgreSQL Type | Notes |
|---|---|---|---|
| `purchase_orders.is_late` | INTEGER (0/1) | BOOLEAN | Converted in migration script |
| All date fields | TEXT | VARCHAR(50) | Kept as strings for Phase 1 |
| `ai_memories.embedding` | — | vector(1536) | New table, pgvector type |

## Known Gaps

- `projects.actual_finish` is NULL for all 60 rows in the source data
- `purchase_requests.material_category` is NULL for ~40% of rows (intentional — AI target)
- `purchase_requests.specification` is NULL for ~35% of rows (intentional — AI target)
- No employee, role, or user data in source (new `user_accounts` table is empty)
- No RFI data in source (requires new `rfis` table — Phase 2)

## Row Count Validation

Run `python -m scripts.migrate_sqlite` to see the live validation report.
Expected totals:

| Table | Expected Rows |
|---|---|
| projects | 60 |
| suppliers | 80 |
| subcontractors | 70 |
| meetings | 260 |
| project_decisions | 535 |
| purchase_requests | 3,000 |
| purchase_orders | 2,550 |
| site_reports | 1,200 |
| daily_activities | 2,385 |
| documents | 120 |
| generated_documents | 1,060 |
| correspondence | 120 |
| safety_events | 449 |
| ncrs | 739 |
| claims | 120 |
| change_orders | 120 |
| subcontractor_evaluations | 499 |
| claim_evidence | 120 |
| **TOTAL** | **13,487** |
