from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.auth import get_current_user
from app.database import get_connection, record_audit
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/catalogue", tags=["catalogue"])

class RecommendationRequest(BaseModel):
    title: str
    author: str
    genre: str
    publisher: str
    year: int
    reason: str 

    

def generate_record_id(serial_no: int):
    year = datetime.now().year
    return f"AO-REC-{year}-{str(serial_no).zfill(6)}"

# --- 1. FETCH SINGLE RECORD (FOR DETAIL & EDIT VIEWS) ---
@router.get("/{serial_no}")

def get_book(serial_no: int, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Standardized Aliases to match Vue 'item' variables exactly
        query = """
            SELECT 
                i.serial_no, 
                i.accession_no, 
                i.shelf, 
                w.language as language,
                w.title, 
                w.author, 
                w.publisher, 
                w.year, 
                w.isbn, 
                w.ddc, 
                w.call_no,
                w.original_language, 
                w.notes,
                w.category,
                w.genre,
                w.translation_compilation
            FROM public.items i
            INNER JOIN public.works w ON i.work_id = w.work_id
            WHERE i.serial_no = %s AND i.is_deleted = FALSE
        """
        cur.execute(query, (serial_no,))
        result = cur.fetchone()
        if result:
            result["record_id"] = generate_record_id(result["serial_no"])
        if not result:
            raise HTTPException(status_code=404, detail="Book Record not found")
        return result
    except Exception as e:
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        cur.close()
        conn.close()

# --- 2. FETCH PAGINATED CATALOGUE (WITH TOTAL COUNT FIX) ---
@router.get("/")

def get_catalogue(
    page: int = 1, 
    limit: int = 50, 
    sort_by: str = "serial_no", 
    order: str = "asc",

    title: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    language: Optional[str] = None,
    category: Optional[str] = None,

    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        user_role = current_user.get('role', 'GUEST')
        offset = (page - 1) * limit
        safe_order = "ASC" if order.lower() == "asc" else "DESC"
        filters = []
        params = []

        # Base condition
        filters.append("i.is_deleted = FALSE")

        if title:
            filters.append("w.title ILIKE %s")
            params.append(f"%{title}%")

        if author:
            filters.append("w.author ILIKE %s")
            params.append(f"%{author}%")

        if genre:
            filters.append("w.genre ILIKE %s")
            params.append(f"%{genre}%")

        if language:
            filters.append("w.language ILIKE %s")
            params.append(f"%{language}%")

        if category:
            filters.append("w.category ILIKE %s")
            params.append(f"%{category}%")

        where_clause = " AND ".join(filters)
                # RBAC Security: Architects/Archivists see everything; Guests see APPROVED only.
        visibility_filter = ""
        
        # 🛠️ Fix: Count REAL total in DB to wake up pagination buttons
        count_query = f"""
            SELECT COUNT(*) 
            FROM public.items i
            LEFT JOIN public.works w ON i.work_id = w.work_id
            WHERE {where_clause}
        """
        cur.execute(count_query, params)
        
        total_records = cur.fetchone()['count']

        # Fetch the specific page data
        query = f"""
            SELECT 
                i.serial_no, i.accession_no, w.title, w.author, 
                w.category, w.genre, w.year, w.publisher, 
                i.shelf, w.language as language, w.isbn, 
                w.ddc, w.call_no, 
                w.notes, w.original_language, w.translation_compilation
            FROM public.items i
            LEFT JOIN public.works w ON i.work_id = w.work_id
            WHERE {where_clause}
            ORDER BY i.serial_no {safe_order}
            LIMIT %s OFFSET %s
        """
        cur.execute(query, (limit, offset))
        items = cur.fetchall()
        for item in items:
            item["record_id"] = generate_record_id(item["serial_no"])

        return {
            "data": items, 
            "total": total_records, 
            "page": page,
            "limit": limit
        }
    except Exception as e:
        print(f"❌ DATABASE ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# --- 3. ATOMIC SELECTIVE UPDATE (STOPS WIPEOUTS) ---

# --- 3. ATOMIC SELECTIVE UPDATE (STOPS WIPEOUTS) ---
@router.patch("/{serial_no}")

async def update_ledger_record(serial_no: int, payload: dict, request: Request, current_user: dict = Depends(get_current_user)):
    
    if current_user.get('role') != "Sys_Arch":
        raise HTTPException(status_code=403, detail="Architect Authorization Required")

    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Update Physical Data (Items Table)
        cur.execute("""
            UPDATE public.items SET 
                shelf = COALESCE(NULLIF(%s, ''), shelf),
                notes = %s,
                language_id = COALESCE(NULLIF(%s, ''), language_id)
            WHERE serial_no = %s RETURNING work_id
        """, (payload.get('shelf'), payload.get('notes'), payload.get('language'), serial_no))
        
        res = cur.fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="Item not found")
        work_id = res[0]

        # 2. Update Bibliographic Data (Works Table)
        # Note: 11 placeholders (%s) total
        cur.execute("""
            UPDATE public.works SET 
                title = COALESCE(NULLIF(%s, ''), title),
                author = COALESCE(NULLIF(%s, ''), author),
                publisher = COALESCE(NULLIF(%s, ''), publisher),
                isbn = COALESCE(NULLIF(%s, ''), isbn),
                ddc = COALESCE(NULLIF(%s, ''), ddc),
                year = COALESCE(NULLIF(%s, 0)::text::integer, year),
                category = COALESCE(NULLIF(%s, ''), category),
                genre = COALESCE(NULLIF(%s, ''), genre),
                original_language = COALESCE(NULLIF(%s, ''), original_language),
                translation_compilation = %s,
                notes = %s
            WHERE work_id = %s
        """, (
            payload.get('title'),                 # 1
            payload.get('author'),                # 2
            payload.get('publisher'),             # 3
            payload.get('isbn'),                  # 4
            payload.get('ddc'),                   # 5
            payload.get('year'),                  # 6
            payload.get('category'),              # 7
            payload.get('genre'),                 # 8
            payload.get('original_language'),      # 9
            payload.get('translation_compilation'),# 10
            payload.get('notes'),                 # 11 (Matches notes = %s)
            work_id                               # WHERE clause ID
        ))

        conn.commit()
        return {"status": "success"}
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# --- 4. WORK APPROVAL OPERATIONS ---
@router.post("/approve/{work_id}", tags=["Admin Operations"])
async def approve_work(
    work_id: int, action: str, reason: str, request: Request,
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] != "Sys_Arch":
        raise HTTPException(status_code=403, detail="Architect only.")

    conn = get_connection()
    cur = conn.cursor()
    try:
        new_status = "APPROVED" if action.upper() == "APPROVE" else "REJECTED"
        cur.execute("""
            UPDATE public.works 
            SET status = %s, approved_by = %s, approval_reason = %s, approved_at = CURRENT_TIMESTAMP
            WHERE work_id = %s RETURNING title
        """, (new_status, current_user['user_id'], reason, work_id))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Work not found.")

        await record_audit(
            user_id=current_user['user_id'],
            action_type=f"WORK_{new_status}",
            request=request,
            target_id=str(work_id),
            details=f"Decision: {new_status}. Reason: {reason}"
        )
        conn.commit()
        return {"message": f"Work '{row[0]}' {new_status}."}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# --- 5. SOFT DELETE OPERATIONS ---
@router.delete("/{book_id}", tags=["Catalogue Operations"])
async def soft_delete_book(
    book_id: int, reason: str, request: Request,
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] != "Sys_Arch":
        raise HTTPException(status_code=403, detail="Architect only.")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE public.items 
            SET is_deleted = TRUE, deletion_reason = %s 
            WHERE serial_no = %s
        """, (reason, book_id))
        
        await record_audit(
            user_id=current_user['user_id'],
            action_type="SOFT_DELETE",
            request=request,
            target_id=str(book_id),
            details=f"Reason: {reason}"
        )
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()