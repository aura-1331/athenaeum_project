from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth import get_current_user, require_role
from app.database import get_connection
from app.audit_utils import audit_action

router = APIRouter(prefix="/reports", tags=["reports"])


# ============================================================
# ACCESSIONS REPORT
# ============================================================

@audit_action("VIEW_ACCESSIONS_REPORT")
@router.get(
    "/accessions",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))]
)
def accessions_report(
    limit: int = 50,
    offset: int = 0,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100."
        )

    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="Offset cannot be negative."
        )

    conn = get_connection(request=request)
    cur = conn.cursor()

    try:
        # Total number of records
        cur.execute("""
            SELECT COUNT(*)
            FROM public.status_audit
        """)
        total = cur.fetchone()[0]

        # Requested page
        cur.execute("""
            SELECT
                accession_no,
                old_status,
                new_status,
                changed_by,
                changed_at
            FROM public.status_audit
            ORDER BY changed_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))

        rows = cur.fetchall()

        items = [
            {
                "accession_no": r[0],
                "old_status": r[1],
                "new_status": r[2],
                "changed_by": r[3],
                "changed_at": r[4]
            }
            for r in rows
        ]

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    finally:
        cur.close()
        conn.close()


# ============================================================
# ACTIVITY REPORT
# ============================================================

@audit_action("VIEW_ACTIVITY_REPORT")
@router.get(
    "/activity",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))]
)
def activity_report(
    limit: int = 50,
    offset: int = 0,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100."
        )

    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="Offset cannot be negative."
        )

    conn = get_connection(request=request)
    cur = conn.cursor()

    try:
        # Total number of records
        cur.execute("""
            SELECT COUNT(*)
            FROM public.activity_log
        """)
        total = cur.fetchone()[0]

        # Requested page
        cur.execute("""
            SELECT
                log_id,
                user_id,
                action,
                entity,
                entity_id,
                details,
                timestamp
            FROM public.activity_log
            ORDER BY timestamp DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))

        rows = cur.fetchall()

        items = [
            {
                "log_id": r[0],
                "user_id": r[1],
                "action": r[2],
                "entity": r[3],
                "entity_id": r[4],
                "details": r[5],
                "timestamp": r[6]
            }
            for r in rows
        ]

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    finally:
        cur.close()
        conn.close()