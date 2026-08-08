from fastapi import APIRouter, Depends, HTTPException, Request
from app.database import get_connection
from app.auth import get_current_user
from app.audit_utils import audit_action

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@audit_action("VIEW_DASHBOARD")
@router.get("/summary")
def dashboard_summary(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    conn = None
    cursor = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        results = {"role": role}
        
        # Count all works regardless of pending/approved, or match your active status 
        # (Change 'PENDING' to 'AVAILABLE' or whatever status your app uses)
        cursor.execute("SELECT COUNT(*) FROM public.works")
        results["total_accessions"] = int(cursor.fetchone()[0])
        
        cursor.execute("SELECT COUNT(*) FROM public.works")
        results["total_books"] = int(cursor.fetchone()[0])

        # Missing & Damaged items metrics if your cards use them
        cursor.execute("""
        SELECT COUNT(*)
        FROM public.items
        WHERE availability_status = 'MISSING'
        """)
        results["missing_items"] = int(cursor.fetchone()[0])

        cursor.execute("""
        SELECT COUNT(*)
        FROM public.items
        WHERE availability_status = 'DAMAGED'
        """)
        results["damaged_items"] = int(cursor.fetchone()[0])
        
        # Languages breakdown if your template maps summaryStats.languages
        cursor.execute("SELECT language, COUNT(*) as count FROM public.works GROUP BY language")
        lang_rows = cursor.fetchall()
        results["languages"] = [{"language": row[0] or "Unknown", "count": row[1]} for row in lang_rows]

        if role in ["keeper", "chief"]:
            cursor.execute("SELECT COUNT(*) FROM public.items WHERE availability_status = 'ISSUED'")
            results["total_issued"] = int(cursor.fetchone()[0])
            
            cursor.execute("SELECT id, accession_no, new_status, changed_at FROM public.status_audit ORDER BY changed_at DESC LIMIT 5")
            results["recent_activity"] = cursor.fetchall()
            
        if role == "chief":
            cursor.execute("SELECT COUNT(*) FROM public.users")
            results["total_users"] = int(cursor.fetchone()[0])

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()