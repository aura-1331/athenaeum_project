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

        cursor.execute("SELECT COUNT(*) FROM public.items WHERE is_deleted = FALSE")
        total_items = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM public.works WHERE status = 'APPROVED'")
        total_books = cursor.fetchone()[0]

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
                # Safe date conversion
                dt = r[4]
                formatted_date = dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
                
                recent_activity.append({
                    "id": r[0],
                    "accession_no": r[1],
                    "old_status": r[2],
                    "new_status": r[3],
                    "changed_at": formatted_date
                })
        except Exception as table_err:
            print(f"⚠️ Activity Table Error: {table_err}")
            recent_activity = []

        # 🛠️ FIXED: Renamed 'total_items' to 'total_accessions' for the Dashboard
        return {
    "total_accessions": int(total_items), 
    "total_books": int(total_books),
    "recent_activity": recent_activity
}

    except Exception as e:
        print(f"❌ CRITICAL DASHBOARD ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Database Sync Error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()