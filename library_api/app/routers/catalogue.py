from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.auth import get_current_user
from app.database import get_connection, record_audit
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/catalogue", tags=["catalogue"])

class RecommendationRequest(BaseModel):
    title: str
    author: str
    genre: str
    publisher: str
    year: int
    reason: str 

class WorkCreate(BaseModel):
    title: str
    author: str
    category: str
    language: str
    publisher: Optional[str] = None
    year: Optional[str] = None
    isbn: Optional[str] = None
    ddc: Optional[str] = None
    call_no: Optional[str] = None
    translation_compilation: Optional[str] = None
    genre: Optional[str] = None
    original_language: Optional[str] = None
    notes: Optional[str] = None

def generate_record_id(serial_no: int):
    year = datetime.now().year
    return f"AO-REC-{year}-{str(serial_no).zfill(6)}"

# --- ADDED: AUTHOR SEARCH SUGGESTIONS ENDPOINT ---
@router.get("/authors/search", response_model=List[str])
def search_authors(q: str, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT author 
            FROM public.works 
            WHERE author ILIKE %s 
            ORDER BY author 
            LIMIT 10
        """, (f"%{q}%",))
        rows = cur.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail="Author lookup failed")
    finally:
        cur.close()
        conn.close()

# --- ADDED: CREATE AUTHORITY RECORD AND PHYSICAL COPY ENDPOINT ---
@router.post("/create-work")
def create_work(payload: WorkCreate, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        work_query = """
            INSERT INTO public.works (
                title, 
                language,
                category,
                genre,
                author,
                publisher, 
                original_language,
                ddc,
                notes,
                translation_compilation,
                year,
                isbn,
                call_no,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING work_id
        """
        
        safe_year = int(payload.year) if payload.year else None

        cur.execute(
            work_query,
            (
                payload.title,
                payload.language,
                payload.category,
                payload.genre or None,
                payload.author,
                payload.publisher or None,
                payload.original_language or None,
                payload.ddc or None,
                payload.notes or None,
                payload.translation_compilation or None,
                safe_year,
                payload.isbn or None,
                payload.call_no or None
            )
        )
        work_id = cur.fetchone()[0]

        cur.execute("SELECT generate_next_accession_no(%s)", (payload.language,))
        accession_no = cur.fetchone()[0]

        item_query = """
            INSERT INTO public.items (
                work_id, accession_no, call_no, availability_status, is_deleted, created_at
            ) VALUES (%s, %s, %s, 'AVAILABLE', 'f', NOW())
        """
        cur.execute(item_query, (work_id, accession_no, payload.call_no or None))

        conn.commit()
        return {
            "work_id": work_id,
            "accession_no": accession_no
        }
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# --- 1. FETCH SINGLE RECORD (FOR DETAIL & EDIT VIEWS) ---
@router.get("/{serial_no}")
def get_book(serial_no: int, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
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
        visibility_filter = ""
        
        count_query = f"""
            SELECT COUNT(*) 
            FROM public.items i
            LEFT JOIN public.works w ON i.work_id = w.work_id
            WHERE {where_clause}
        """
        cur.execute(count_query, params)
        
        total_records = cur.fetchone()['count']

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
@router.patch("/{serial_no}")
async def update_ledger_record(serial_no: int, payload: dict, request: Request, current_user: dict = Depends(get_current_user)):
    if current_user.get('role') != "The Chief":
        raise HTTPException(status_code=403, detail="Chief Authorization Required")

    conn = get_connection()
    cur = conn.cursor()
    try:
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
            payload.get('title'),
            payload.get('author'),
            payload.get('publisher'),
            payload.get('isbn'),
            payload.get('ddc'),
            payload.get('year'),
            payload.get('category'),
            payload.get('genre'),
            payload.get('original_language'),
            payload.get('translation_compilation'),
            payload.get('notes'),
            work_id
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
    if current_user['role'] != "The Chief":
        raise HTTPException(status_code=403, detail="Chief only.")

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
    if current_user['role'] != "The Chief":
        raise HTTPException(status_code=403, detail="Chief only.")

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