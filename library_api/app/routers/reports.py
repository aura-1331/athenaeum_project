from fastapi import APIRouter, Depends, HTTPException, Request, Query
from app.auth import get_current_user, require_role
from app.database import get_connection
from app.audit_utils import audit_action

router = APIRouter(prefix="/reports", tags=["reports"])


# ============================================================
# ACCESSIONS REPORT
# ============================================================

@router.get(
    "/accessions",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))],
)
@audit_action("VIEW_ACCESSIONS_REPORT")
def accessions_report(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=1000000),
    current_user: dict = Depends(get_current_user),
):
    conn = get_connection(request=request)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT COUNT(*)
            FROM public.status_audit
        """)
        total = cur.fetchone()[0]

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
                "accession_no": row[0],
                "old_status": row[1],
                "new_status": row[2],
                "changed_by": row[3],
                "changed_at": row[4],
            }
            for row in rows
        ]

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        print(f"Accessions report failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Unable to load the accessions report.",
        ) from exc
    finally:
        cur.close()
        conn.close()


# ============================================================
# ACTIVITY REPORT
# ============================================================

@router.get(
    "/activity",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))],
)
@audit_action("VIEW_ACTIVITY_REPORT")
def activity_report(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=1000000),
    current_user: dict = Depends(get_current_user),
):
    conn = get_connection(request=request)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT COUNT(*)
            FROM public.activity_log
        """)
        total = cur.fetchone()[0]

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
                "log_id": row[0],
                "user_id": row[1],
                "action": row[2],
                "entity": row[3],
                "entity_id": row[4],
                "details": row[5],
                "timestamp": row[6],
            }
            for row in rows
        ]

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        print(f"Activity report failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Unable to load the activity report.",
        ) from exc
    finally:
        cur.close()
        conn.close()
