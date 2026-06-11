from fastapi import APIRouter, Depends, Request
from psycopg2.extras import RealDictCursor
from app.database import get_connection
from app.auth import get_current_user
from app.audit_utils import audit_action  # 🛡️ Standardized auditing

router = APIRouter(prefix="/search", tags=["search"])

# ================= GLOBAL SEARCH =================
@audit_action("GLOBAL_SEARCH")
@router.get("")
def global_search(
    q: str = "", 
    page: int = 1, 
    limit: int = 10, 
    request: Request = None, 
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    offset = (page - 1) * limit

    try:
        # Standardized Search Query
        # Note: You were building query strings manually; 
        # ensure your input 'q' is sanitized or handled by psycopg2 parameters
        query = """
            SELECT i.serial_no, i.accession_no, w.title, w.author, w.language,
            CASE WHEN LOWER(w.title) = LOWER(%s) THEN 100 
                 WHEN w.title ILIKE %s THEN 80 
                 WHEN w.title ILIKE %s THEN 60 
                 WHEN w.author ILIKE %s THEN 40 
                 ELSE 0 END AS score
            FROM items i
            LEFT JOIN works w ON i.work_id = w.work_id
            WHERE i.is_deleted = FALSE 
            AND (w.search_vector @@ plainto_tsquery('english', %s) 
                 OR w.title ILIKE %s OR w.author ILIKE %s)
            ORDER BY score DESC, i.serial_no
            LIMIT %s OFFSET %s
        """
        # Execute with standardized parameters
        cur.execute(query, (q, f"{q}%", f"%{q}%", f"%{q}%", q, f"%{q}%", f"%{q}%", limit, offset))
        rows = cur.fetchall()

        return {"data": rows, "page": page, "limit": limit}
    finally:
        cur.close(); conn.close()

# ================= AUTOCOMPLETE =================
@audit_action("SEARCH_SUGGEST")
@router.get("/suggest")
def suggest(
    q: str = "", 
    request: Request = None, 
    current_user: dict = Depends(get_current_user)
):
    if not q: return []
    
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT title, author,
            CASE WHEN LOWER(title) = LOWER(%s) THEN 100 
                 WHEN title ILIKE %s THEN 80 ELSE 0 END AS score
            FROM works
            WHERE title ILIKE %s OR author ILIKE %s
            ORDER BY score DESC LIMIT 10
        """, (q, f"{q}%", f"%{q}%", f"%{q}%"))
        return cur.fetchall()
    finally:
        cur.close(); conn.close()