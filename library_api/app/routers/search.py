from fastapi import APIRouter
from psycopg2.extras import RealDictCursor
from app.database import get_connection


router = APIRouter(prefix="/search", tags=["search"])




# ================= GLOBAL SEARCH =================
@router.get("")
def global_search(q: str = "", page: int = 1, limit: int = 10):

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    offset = (page - 1) * limit
    

    # -------- COUNT --------
    count_query = """
        SELECT COUNT(*)
        FROM items i
        LEFT JOIN works w ON i.work_id = w.work_id
        WHERE i.is_deleted = FALSE
    """

    count_params = []

    if q:
        count_query += """
        AND (
            w.search_vector @@ plainto_tsquery('english', %s)
            OR similarity(w.title, %s) > 0.2
            OR similarity(w.author, %s) > 0.2
            OR w.title ILIKE %s
            OR w.author ILIKE %s
            
        )
        """
        count_params.extend([
            q,
            q,
            q,
            f"%{q}%",
            f"%{q}%",
            
            
        ])

    cur.execute(count_query, count_params)
    total = cur.fetchone()["count"]

    # -------- DATA + RANKING --------
    query = """
        SELECT
            i.serial_no,
            i.accession_no,
            w.title,
            w.author,
            w.language,

            CASE
                WHEN LOWER(w.title) = LOWER(%s) THEN 100
                WHEN w.title ILIKE %s THEN 80
                WHEN w.title ILIKE %s THEN 60
                WHEN w.author ILIKE %s THEN 40
                WHEN similarity(w.title, %s) > 0.3 THEN 20
                      
                ELSE 0
            END AS score

        FROM items i
        LEFT JOIN works w ON i.work_id = w.work_id
        WHERE i.is_deleted = FALSE
    """

    data_params = []

    if q:
        query += """
        AND (
            w.search_vector @@ plainto_tsquery('english', %s)
            OR similarity(w.title, %s) > 0.2
            OR similarity(w.author, %s) > 0.2
            OR w.title ILIKE %s
            OR w.author ILIKE %s
            
        )
        """
        data_params.extend([
            q,
            q,
            q,
            f"%{q}%",
            f"%{q}%",
                        
        ])

    ranking_params = [
        q,                      # exact title
        f"{q}%",                # starts with
        f"%{q}%",               # contains
        f"%{q}%",               # author
        q,                      # similarity
    
    ]

    query += """
        ORDER BY score DESC, i.serial_no
        LIMIT %s OFFSET %s
    """

    cur.execute(query, ranking_params + data_params + [limit, offset])
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "data": rows,
        "total": total,
        "page": page,
        "limit": limit
    }


# ================= AUTOCOMPLETE =================
@router.get("/suggest")
def suggest(q: str = ""):

    if not q:
        return []
    
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT 
            w.title,
            w.author,

            CASE
                WHEN LOWER(w.title) = LOWER(%s) THEN 100
                WHEN w.title ILIKE %s THEN 80
                WHEN w.title ILIKE %s THEN 60
                WHEN w.author ILIKE %s THEN 40
                
                ELSE 0
            END AS score

        FROM works w
        WHERE 
            w.title ILIKE %s
            OR w.author ILIKE %s
            

        ORDER BY score DESC, w.title
        LIMIT 10
    """, (
        q,
        f"{q}%",
        f"%{q}%",
        f"%{q}%",
        f"%{q}%",
        f"%{q}%",
        
        
    ))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows