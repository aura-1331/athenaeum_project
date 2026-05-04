# Athenaeum Project Recovery Notes

## What happened
Local project files were deleted accidentally.

## Recovery steps completed

### Code Recovery
- Re-cloned/restored project from GitHub
- Backend restored
- Frontend restored

---

## Database Recovery
PostgreSQL database survived.

Database:
library_catalogue

Verified tables:
- items
- works
- loans
- fines
- users
- activity_log
- status_audit
- etc.

---

## Important schema update
Old table:
books

Renamed to:
books_legacy_backup

Reason:
Old accession format:
LIB-2026-*

Current active accession format:
ML-*
EN-*

Current active tables:
- items → physical inventory
- works → bibliographic metadata

---

## Bugs fixed

### 1. print router conflict
Problem:
print.py router conflicted with Python print()

Fix:
Renamed import alias:

print → print_router

---

### 2. Frontend redirect issue
Problem:
App redirected to /catalogue without login

Fix:
Changed:

/ → /catalogue

to:

/ → /login

---

### 3. operations_service fix
Problem:
Referenced dead table:
catalogue

Fix:
Updated to:

public.items

---

### 4. Missing stored procedure
Problem:
sp_execute_status_transition did not exist

Fix:
Replaced procedure logic with direct status updates

Supported:
- LOST
- DAMAGED
- OVERRIDE

Issue/Return handled in:
circulation.py

---

## Database backup

Created:
library_catalogue_backup.sql

Location:
library_api/

Keep external copy in:
- Google Drive
- External HDD
- Cloud storage

---

## Recovery commands

Backend:
python -m uvicorn app.main:app --reload

Frontend:
npm run tauri dev

Database backup:
pg_dump -U postgres library_catalogue > library_catalogue_backup.sql