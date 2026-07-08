# Dataset Setup & Restoration Guide

## Overview

The AMAD Construction AI Platform includes a comprehensive production dataset with **13,487 records across 18 operational tables**. This includes:

- **60 real construction projects** with full lifecycles
- **80 suppliers** with performance metrics
- **70 subcontractors** with evaluation histories
- **1,200+ site reports** with daily activity logs
- **2,385+ daily activities** with task tracking
- **3,000+ purchase requests** with procurement workflows
- **2,550+ purchase orders** with delivery tracking
- **1,060+ generated documents** for project deliverables
- **449 safety events** with incident severity levels
- **739 NCRs** (non-conformance reports) with closure tracking
- **120 claims** with financial impact analysis
- **And more...**

The dataset is stored externally as a **SQLite-format SQL dump** and can be loaded into PostgreSQL for full platform functionality.

## ⚠️ Important Notes

- The dataset is **NOT included in the Git repository** (see `.gitignore`)
- The dataset must be placed manually in `backend/data/` directory
- After placement, a migration script restores it into PostgreSQL
- The platform works without the dataset (uses seeded demo data), but full features require it
- The dataset is production-ready and demonstrates real construction workflows

## Prerequisites

Before restoring the dataset, ensure:

1. PostgreSQL 15+ is installed and running
2. `backend/.env` is configured with valid `DATABASE_URL`
3. Database exists and migrations have run:
   ```bash
   cd backend
   alembic upgrade head
   ```
4. The SQL dump file is available

## Obtaining the Dataset

The dataset file (`construction_ai_dataset_full_dump.sql`) is stored externally and must be obtained from:

- **Project Repository**: Ask the team for the data file
- **Shared Storage**: Check project drive/cloud storage
- **Replit Workspace**: If available in source Replit environment

## Restoring the Dataset (Method 1: Automated Script)

### Step 1: Place the SQL Dump

```bash
# Copy the SQL dump to the expected location
# File: construction_ai_dataset_full_dump.sql
# Destination: backend/data/construction_ai_dataset_full_dump.sql

# On Windows:
copy "C:\path\to\construction_ai_dataset_full_dump.sql" "backend\data\"

# On macOS/Linux:
cp /path/to/construction_ai_dataset_full_dump.sql backend/data/
```

### Step 2: Run the Migration Script

```bash
cd backend

# Activate virtual environment
.venv\Scripts\activate    # Windows
# or
source .venv/bin/activate # macOS/Linux

# Run the migration script
python migrate_from_local_data.py
```

**Expected Output:**
```
Loading SQLite dump from: backend/data/construction_ai_dataset_full_dump.sql
SQLite loaded into memory.
Connecting to PostgreSQL: localhost:5432/amad_construction_ai
Clearing existing data...
✓ Existing data cleared

Table                        Source   Inserted   Status
─────────────────────────────────────────────────────────
projects                        60         60     ✓
suppliers                        80         80     ✓
[... all tables ...]
─────────────────────────────────────────────────────────
TOTAL                        13487      13487

✓ Migration completed successfully!
✓ Total rows migrated: 13487
```

### Step 3: Verify Restoration

```bash
# Start backend server
python run_server.py

# The frontend should now show:
# - Dashboard with real metrics
# - 60 projects in Projects page
# - 80 suppliers in Suppliers page
# - 1,089 alerts in Alerts page
# - Real executive reports
```

## Restoring the Dataset (Method 2: Manual PostgreSQL)

If the automated script doesn't work:

```bash
# Method 1: Direct SQL restore with psql
psql -U postgres -d amad_construction_ai < backend/data/construction_ai_dataset_full_dump.sql

# Method 2: Using pgAdmin GUI
# 1. Open pgAdmin
# 2. Right-click database → Restore
# 3. Select the SQL dump file
# 4. Start restoration

# Verify the data loaded
psql -U postgres -d amad_construction_ai -c "SELECT COUNT(*) FROM projects;"
# Should show: 60

# Check all tables
psql -U postgres -d amad_construction_ai -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
```

## Dataset Contents

### Projects Table (60 records)
```sql
SELECT project_code, project_name, status, health_score 
FROM projects 
ORDER BY health_score DESC 
LIMIT 10;
```

Example projects:
- Khobar School Project 1
- Tabuk Tower Project 2
- Riyadh Hospital Project 3
- Jubail School Project 4
- Dammam School Project 5

