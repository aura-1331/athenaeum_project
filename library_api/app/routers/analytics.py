# app/routers/analytics.py
from fastapi import APIRouter, HTTPException
from app.database import get_connection

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/status-transitions")
def status_transition_counts():
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

        data = []
        for r in rows:
            data.append(
                {
                    "old_status": r[0],
                    "new_status": r[1],
                    "count": r[2],
                }
            )

        return data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
