# RESTORE ORIGINAL POSTGRESQL DATABASE FROM REPLIT TO WINDOWS

## STEP 1: CREATE DATABASE DUMP IN REPLIT

**Environment:** In Replit shell/terminal

```bash
# Get PostgreSQL credentials (check Replit's database connection URL)
# Format is typically: postgresql://username:password@host:port/dbname

# Create the dump file
pg_dump -h <host> -U <username> -d <database_name> -F custom -f ~/construction_ai_dump.tar

# Example (if using Replit's built-in PostgreSQL):
pg_dump -h localhost -U postgres -d amad_construction_ai -F custom -f ~/construction_ai_dump.tar

# Alternative (if password-protected):
PGPASSWORD='your_password' pg_dump -h localhost -U postgres -d amad_construction_ai -F custom -f ~/construction_ai_dump.tar
```

**Notes:**
- `-F custom` creates a binary dump file (more efficient, supports parallel restore)
- Saves to home directory as `construction_ai_dump.tar`
- This dump includes all tables, sequences, indexes, constraints, data


## STEP 2: DOWNLOAD DUMP FROM REPLIT

**In Replit:**
1. Click **Files** panel on the left
2. Navigate to home directory (should see `construction_ai_dump.tar`)
3. Right-click → **Download**
4. Save to local machine: `C:\Users\ASUS\Downloads\construction_ai_dump.tar`


## STEP 3: PREPARE LOCAL DATABASE

**On Windows (PowerShell):**

```powershell
# Option A: Keep current placeholder data (safe, for testing)
# Skip this section - restore to separate database first

# Option B: Drop and recreate (if you want to replace immediately)
$env:PGPASSWORD = 'Admin123!'
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS amad_construction_ai;"
psql -h localhost -U postgres -c "CREATE DATABASE amad_construction_ai;"
```

**Recommendation:** Do Option A first - test restore to temporary database before overwriting local.


## STEP 4: RESTORE TO LOCAL DATABASE (SAFE TEST FIRST)

**Create temporary database for testing:**

```powershell
$env:PGPASSWORD = 'Admin123!'

# Create test database
psql -h localhost -U postgres -c "CREATE DATABASE amad_construction_ai_restored;"

# Restore the dump
pg_restore -h localhost -U postgres -d amad_construction_ai_restored `
  -v `
  C:\Users\ASUS\Downloads\construction_ai_dump.tar
```

**Full restore (with progress output):**
```powershell
$env:PGPASSWORD = 'Admin123!'
pg_restore -h localhost -U postgres -d amad_construction_ai_restored `
  --verbose --no-owner --no-privileges `
  C:\Users\ASUS\Downloads\construction_ai_dump.tar
```

**Wait for completion** - may take 2-5 minutes depending on data size.


## STEP 5: VERIFY RESTORED DATA CONTENT

**Check table row counts:**

```powershell
$env:PGPASSWORD = 'Admin123!'

$query = @"
SELECT 
    schemaname,
    tablename,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name=tablename) as count
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;
"@

psql -h localhost -U postgres -d amad_construction_ai_restored -c $query
```

**Sample project names (verify realistic data, not "Construction Project 1"):**

```powershell
$env:PGPASSWORD = 'Admin123!'

psql -h localhost -U postgres -d amad_construction_ai_restored `
  -c "SELECT id, project_name, project_code FROM projects LIMIT 5;"
```

**Expected output (ORIGINAL data):**
```
 id |        project_name         | project_code
----+-----------------------------+---------------
  1 | [Real project name]         | PRJ-XXXX
  2 | [Real project name]         | PRJ-XXXX
```

**Current output (PLACEHOLDER data - means dump failed):**
```
 id |        project_name         | project_code
----+-----------------------------+---------------
  1 | Construction Project 1      | PRJ-0001
  2 | Construction Project 2      | PRJ-0002
```

**Check suppliers (realistic names):**

```powershell
$env:PGPASSWORD = 'Admin123!'

psql -h localhost -U postgres -d amad_construction_ai_restored `
  -c "SELECT id, supplier_name, category FROM suppliers LIMIT 5;"
```


## STEP 6: VERIFY ADMIN LOGIN EXISTS IN RESTORED DATABASE

```powershell
$env:PGPASSWORD = 'Admin123!'

psql -h localhost -U postgres -d amad_construction_ai_restored `
  -c "SELECT id, email, is_active FROM user_accounts WHERE email='admin@construction.ai';"
