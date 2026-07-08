# AMAD Construction AI Platform

A comprehensive AI-powered construction operations intelligence platform featuring real-time project monitoring, safety management, procurement optimization, and executive intelligence dashboards.

## Features

- **Project Management**: Track 60+ construction projects with real-time health scoring
- **Executive Dashboard**: Portfolio-level insights, risk summaries, and KPI monitoring
- **Health Scoring Engine**: Deterministic project health calculations based on schedule, safety, procurement, and quality metrics
- **Smart Alerts**: 1,000+ rule-based operational alerts with severity classification
- **Safety Management**: Safety event tracking, NCR management, and risk assessment
- **Procurement**: Purchase order tracking, supplier management, and delivery status monitoring
- **Site Reports**: Daily activity logs, meeting minutes, and decision tracking
- **Role-Based Access Control**: Admin, Executive, Project Manager, Site Engineer, Safety Officer roles
- **Cross-Platform Support**: Fully functional on Windows, macOS, and Linux

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115.7
- **Server**: Uvicorn 0.34.0
- **ORM**: SQLAlchemy 2.0.36
- **Database**: PostgreSQL 15.x
- **Migrations**: Alembic
- **Authentication**: JWT (python-jose) + bcrypt password hashing
- **Language**: Python 3.12.2

### Frontend
- **Framework**: React 19.1.0
- **Build Tool**: Vite 7.3.5
- **Language**: TypeScript
- **Package Manager**: pnpm 11.10.0
- **UI Library**: Modern CSS-in-JS (styled with design tokens)

### Database
- **Primary**: PostgreSQL 15.x (15,000+ rows of production data)
- **Cache**: Redis (optional)
- **Migrations**: Alembic for schema management

## Local Setup (Windows 11)

