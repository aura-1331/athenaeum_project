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
              AND w.status = 'NEEDS_CORRECTION'
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
def dashboard_summary(request: Request):
    conn = None
    cursor = None

    try:
        # Use the database connection already used by this project
        conn = get_connection(request=request)
        cursor = conn.cursor()

        # Total approved works
        cursor.execute("""
            SELECT COUNT(*)
            FROM public.works
            WHERE UPPER(TRIM(status)) = 'APPROVED'
        """)
        total_works = cursor.fetchone()[0] or 0

        
        # Item and accession metrics
        cursor.execute("""
            SELECT
                COUNT(*),
                COUNT(accession_no),
                COUNT(*) FILTER (
                    WHERE UPPER(TRIM(COALESCE(availability_status, ''))) = 'ISSUED'
                ),
                COUNT(*) FILTER (
                    WHERE UPPER(TRIM(COALESCE(availability_status, ''))) = 'MISSING'
                ),
                COUNT(*) FILTER (
                    WHERE UPPER(TRIM(COALESCE(availability_status, ''))) = 'DAMAGED'
                )
            FROM public.items
        """)
        item_row = cursor.fetchone()

        total_items = item_row[0] or 0
        total_accessions = item_row[1] or 0
        total_issued = item_row[2] or 0
        missing_items = item_row[3] or 0
        damaged_items = item_row[4] or 0


        total_books = total_works

        # Language breakdown
        cursor.execute("""
            SELECT
                COALESCE(NULLIF(TRIM(language), ''), 'Unspecified'),
                COUNT(*)
            FROM public.works
            WHERE UPPER(TRIM(status)) IN ('APPROVED', 'PENDING')
            GROUP BY COALESCE(NULLIF(TRIM(language), ''), 'Unspecified')
            ORDER BY COUNT(*) DESC
        """)
        languages = [
            {"language": row[0], "count": int(row[1])}
            for row in cursor.fetchall()
        ]

        # Category breakdown
        cursor.execute("""
            SELECT
                COALESCE(NULLIF(TRIM(category), ''), 'Uncategorised'),
                COUNT(*)
            FROM public.works
            WHERE UPPER(TRIM(status)) IN ('APPROVED', 'PENDING')
            GROUP BY COALESCE(NULLIF(TRIM(category), ''), 'Uncategorised')
            ORDER BY COUNT(*) DESC
        """)
        categories = [
            {"category": row[0], "count": int(row[1])}
            for row in cursor.fetchall()
        ]

        # Genre breakdown
        cursor.execute("""
            SELECT
                COALESCE(NULLIF(TRIM(genre), ''), 'Unspecified'),
                COUNT(*)
            FROM public.works
            WHERE UPPER(TRIM(status)) IN ('APPROVED', 'PENDING')
            GROUP BY COALESCE(NULLIF(TRIM(genre), ''), 'Unspecified')
            ORDER BY COUNT(*) DESC
        """)
        genres = [
            {"genre": row[0], "count": int(row[1])}
            for row in cursor.fetchall()
        ]

        # Recent activity
        recent_activity = []
        try:
            cursor.execute("""
                SELECT *
                FROM public.status_audit
                ORDER BY 1 DESC
                LIMIT 5
            """)
            recent_activity = cursor.fetchall()
        except Exception as e:
            print(f"Recent activity lookup failed: {e}")
            try:
                conn.rollback()
            except Exception:
                pass

        return {
            "total_works": total_works,
            "total_items": total_items,
            "total_accessions": total_accessions,
            "total_books": total_books,
            "total_issued": total_issued,
            "missing_items": missing_items,
            "damaged_items": damaged_items,
            "recent_activity": recent_activity,
            "languages": languages,
            "categories": categories,
            "genres": genres,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
        status_code=500,
        detail="Unable to load dashboard summary."
    )

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
