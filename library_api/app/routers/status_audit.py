from fastapi import APIRouter, HTTPException
from app.database import get_connection

router = APIRouter(prefix="/status_audit", tags=["status_audit"])


@router.get("/")
def list_status_audit(limit: int = 50, offset: int = 0):

    if limit < 1 or limit > 500:
        limit = 50

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                accession_no,
                old_status,
                new_status,
                changed_by,
                changed_at
            FROM public.status_audit
            ORDER BY changed_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )

        rows = cursor.fetchall()

        return [
            {
                "id": r[0],
                "accession_no": r[1],
                "old_status": r[2],
                "new_status": r[3],
                "changed_by": r[4],
                "changed_at": r[5],
            }
            for r in rows
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()