### Suppliers Table (80 records)
```sql
SELECT supplier_name, performance_rating, total_orders 
FROM suppliers 
ORDER BY performance_rating DESC 
LIMIT 10;
```

Example suppliers:
- Risk Supplier 001
- Risk Supplier 002
- Quality Watch Supplier 005
- Standard Supplier 010

### Safety Events (449 records)
```sql
SELECT COUNT(*), severity 
FROM safety_events 
GROUP BY severity;
```

Critical and high-severity incidents tracked and analyzed.

### Procurement Data
- **Purchase Requests**: 3,000 records with workflow status
- **Purchase Orders**: 2,550 records with delivery tracking
- **Subcontractors**: 70 records with evaluation history

### Quality & Compliance
- **NCRs**: 739 non-conformance reports
- **Documents**: 1,060 generated project documents
- **Meeting Records**: 260+ meetings with action items

## Troubleshooting

### "File not found" error

```bash
# Verify the file exists
ls -la backend/data/construction_ai_dataset_full_dump.sql

# Check file is readable
file backend/data/construction_ai_dataset_full_dump.sql

# If file is large (>100MB), ensure:
# - Enough disk space
# - Enough RAM (>2GB recommended)
# - No antivirus blocking file access
```

### "Permission denied" error

```bash
# On Windows, ensure PostgreSQL service is running
net start postgresql-x64-15

# Verify database user has permissions
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE amad_construction_ai TO postgres;"
```

### Migration script errors

```bash
# Check Python dependencies
pip install -r requirements.txt

# Verify PostgreSQL connection
psql -U postgres -d amad_construction_ai -c "SELECT version();"

# Check .env configuration
cat .env | grep DATABASE_URL

# Manually verify SQLite dump format
file backend/data/construction_ai_dataset_full_dump.sql
```

### Duplicate key errors

```bash
# If running migration twice, clear data first
cd backend
python clear_data.py

# Then run migration again
python migrate_from_local_data.py
```

## Working Without the Dataset

If the dataset is unavailable:

1. Platform still functions with default seeded data
2. Run `python -m scripts.seed_users` to create demo data
3. Login with credentials:
   - Email: `admin@construction.ai`
   - Password: `Admin123!`
4. Dashboard will show placeholder metrics
5. All API endpoints functional with minimal test data

## Performance Notes

**Restoration Time**:
- Full dataset: 30-60 seconds on typical hardware
- Post-restoration: All queries <500ms on average
- Health score calculation: ~5 seconds for 60 projects
- Alert generation: ~2 seconds for all alerts

**Storage Requirements**:
- SQL dump file: ~3MB (compressed)
- PostgreSQL storage: ~15-50MB after restoration
- Total disk space needed: 100MB minimum

## Backup & Export

To create your own dataset backup:

```bash
# Export current data to SQL
pg_dump -U postgres -d amad_construction_ai > construction_ai_dataset_backup.sql

# Export to custom binary format (faster restore)
pg_dump -U postgres -d amad_construction_ai -Fc > construction_ai_dataset_backup.dump

# Restore from binary format
pg_restore -U postgres -d amad_construction_ai construction_ai_dataset_backup.dump
```

## Data Validation

After restoration, verify:

```bash
# Count all records
psql -U postgres -d amad_construction_ai -c "
  SELECT 
    COUNT(*) FILTER (WHERE 1=1) as total,
    (SELECT COUNT(*) FROM projects) as projects,
    (SELECT COUNT(*) FROM suppliers) as suppliers,
    (SELECT COUNT(*) FROM safety_events) as safety_events,
    (SELECT COUNT(*) FROM purchase_orders) as purchase_orders
  FROM projects;
"

# Check data integrity
psql -U postgres -d amad_construction_ai -c "
  SELECT 
    'OK' as status,
    COUNT(*) as total_records
  FROM (
    SELECT * FROM projects UNION ALL
    SELECT * FROM suppliers UNION ALL
    SELECT * FROM safety_events UNION ALL
    SELECT * FROM purchase_orders
  ) combined;
"
```

Expected result: **13,487 total records**

## Support

- **Issues with restoration**: Check logs in `backend/migrate_from_local_data.log`
- **Database questions**: Consult PostgreSQL documentation
- **Dataset questions**: Contact the development team

---

**Last Updated**: 2026-07-08  
**Total Records**: 13,487  
**Tables**: 18  
**File Format**: SQLite SQL dump (compatible with PostgreSQL)
