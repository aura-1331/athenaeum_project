# ATHENAEUM DATABASE MIGRATION WORKFLOW GUIDE

## Overview
Athenaeum now uses:
- Render → application deployment
- Neon → production PostgreSQL database
- Local PostgreSQL → development database
- Alembic → schema migration automation

--------------------------------------------------
ARCHITECTURE FLOW
--------------------------------------------------
LOCAL MACHINE
→ code development
→ migration creation
→ local testing

RENDER
→ pulls latest GitHub code
→ installs dependencies
→ runs Alembic migrations automatically
→ starts backend

NEON
→ receives automatic production schema updates

--------------------------------------------------
LOCAL DATABASE
--------------------------------------------------
Your local .env uses local PostgreSQL.

Used for:
- local testing
- local migrations
- development verification

--------------------------------------------------
PRODUCTION DATABASE
--------------------------------------------------
Render environment variable:
DATABASE_URL = Neon URL

Used for:
- production deployment
- automatic production migrations

--------------------------------------------------
WHEN ADDING NEW TABLES/COLUMNS/INDEXES
--------------------------------------------------
1. Create migration file:
alembic revision -m "add digital assets table"

2. Edit migration file

3. Run locally:
alembic upgrade head

4. Test locally

5. Git push

Render automatically runs:
alembic upgrade head

Neon updates automatically.

--------------------------------------------------
WHEN TO USE PSQL MANUALLY
--------------------------------------------------
Allowed only for:
- debugging
- deleting bad records
- emergency fixes
- manual inspections
- one-time cleanup

--------------------------------------------------
WHAT NOT TO DO
--------------------------------------------------
DO NOT manually create tables in psql.

Wrong:
CREATE TABLE xyz (...)

Why bad:
- Alembic won’t know
- duplicate table errors later
- production mismatch

--------------------------------------------------
IF YOU ACCIDENTALLY CREATE TABLE MANUALLY
--------------------------------------------------
Fix:
alembic stamp head

--------------------------------------------------
RENDER AUTOMATION
--------------------------------------------------
Build command:
pip install -r requirements.txt && alembic upgrade head

Start command:
uvicorn app.main:app --host 0.0.0.0 --port $PORT

--------------------------------------------------
CURRENT RULE
--------------------------------------------------
Schema changes → Alembic
Data changes → psql
Deployment → Git push

--------------------------------------------------
STATUS
--------------------------------------------------
FULLY AUTOMATED DATABASE DEPLOYMENT ENABLED
