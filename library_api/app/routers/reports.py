from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth import get_current_user, require_role  # 1. Import require_role
from app.database import get_connection
from app.audit_utils import audit_action

router = APIRouter(prefix="/reports", tags=["reports"])

@audit_action("VIEW_ACCESSIONS_REPORT")
@router.get("/accessions", dependencies=[Depends(require_role(["The Keeper", "The Chief"]))]) # 2. Add Security Guard
def accessions_report(
    limit: int = 50, 
    offset: int = 0, 
    request: Request = None, 
    current_user: dict = Depends(get_current_user)
):
    # Manual 'if current_user["role"]...' check removed
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT accession_no, old_status, new_status, changed_by, changed_at
            FROM public.status_audit
            ORDER BY changed_at DESC LIMIT %s OFFSET %s
        """, (limit, offset))
        
        return [
            {
                "accession_no": r[0], "old_status": r[1], 
                "new_status": r[2], "changed_by": r[3], "changed_at": r[4]
            } for r in cur.fetchall()
        ]
    finally:
        cur.close(); conn.close()

@audit_action("VIEW_ACTIVITY_REPORT")
@router.get("/activity", dependencies=[Depends(require_role(["The Keeper", "The Chief"]))]) # 2. Add Security Guard
def activity_report(
    limit: int = 50, 
    offset: int = 0, 
    request: Request = None, 
    current_user: dict = Depends(get_current_user)
):
    # Manual 'if current_user["role"]...' check removed
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT * FROM public.activity_log
            ORDER BY 1 DESC LIMIT %s OFFSET %s
        """, (limit, offset))
        return [list(r) for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()