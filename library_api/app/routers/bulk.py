# app/routers/bulk.py  (FINAL VERSION — SAFE + LOGGED)

from fastapi import APIRouter, HTTPException
from app.database import get_connection

router = APIRouter(prefix="/bulk", tags=["bulk"])


@router.post("/status-update")
def bulk_status_update(old_status: str, new_status: str, changed_by: str = "system"):
    conn = None
    cursor = None
    try:
        # basic lifecycle guard
        if old_status == new_status:
            raise HTTPException(status_code=400, detail="Invalid transition")

        conn = get_connection()
        cursor = conn.cursor()

        # insert new audit rows
        cursor.execute(
            """
            INSERT INTO public.status_audit
            (accession_no, old_status, new_status, changed_by, changed_at)
            SELECT accession_no, %s, %s, %s, NOW()
            FROM public.status_audit
            WHERE new_status = %s
            RETURNING accession_no
            """,
            (old_status, new_status, changed_by, old_status),
        )

        affected_rows = cursor.fetchall()
        affected_count = len(affected_rows)

        # activity log auto-write
        if affected_count > 0:
            cursor.execute(
                """
                INSERT INTO public.activity_log
                (user_id, action, entity, entity_id, details, timestamp)
                VALUES
                (%s, %s, %s, %s, %s, NOW())
                """,
                (
                    None,
                    "BULK_STATUS_UPDATE",
                    "status_audit",
                    None,
                    f"{old_status} -> {new_status} | rows={affected_count}",
                ),
            )

        conn.commit()

        return {
            "updated_rows": affected_count,
            "transition": f"{old_status}->{new_status}",
        }

    except HTTPException:
        raise

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