### Prerequisites
- Python 3.12+ (https://www.python.org/downloads/)
- Node.js 24.x+ (https://nodejs.org/)
- PostgreSQL 15+ (https://www.postgresql.org/download/windows/)
- pnpm 11.x+ (`npm install -g pnpm`)
- Git

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd amad-construction-ai-platform-main
```

### Step 2: Set Up PostgreSQL Database

```bash
# Start PostgreSQL service (Windows)
# Or use: net start postgresql-x64-15

# Create database
createdb -U postgres -E UTF8 amad_construction_ai

# Create user (if needed)
# psql -U postgres -c "CREATE USER construction_user WITH PASSWORD 'your_password';"
```

### Step 3: Backend Setup

```bash
# Navigate to backend
cd backend

# Create .env from template
copy .env.example .env

# Edit .env and set:
# - DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/amad_construction_ai
# - SESSION_SECRET=<generate with: python -c "import secrets; print(secrets.token_hex(32))">

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed initial user data (optional)
python -m scripts.seed_users
```

### Step 4: Restore Production Dataset (Optional)

See [DATA_SETUP.md](DATA_SETUP.md) for detailed instructions on restoring the production dataset.

```bash
# After database is set up, restore data:
python migrate_from_local_data.py
```

### Step 5: Start Backend

```bash
# From backend directory (with .venv activated)
python run_server.py

# Server will run on http://127.0.0.1:8000
# API docs: http://127.0.0.1:8000/api/docs
```

### Step 6: Frontend Setup

```bash
# In new terminal, from project root
cd artifacts/web

# Create .env (if needed)
copy .env.example .env

# Install dependencies
pnpm install

# Start development server
pnpm dev

# Frontend will run on http://localhost:5174
```

## Default Login Credentials

After setup and seeding, use:

**Email**: `admin@construction.ai`  
**Password**: `Admin123!`

> ⚠️ **Security Note**: Change these credentials before production deployment!

## Project Structure

```
.
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── main.py            # FastAPI app entrypoint
│   │   ├── config.py          # Settings and configuration
│   │   ├── database.py        # Database connection
│   │   ├── models/            # SQLAlchemy models (33 models, 27 tables)
│   │   ├── api/v1/            # REST API endpoints
│   │   ├── ai/                # Health scoring and analytics
│   │   ├── core/              # Auth, security, dependencies
│   │   └── schemas/           # Pydantic validation schemas
│   ├── alembic/               # Database migrations
│   ├── data/                  # Data files (SQL dumps for restoration)
│   ├── .env.example           # Environment template
│   ├── requirements.txt       # Python dependencies
│   └── run_server.py          # Server launcher
│
├── artifacts/web/             # React/Vite frontend application
│   ├── src/
│   │   ├── App.tsx            # Main React component
│   │   ├── pages/             # Page components
│   │   ├── components/        # Reusable components
│   │   ├── services/          # API client
│   │   └── hooks/             # React hooks
│   ├── vite.config.ts         # Vite configuration
│   ├── tsconfig.json          # TypeScript config
│   └── package.json
│
├── lib/                       # Shared libraries
│   ├── api-client-react/      # React API client
│   ├── api-spec/              # OpenAPI specification
│   ├── api-zod/               # Zod validation schemas
│   ├── brand-tokens/          # Design tokens
│   └── db/                    # Database utilities
│
├── docs/                      # Documentation
├── scripts/                   # Monorepo scripts
└── README.md                  # This file
```

## Database Schema

The application uses 27 PostgreSQL tables across 12 data models:

**Core**: Projects, Organizations, Users, ProjectMemberships  
**Operations**: Meetings, Documents, MeetingActionItems  
**Safety**: SafetyEvents, NCRs  
**Procurement**: PurchaseRequests, PurchaseOrders, Suppliers, Subcontractors  
**Finance**: Claims, ChangeOrders  
**Analytics**: ProjectRisks, HealthScores, AIConversations

See `backend/app/models/` for detailed schema definitions.

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Current user info

### Dashboard & Reports
- `GET /api/v1/dashboard/summary` - Dashboard metrics
- `GET /api/v1/reports/executive-weekly` - Executive weekly report
- `GET /api/v1/alerts` - List operational alerts
- `GET /api/v1/alerts/summary` - Alert statistics
- `GET /api/v1/executive` - Executive intelligence

### Projects
- `GET /api/v1/projects` - List all projects
- `GET /api/v1/projects/{id}` - Project details
- `GET /api/v1/projects/health-scores` - Project health metrics

### Operations
- `GET /api/v1/safety-events` - Safety incidents
- `GET /api/v1/ncrs` - Non-conformance reports
- `GET /api/v1/purchase-orders` - Procurement orders
- `GET /api/v1/suppliers` - Supplier directory

See `http://127.0.0.1:8000/api/docs` for full API documentation.

## Health Scoring Algorithm

Projects are scored 0-100 based on weighted penalties:

| Factor | Max Penalty | Details |
|--------|------------|---------|
| Schedule | 35 | Delayed status, overdue days |
| Safety | 25 | High/critical events, counts |
| Quality (NCR) | 20 | Open non-conformances |
| Procurement | 15 | Late purchase orders |
| Risk | 10 | Project risk assessments |

**Score Levels**:
- 80-100: Excellent
- 60-79: Good
- 40-59: At Risk
- 0-39: Critical

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd artifacts/web
pnpm test
```

### Code Formatting

```bash
# Backend
cd backend
black app/ tests/
isort app/ tests/

# Frontend
cd artifacts/web
pnpm format
```

### Database Migrations

```bash
# Backend directory
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Troubleshooting

### Backend Won't Start
```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT version();"

# Verify .env configuration
cat backend/.env

# Check database exists
psql -U postgres -l | grep amad_construction_ai

# Run migrations
cd backend && alembic upgrade head
```

### Frontend Won't Start
```bash
# Clear node_modules and reinstall
rm -r artifacts/web/node_modules
pnpm install --force

# Check port 5174 is available
netstat -ano | findstr :5174

# Clear pnpm cache
pnpm store prune
```

### Login Issues
```bash
# Reset admin password
cd backend
python -c "from app.models.auth import UserAccount; from app.database import SessionLocal; from app.core.security import hash_password; db=SessionLocal(); u=db.query(UserAccount).filter(UserAccount.email=='admin@construction.ai').first(); u.password_hash=hash_password('Admin123!'); db.commit(); print('Password reset')"
```

## Performance Notes

- Health score calculation: ~5s for 60 projects
- Alert generation: ~2s for 1,089 alerts
- Database queries optimized with joinedload() for relationships
- Pagination supported on all list endpoints (default: 100 items, max: 500)

## Security Considerations

- ⚠️ Change default credentials before production
- ⚠️ Use strong SESSION_SECRET and SECRET_KEY values
- ⚠️ Configure ALLOWED_ORIGINS for CORS in production
- ⚠️ Use environment-specific .env files (never commit .env)
- ⚠️ Database credentials should use least-privilege user
- ⚠️ Enable HTTPS in production
- ⚠️ Implement rate limiting
- ⚠️ Regular security updates for dependencies

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes and commit: `git commit -am 'Add new feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Submit a pull request

## License

Proprietary - All rights reserved

## Support

For issues, questions, or contributions, please contact the development team.

---

**Version**: 1.0.0  
**Last Updated**: 2026-07-08  
**Platform**: Windows 11, macOS, Linux  
**Python**: 3.12+  
**Node**: 24.x+
