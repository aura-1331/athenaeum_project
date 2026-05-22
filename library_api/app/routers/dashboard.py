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

        # Total accessions
        cursor.execute("""
            SELECT COUNT(*) 
            FROM public.items 
            WHERE is_deleted = FALSE
        """)
        total_accessions = cursor.fetchone()[0]

        # Total approved books
        cursor.execute("""
            SELECT COUNT(*) 
            FROM public.works 
            WHERE status = 'APPROVED'
        """)
        total_books = cursor.fetchone()[0]

        # Issued books
        cursor.execute("""
            SELECT COUNT(*) 
            FROM public.items
            WHERE availability_status = 'ISSUED'
            AND is_deleted = FALSE
        """)
        total_issued = cursor.fetchone()[0]

        # Missing books
        cursor.execute("""
            SELECT COUNT(*) 
            FROM public.items
            WHERE availability_status = 'MISSING'
            AND is_deleted = FALSE
        """)
        missing_items = cursor.fetchone()[0]

        # Damaged books
        cursor.execute("""
            SELECT COUNT(*) 
            FROM public.items
            WHERE availability_status = 'DAMAGED'
            AND is_deleted = FALSE
        """)
        damaged_items = cursor.fetchone()[0]

        
        # ---------------- RECENT ACTIVITY ----------------
        recent_activity = []

        try:
            cursor.execute("""
                SELECT id, accession_no, old_status, new_status, changed_at
                FROM public.status_audit
                ORDER BY changed_at DESC
                LIMIT 5
            """)

            rows = cursor.fetchall()

            for r in rows:
                dt = r[4]

                recent_activity.append({
                    "id": r[0],
                    "accession_no": r[1],
                    "old_status": r[2],
                    "new_status": r[3],
                    "changed_at": dt.isoformat() if hasattr(dt, "isoformat") else str(dt)
                })

        except Exception as table_err:
            print(f"⚠️ Activity Table Error: {table_err}")
            recent_activity = []


        # ---------------- CATEGORY STATS ----------------
        
        # ---------------- CATEGORY STATS ----------------
        cursor.execute("""
            SELECT 
                COALESCE(w.category, 'Uncategorized') as category,
                COUNT(*) as count
            FROM public.items i
            LEFT JOIN public.works w ON i.work_id = w.work_id
            WHERE i.is_deleted = FALSE
            GROUP BY w.category
            ORDER BY count DESC
            LIMIT 5
        """)

        category_rows = cursor.fetchall()
        categories = [{"category": row[0], "count": row[1]} for row in category_rows]

        # ---------------- LANGUAGE STATS ----------------
        cursor.execute("""
            SELECT 
                COALESCE(w.language, 'Unknown') as language,
                COUNT(*) as count
            FROM public.items i
            LEFT JOIN public.works w ON i.work_id = w.work_id
            WHERE i.is_deleted = FALSE
            GROUP BY w.language
            ORDER BY count DESC
            LIMIT 5
        """)

        language_rows = cursor.fetchall()
        languages = [{"language": row[0], "count": row[1]} for row in language_rows]

        # ---------------- RECENT ADDITIONS ----------------
        cursor.execute("""
            SELECT 
                i.accession_no,
                w.title,
                w.author,
                i.created_at
            FROM public.items i
            LEFT JOIN public.works w ON i.work_id = w.work_id
            WHERE i.is_deleted = FALSE
            ORDER BY i.created_at DESC
            LIMIT 5
        """)

        recent_rows = cursor.fetchall()
        recent_additions = []
        for row in recent_rows:
            recent_additions.append({
                "accession_no": row[0],
                "title": row[1],
                "author": row[2],
                "created_at": row[3].isoformat() if row[3] else None
            })

        # ---------------- FINAL RESPONSE ----------------
        return {
            "total_accessions": int(total_accessions),
            "total_books": int(total_books),
            "total_issued": int(total_issued),
            "missing_items": int(missing_items),
            "damaged_items": int(damaged_items),
            "recent_activity": recent_activity,
            "categories": categories,
            "recent_additions": recent_additions,
            "languages": languages
        }

    except Exception as e:
        print(f"❌ CRITICAL DASHBOARD ERROR: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Database Sync Error"
        )

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()