from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user, require_role # 1. Import dependencies
from app.database import get_connection

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/status-transitions", dependencies=[Depends(require_role(["The Chief"]))]) # 2. Add Security Guard
def status_transition_counts(current_user: dict = Depends(get_current_user)):
    # 3. Manual role check removed
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT old_status, new_status, COUNT(*)
            FROM public.status_audit
            GROUP BY old_status, new_status
            ORDER BY COUNT(*) DESC
            """
        )

        rows = cursor.fetchall()
        return [{"old_status": r[0], "new_status": r[1], "count": r[2]} for r in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()