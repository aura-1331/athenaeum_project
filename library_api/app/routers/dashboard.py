from fastapi import APIRouter, Depends, HTTPException, Request
from app.database import get_connection
from app.auth import get_current_user, require_role

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_role(["The Chief", "The Keeper"]))],
)


@router.get("/keeper-attention")
def keeper_attention(request: Request, current_user: dict = Depends(get_current_user)):
    """Return rejected submissions that require action from the current Keeper.

    An initial Item belongs to the Work submission that created it. If that Work
    is rejected, its initial Item is not a separate rejected submission and must
    not create a duplicate attention alert. Independently submitted Items can
    only belong to an already-approved Work.
    """
    if str(current_user.get("role") or "").strip().lower() != "the keeper":
        return {"rejected_works": [], "rejected_items": []}

    conn = None
    cursor = None

    try:
        conn = get_connection(request=request)
        cursor = conn.cursor()
        user_id = current_user["user_id"]

        cursor.execute("""
            SELECT
                w.work_id,
                w.title,
                w.created_at,
                w.approval_reason
            FROM public.works w
            WHERE w.proposed_by = %s
              AND w.status = 'REJECTED'
            ORDER BY w.created_at DESC, w.work_id DESC
        """, (user_id,))
        rejected_works = [
            {
                "work_id": row[0],
                "title": row[1],
                "created_at": row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2]),
                "reason": row[3],
            }
            for row in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT
                i.serial_no,
                i.accession_no,
                i.work_id,
                w.title,
                i.created_at,
                i.deletion_reason
            FROM public.items i
            INNER JOIN public.works w
                ON w.work_id = i.work_id
            WHERE i.proposed_by = %s
              AND i.availability_status = 'REJECTED'
              AND i.is_deleted = TRUE
              -- Only independently submitted Items on approved Works appear here.
              -- The initial Item follows the decision made on its parent Work.
              AND UPPER(TRIM(w.status)) = 'APPROVED'
            ORDER BY i.created_at DESC, i.serial_no DESC
        """, (user_id,))
        rejected_items = [
            {
                "serial_no": row[0],
                "accession_no": row[1],
                "work_id": row[2],
                "title": row[3],
                "created_at": row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4]),
                "reason": row[5],
            }
            for row in cursor.fetchall()
        ]

        return {
            "rejected_works": rejected_works,
            "rejected_items": rejected_items,
        }

    except Exception as e:
        print(f"Keeper attention lookup failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to load Keeper attention items."
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/summary")
def dashboard_summary(request: Request, current_user: dict = Depends(get_current_user)):
    conn = None
    cursor = None

    try:
        conn = get_connection(request=request)
        cursor = conn.cursor()

        # Official catalogue totals include approved Works only.
        # Pending Works and their automatically created initial Items remain
        # outside the accepted catalogue until the Chief approves the Work.
        cursor.execute("""
            SELECT COUNT(*)
            FROM public.works
            WHERE status = 'APPROVED'
        """)
        total_works = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM public.items i
            INNER JOIN public.works w
                ON w.work_id = i.work_id
            WHERE i.is_deleted = FALSE
              AND i.availability_status = 'AVAILABLE'
              AND UPPER(TRIM(w.status)) = 'APPROVED'
        """)
        total_items = cursor.fetchone()[0]

        # Physical-item metrics are restricted to active Items belonging to
        # approved Works so pending/rejected Work submissions cannot leak in.
        cursor.execute("""
            SELECT COUNT(*)
            FROM public.items i
            INNER JOIN public.works w
                ON w.work_id = i.work_id
            WHERE i.availability_status = 'ISSUED'
              AND i.is_deleted = FALSE
              AND UPPER(TRIM(w.status)) = 'APPROVED'
        """)
        total_issued = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM public.items i
            INNER JOIN public.works w
                ON w.work_id = i.work_id
            WHERE i.availability_status = 'MISSING'
              AND i.is_deleted = FALSE
              AND UPPER(TRIM(w.status)) = 'APPROVED'
        """)
        missing_items = cursor.fetchone()[0]

        # Count physical Items, not incident rows: one damaged Item can have
        # more than one open incident and must still count as one Item.
        cursor.execute("""
            SELECT COUNT(*)
            FROM public.items i
            INNER JOIN public.works w
                ON w.work_id = i.work_id
            WHERE i.availability_status = 'DAMAGED'
              AND i.is_deleted = FALSE
              AND UPPER(TRIM(w.status)) = 'APPROVED'
        """)
        damaged_items = cursor.fetchone()[0]

        # Language breakdown includes approved Works and pending proposals.
        cursor.execute("""
            SELECT
                COALESCE(language, 'Unknown') AS language,
                COUNT(*) AS count
            FROM public.works
            WHERE status IN ('APPROVED', 'PENDING')
            GROUP BY language
            ORDER BY count DESC
        """)
        language_rows = cursor.fetchall()
        languages = [
            {"language": row[0], "count": row[1]}
            for row in language_rows
        ]

        # Recent status activity is supplementary; the summary remains usable
        # if the legacy status_audit table is unavailable.
        recent_activity = []
        try:
            cursor.execute("""
                SELECT id, accession_no, old_status, new_status, changed_at
                FROM public.status_audit
                ORDER BY changed_at DESC
                LIMIT 5
            """)
            rows = cursor.fetchall()

            for row in rows:
                dt = row[4]
                recent_activity.append({
                    "id": row[0],
                    "accession_no": row[1],
                    "old_status": row[2],
                    "new_status": row[3],
                    "changed_at": (
                        dt.isoformat()
                        if hasattr(dt, "isoformat")
                        else str(dt)
                    ),
                })
        except Exception:
            recent_activity = []

        return {
            "total_works": int(total_works),
            "total_items": int(total_items),
            # Backward-compatible names used by older dashboard code.
            "total_accessions": int(total_works),
            "total_books": int(total_works),
            "total_issued": int(total_issued),
            "missing_items": int(missing_items),
            "damaged_items": int(damaged_items),
            "recent_activity": recent_activity,
            "languages": languages,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Dashboard summary lookup failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
