from fastapi import APIRouter, HTTPException
from app.database import get_connection

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/accessions")
def accessions_report(limit: int = 50, offset: int = 0):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
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

        data = []
        for r in rows:
            data.append(
                {
                    "accession_no": r[0],
                    "old_status": r[1],
                    "new_status": r[2],
                    "changed_by": r[3],
                    "changed_at": r[4],
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


@router.get("/activity")
def activity_report(limit: int = 50, offset: int = 0):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM public.activity_log
            ORDER BY 1 DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )

        rows = cursor.fetchall()

        data = []
        for r in rows:
            data.append(list(r))

        return data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