```

**Expected result:**
- If admin exists: Restore completed successfully (login may work as-is)
- If admin doesn't exist: Will need to recreate (see Step 7)


## STEP 7: HANDLE ADMIN LOGIN AFTER RESTORE

**Option A: Preserve existing admin user (if in dump)**
- If Step 6 shows admin exists, login should work with credentials from Replit
- Test: `admin@construction.ai` / password from Replit

**Option B: Recreate admin user for local development**

```powershell
# From backend directory
cd C:\Users\ASUS\Downloads\amad-construction-ai-platform-main\amad-construction-ai-platform-main\backend

# Set database to restored version
$env:DATABASE_URL = 'postgresql://postgres:Admin123!@localhost:5432/amad_construction_ai_restored'

# Recreate admin user script
python -c @"
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))

from app.database import SessionLocal
from app.models.auth import UserAccount, Organization
from app.core.security import get_password_hash

db = SessionLocal()

# Check if admin exists
admin = db.query(UserAccount).filter(UserAccount.email=='admin@construction.ai').first()

if not admin:
    # Create admin org
    org = Organization(name='Admin Organization', tier='enterprise')
    db.add(org)
    db.flush()
    
    # Create admin user
    admin = UserAccount(
        email='admin@construction.ai',
        password_hash=get_password_hash('Admin123!'),
        is_active=True,
        is_admin=True,
        organization_id=org.id
    )
    db.add(admin)
    db.commit()
    print('✓ Admin user created')
else:
    print(f'✓ Admin already exists: {admin.email}')

db.close()
"@
```


## STEP 8: SWITCH TO RESTORED DATABASE (AFTER VERIFICATION)

**Only after confirming data is correct in Step 5:**

```powershell
$env:PGPASSWORD = 'Admin123!'

# Backup current placeholder database (optional)
pg_dump -h localhost -U postgres -d amad_construction_ai -F custom `
  -f C:\Users\ASUS\Downloads\amad_construction_ai_placeholder_backup.tar

# Drop current placeholder database
psql -h localhost -U postgres -c "DROP DATABASE amad_construction_ai;"

# Rename restored database
psql -h localhost -U postgres `
  -c "ALTER DATABASE amad_construction_ai_restored RENAME TO amad_construction_ai;"
```

**Verify switch:**
```powershell
$env:PGPASSWORD = 'Admin123!'
psql -h localhost -U postgres -l | findstr "amad_construction_ai"
```


## STEP 9: TEST APPLICATION WITH RESTORED DATA

```powershell
# Terminal 1: Start backend (from backend directory)
cd backend
python run_server.py

# Terminal 2: Start frontend (from artifacts/web)
cd artifacts\web
pnpm dev

# Browser: http://localhost:5173
# Login: admin@construction.ai / [password from Replit]
# Verify: Dashboard shows original data (not placeholder projects)
```


## TROUBLESHOOTING

**Error: "pg_dump: command not found"**
- PostgreSQL tools not in PATH
- Install PostgreSQL on Windows or add to PATH

**Error: "FATAL: password authentication failed"**
- Check PGPASSWORD environment variable
- Verify credentials match local PostgreSQL setup (postgres:Admin123!)

**Error: "database amad_construction_ai already exists"**
- Drop it first: `psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS amad_construction_ai;"`

**Dump file is small (< 1MB) or restore completes instantly**
- Likely created empty dump
- Verify Replit database actually has data
- Check if PostgreSQL is running in Replit
- Re-run pg_dump with verbose: `pg_dump -v ...`

**Restored data still shows "Construction Project 1"**
- Dump may have been created from wrong database
- Verify you dumped from `amad_construction_ai` on Replit, not local
- Check Replit database connection details


## SUMMARY CHECKLIST

- [ ] 1. Create dump in Replit: `pg_dump ... -f ~/construction_ai_dump.tar`
- [ ] 2. Download `construction_ai_dump.tar` from Replit Files
- [ ] 3. Create test database: `CREATE DATABASE amad_construction_ai_restored;`
- [ ] 4. Restore dump: `pg_restore ... -d amad_construction_ai_restored ...`
- [ ] 5. Verify data content: `SELECT * FROM projects LIMIT 5;` (should show realistic names)
- [ ] 6. Check admin user exists in dump
- [ ] 7. If satisfied, drop old DB and rename restored: `ALTER DATABASE ... RENAME ...`
- [ ] 8. Test application with restored data
