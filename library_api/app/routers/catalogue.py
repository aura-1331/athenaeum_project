from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from app.auth import get_current_user, require_role
from app.database import get_connection, record_audit
from app.audit_utils import audit_action  # 1. Added automated audit import
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor
from typing import Optional, List
from datetime import datetime
import httpx

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
    author: Optional[str] = "Unknown"  
    category: Optional[str] = None
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

class DuplicateCheckRequest(BaseModel):
    title: str
    author: Optional[str] = None
    
def generate_record_id(serial_no: int):
    year = datetime.now().year
    return f"AO-REC-{year}-{str(serial_no).zfill(6)}"

def get_language_prefix(language: str) -> str:
    lang = language.lower().strip()
    if lang == "malayalam": return "ML"
    if lang == "english": return "EN"
    if "multi" in lang: return "MU"
    if lang == "tamil": return "TA"
    if lang == "telugu": return "TE"
    if lang == "marathi": return "MR"
    if lang == "malay": return "MA"
    return language[:2].upper()

def get_category_code(category: str) -> str:
    cat = category.strip()
    if cat == "Fiction": return "FIC"
    if cat == "Non-Fiction": return "NF"
    if cat == "Reference": return "REF"
    if cat == "Religious": return "REL"
    if cat == "Poetry": return "POE"
    return "GEN"

