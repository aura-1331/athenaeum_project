from fastapi import APIRouter, Depends, HTTPException
from app.database import get_connection
from app.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(current_user: dict = Depends(get_current_user)):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Official Dashboard totals match the accepted catalogue.
        # Pending Works and Pending Items remain outside these totals until
        # the Chief approves them.
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
              AND w.status = 'APPROVED'
        """)
        total_items = cursor.fetchone()[0]

        # Issued / missing / damaged remain physical-item metrics.
        cursor.execute("""
            SELECT COUNT(*)
            FROM public.items
            WHERE availability_status = 'ISSUED'
              AND is_deleted = FALSE
        """)
        total_issued = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM public.items
            WHERE availability_status = 'MISSING'
              AND is_deleted = FALSE
        """)
        missing_items = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM public.items
            WHERE availability_status = 'DAMAGED'
              AND is_deleted = FALSE
        """)
        damaged_items = cursor.fetchone()[0]

        # Language breakdown for active works.
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

        # Recent status activity.
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
