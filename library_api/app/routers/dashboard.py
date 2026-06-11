from fastapi import APIRouter, Depends, HTTPException, Request
from app.database import get_connection
from app.auth import get_current_user
from app.audit_utils import audit_action  # 🛡️ Added for security logging

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@audit_action("VIEW_DASHBOARD") # 🛡️ Tracks who is viewing analytics
@router.get("/summary")
def dashboard_summary(request: Request, current_user: dict = Depends(get_current_user)):
    # Note: Added 'request: Request' so the decorator can log the user's IP/Metadata
    
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Dashboard Metrics
        queries = {
            "total_accessions": "SELECT COUNT(*) FROM public.items WHERE is_deleted = FALSE",
            "total_books": "SELECT COUNT(*) FROM public.works WHERE status = 'APPROVED'",
            "total_issued": "SELECT COUNT(*) FROM public.items WHERE availability_status = 'ISSUED' AND is_deleted = FALSE",
            "missing_items": "SELECT COUNT(*) FROM public.items WHERE availability_status = 'MISSING' AND is_deleted = FALSE",
            "damaged_items": "SELECT COUNT(*) FROM public.items WHERE availability_status = 'DAMAGED' AND is_deleted = FALSE"
        }

        results = {}
        for key, query in queries.items():
            cursor.execute(query)
            results[key] = int(cursor.fetchone()[0])

        # 2. Recent Activity
        cursor.execute("""
            SELECT id, accession_no, old_status, new_status, changed_at
            FROM public.status_audit ORDER BY changed_at DESC LIMIT 5
        """)
        recent_activity = [{
            "id": r[0], "accession_no": r[1], "old_status": r[2], 
            "new_status": r[3], "changed_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4])
        } for r in cursor.fetchall()]

        # 3. Category & Language Stats
        cursor.execute("SELECT COALESCE(w.category, 'Uncategorized'), COUNT(*) FROM public.items i LEFT JOIN public.works w ON i.work_id = w.work_id WHERE i.is_deleted = FALSE GROUP BY w.category ORDER BY COUNT(*) DESC LIMIT 5")
        categories = [{"category": row[0], "count": row[1]} for row in cursor.fetchall()]

        cursor.execute("SELECT COALESCE(w.language, 'Unknown'), COUNT(*) FROM public.items i LEFT JOIN public.works w ON i.work_id = w.work_id WHERE i.is_deleted = FALSE GROUP BY w.language ORDER BY COUNT(*) DESC LIMIT 5")
        languages = [{"language": row[0], "count": row[1]} for row in cursor.fetchall()]

        # 4. Recent Additions
        cursor.execute("SELECT i.accession_no, w.title, w.author, i.created_at FROM public.items i LEFT JOIN public.works w ON i.work_id = w.work_id WHERE i.is_deleted = FALSE ORDER BY i.created_at DESC LIMIT 5")
        recent_additions = [{"accession_no": row[0], "title": row[1], "author": row[2], "created_at": row[3].isoformat() if row[3] else None} for row in cursor.fetchall()]

        return {**results, "recent_activity": recent_activity, "categories": categories, "recent_additions": recent_additions, "languages": languages}

    except Exception as e:
        print(f"❌ CRITICAL DASHBOARD ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Database Sync Error")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()