@router.get("/next-numbers")
def get_next_numbers(language: str, category: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(MAX(serial_no), 0) + 1 FROM public.items")
        next_serial = cur.fetchone()[0]

        lang_prefix = get_language_prefix(language)
        clean_lang = language.strip()
        
        cur.execute("""
            SELECT COUNT(*) + 1 
            FROM public.items i
            JOIN public.works w ON i.work_id = w.work_id
            WHERE w.language = %s
        """, (clean_lang,))
        next_accession_count = cur.fetchone()[0]
        allocated_accession = f"{lang_prefix}-{next_accession_count}"

        allocated_call = None
        if category:
            cat_code = get_category_code(category)
            lang_initial = lang_prefix if len(lang_prefix) == 2 else language[0].upper()
            
            cur.execute("""
                SELECT COUNT(*) + 1 
                FROM public.works 
                WHERE language = %s AND category = %s
            """, (clean_lang, category))
            next_call_count = cur.fetchone()[0]
            allocated_call = f"{lang_initial}-{cat_code}-{next_call_count}.0"

        return {
            "serial_no": next_serial,
            "accession_no": allocated_accession,
            "call_no": allocated_call
        }
    except Exception as e:
        print(f"❌ Error calculating structural previews: {e}")
        raise HTTPException(status_code=500, detail="Calculation of next numbers failed")
    finally:
        cur.close()
        conn.close()

@router.get("/isbn-lookup", response_model=dict)
async def lookup_isbn(isbn: str, current_user: dict = Depends(get_current_user)):
    clean_isbn = isbn.replace("-", "").strip()
    if not clean_isbn:
        raise HTTPException(status_code=400, detail="Invalid ISBN format provided")
    
    headers = {"User-Agent": "AthenaeumOrbisLibrarySystem/1.0"}
    
    async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
        try:
            google_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{clean_isbn}"
            google_res = await client.get(google_url)
            
            if google_res.status_code == 200:
                g_data = google_res.json()
                if "items" in g_data and len(g_data["items"]) > 0:
                    info = g_data["items"][0]["volumeInfo"]
                    
                    authors_list = info.get("authors", [])
                    author_name = authors_list[0] if authors_list else ""
                    
                    pub_date = info.get("publishedDate", "")
                    pub_year = pub_date.split("-")[0] if pub_date else None
                    
                    categories = info.get("categories", [])
                    extracted_genre = categories[0] if categories else ""
                    
                    ddc_val = None
                    
                    return {
                        "title": info.get("title", ""),
                        "author": author_name,
                        "publisher": info.get("publisher", ""),
                        "year": pub_year,
                        "genre": extracted_genre,
                        "ddc": ddc_val
                    }
        except Exception as e:
            print(f"⚠️ Google Books API failed or timed out: {e}")

        try:
            ol_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{clean_isbn}&format=json&jscmd=data"
            ol_res = await client.get(ol_url)
            
            if ol_res.status_code == 200:
                ol_data = ol_res.json()
                book_key = f"ISBN:{clean_isbn}"
                
                if book_key in ol_data:
                    b_info = ol_data[book_key]
                    
                    ol_authors = b_info.get("authors", [])
                    ol_author = ol_authors[0].get("name", "") if ol_authors else ""
                    
                    ol_date = b_info.get("publish_date", "")
                    ol_year = None
                    if ol_date:
                        year_match = datetime.strptime(ol_date[-4:], "%Y") if ol_date[-4:].isdigit() else None
                        if year_match:
                            ol_year = str(year_match.year)
                            
                    ol_publishers = b_info.get("publishers", [])
                    ol_pub = ol_publishers[0].get("name", "") if ol_publishers else ""
                    
                    return {
                        "title": b_info.get("title", ""),
                        "author": ol_author,
                        "publisher": ol_pub,
                        "year": ol_year,
                        "genre": None,
                        "ddc": None
                    }
        except Exception as e:
            print(f"⚠️ Open Library API failed or timed out: {e}")
            
    raise HTTPException(status_code=404, detail="No metadata found for this ISBN")

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

@router.get("/publishers/search", response_model=List[str])
def search_publishers(q: str, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT publisher 
            FROM public.works 
            WHERE publisher ILIKE %s 
            ORDER BY publisher 
            LIMIT 10
        """, (f"%{q}%",))
        rows = cur.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail="Publisher lookup failed")
    finally:
        cur.close()
        conn.close()

@audit_action("CREATE_WORK")
@router.post("/create-work")
def create_work(
    payload: WorkCreate, 
    request: Request, 
    current_user: dict = Depends(get_current_user),
    x_change_reason: Optional[str] = Header(default="New registration initialization sequencing"),
    x_device_id: Optional[str] = Header(default="Desktop Browser Workstation"),
    x_ip_address: Optional[str] = Header(default="127.0.0.1")
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        token_user_id = current_user.get("user_id")
        cur.execute("SELECT name FROM public.users WHERE user_id = %s", (token_user_id,))
        user_row = cur.fetchone()
        real_name = user_row[0] if user_row else "SYSTEM_UNKNOWN"
        real_role = current_user.get("role") or "SYSTEM_UNKNOWN"

        cur.execute("SET LOCAL request.jwt.claim.username = %s;", (real_name,))
        cur.execute("SET LOCAL request.jwt.claim.role = %s;", (real_role,))
        cur.execute("SET LOCAL request.jwt.claim.user_id = %s;", (str(token_user_id),))
        cur.execute("SET LOCAL request.custom.change_reason = %s;", (x_change_reason,))
        cur.execute("SET LOCAL request.custom.device_id = %s;", (x_device_id,))
        cur.execute("SET LOCAL request.custom.ip_address = %s;", (x_ip_address,))

        lang_prefix = get_language_prefix(payload.language)
        clean_lang = payload.language.strip()
        
        cur.execute("""
            SELECT COUNT(*) + 1 
            FROM public.items i
            JOIN public.works w ON i.work_id = w.work_id
            WHERE w.language = %s
        """, (clean_lang,))
        next_accession_count = cur.fetchone()[0]
        final_accession_no = f"{lang_prefix}-{next_accession_count}"

        final_call_no = payload.call_no
        if payload.category and (not final_call_no or final_call_no.endswith('-')):
            cat_code = get_category_code(payload.category)
            lang_initial = lang_prefix if len(lang_prefix) == 2 else payload.language[0].upper()
            
            cur.execute("""
                SELECT COUNT(*) + 1 
                FROM public.works 
                WHERE language = %s AND category = %s
            """, (clean_lang, payload.category))
            next_call_count = cur.fetchone()[0]
            final_call_no = f"{lang_initial}-{cat_code}-{next_call_count}.0"

        work_query = """
            INSERT INTO public.works (
                title, language, category, genre, author, publisher, 
                original_language, ddc, notes, translation_compilation,
                year, isbn, call_no, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING work_id
        """
        
        safe_year = int(payload.year) if payload.year else None

        cur.execute(
            work_query,
            (
                payload.title, 
                payload.language, 
                payload.category or None, 
                payload.genre if (payload.genre and payload.genre.strip() != "") else None,
                payload.author if (payload.author and payload.author.strip() != "") else "Unknown", 
                payload.publisher or None, 
                payload.original_language or None,
                payload.ddc or None, 
                payload.notes or None, 
                payload.translation_compilation or None,
                safe_year, 
                payload.isbn or None, 
                final_call_no
            )
        )
        work_id = cur.fetchone()[0]

        item_query = """
            INSERT INTO public.items (
                work_id, accession_no, call_no, availability_status, is_deleted, created_at
            ) VALUES (%s, %s, %s, 'AVAILABLE', 'f', NOW())
        """
        cur.execute(item_query, (work_id, final_accession_no, final_call_no))

        conn.commit()
        return {
            "work_id": work_id,
            "accession_no": final_accession_no
        }
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

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
                i.work_id, 
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
        
        if not result:
            print("❌ Database Error: 404: Book Record not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Book Record not found"
            )
            
        result["record_id"] = generate_record_id(result["serial_no"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        cur.close()
        conn.close()

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
                i.serial_no, i.accession_no, i.work_id, w.title, w.author, 
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

@audit_action("UPDATE_LEDGER")
@router.patch("/{serial_no}", dependencies=[Depends(require_role(["The Chief"]))]) # <--- ADD THIS
async def update_ledger_record(
    serial_no: int, 
    payload: dict, 
    request: Request, 
    current_user: dict = Depends(get_current_user),
    x_change_reason: Optional[str] = Header(default="Routine operational adjustment"),
    x_device_id: Optional[str] = Header(default="Desktop Browser Workstation"),
    x_ip_address: Optional[str] = Header(default="127.0.0.1")
):    
    lookup_conn = get_connection()
    lookup_cur = lookup_conn.cursor()
    try:
        token_user_id = int(current_user.get("user_id"))
        lookup_cur.execute("SELECT name FROM public.users WHERE user_id = %s", (token_user_id,))
        user_row = lookup_cur.fetchone()
        real_name = user_row[0] if user_row else "SYSTEM_UNKNOWN"
        real_role = current_user.get("role") or "SYSTEM_UNKNOWN"
    finally:
        lookup_cur.close()
        lookup_conn.close()

    conn = get_connection(username=real_name, role=real_role)
    cur = conn.cursor()
    try:
        cur.execute("SET LOCAL request.jwt.claim.username = %s;", (real_name,))
        cur.execute("SET LOCAL request.jwt.claim.role = %s;", (real_role,))
        cur.execute("SET LOCAL request.jwt.claim.user_id = %s;", (str(token_user_id),))
        cur.execute("SET LOCAL request.custom.change_reason = %s;", (x_change_reason,))
        cur.execute("SET LOCAL request.custom.device_id = %s;", (x_device_id,))
        cur.execute("SET LOCAL request.custom.ip_address = %s;", (x_ip_address,))

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

        cur.execute("SELECT language, category, call_no FROM public.works WHERE work_id = %s", (work_id,))
        current_work = cur.fetchone()
        current_lang = current_work[0]
        current_cat = current_work[1]
        current_call = current_work[2]

        new_cat = payload.get('category')
        provided_call = payload.get('call_no')
        
        if provided_call in ["", "---", None]:
            provided_call = None
            
        final_call_no = provided_call or current_call

        if new_cat and new_cat.strip() != "" and (new_cat != current_cat or not final_call_no or final_call_no == "---"):
            lang_prefix = get_language_prefix(current_lang)
            cat_code = get_category_code(new_cat)
            lang_initial = lang_prefix if len(lang_prefix) == 2 else current_lang[0].upper()
            clean_lang = current_lang.strip()

            cur.execute("""
                SELECT COUNT(*) + 1 
                FROM public.works 
                WHERE language = %s AND category = %s
            """, (clean_lang, new_cat))
            next_call_count = cur.fetchone()[0]
            final_call_no = f"{lang_initial}-{cat_code}-{next_call_count}.0"

        cur.execute("""
            UPDATE public.works SET 
                title = COALESCE(NULLIF(%s, ''), title),
                author = COALESCE(NULLIF(%s, ''), author),
                publisher = COALESCE(NULLIF(%s, ''), publisher),
                isbn = COALESCE(NULLIF(%s, ''), isbn),
                ddc = COALESCE(NULLIF(%s, ''), ddc),
                year = COALESCE(NULLIF(%s, 0)::text::integer, year),
                category = NULLIF(%s, ''),
                genre = %s,
                original_language = COALESCE(NULLIF(%s, ''), original_language),
                translation_compilation = %s,
                notes = %s,
                call_no = COALESCE(NULLIF(%s, ''), call_no)
            WHERE work_id = %s
        """, (
            payload.get('title'),
            payload.get('author'),
            payload.get('publisher'),
            payload.get('isbn'),
            payload.get('ddc'),
            payload.get('year'),
            new_cat,
            payload.get('genre') if (payload.get('genre') and payload.get('genre').strip() != "") else None,
            payload.get('original_language'),
            payload.get('translation_compilation'),
            payload.get('notes'),
            final_call_no,
            work_id
        ))

        if final_call_no:
            cur.execute("UPDATE public.items SET call_no = %s WHERE work_id = %s", (final_call_no, work_id))

        conn.commit()
        return {"status": "success", "call_no": final_call_no}
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@audit_action("WORK_APPROVAL")
@router.post("/approve/{work_id}", tags=["Admin Operations"], dependencies=[Depends(require_role(["The Chief"]))]) # <--- ADD THIS
async def approve_work(
    work_id: int, action: str, reason: str, request: Request,
    current_user: dict = Depends(get_current_user)
):    
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

        conn.commit()
        return {"message": f"Work '{row[0]}' {new_status}."}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@audit_action("SOFT_DELETE")
@router.delete("/{book_id}", tags=["Catalogue Operations"], dependencies=[Depends(require_role(["The Chief"]))]) # <--- ADD THIS
async def soft_delete_book(
    book_id: int, reason: str, request: Request,
    current_user: dict = Depends(get_current_user)
):    
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE public.items 
            SET is_deleted = TRUE, deletion_reason = %s 
            WHERE serial_no = %s
        """, (reason, book_id))
        
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.post("/check-duplicate")
def check_duplicate(payload: DuplicateCheckRequest, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COUNT(*) 
            FROM public.works 
            WHERE title ILIKE %s AND author ILIKE %s
        """, (payload.title.strip(), f"%{payload.author.strip()}%" if payload.author else "%Unknown%"))
        count = cur.fetchone()[0]
        return {"is_duplicate": count > 0}
    except Exception as e:
        print(f"❌ Duplicate check failure: {e}")
        raise HTTPException(status_code=500, detail="Duplicate verification failed")
    finally:
        cur.close()
        conn.close()