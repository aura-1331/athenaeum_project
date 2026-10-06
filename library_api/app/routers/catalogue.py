# app/routers/catalogue.py

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from app.auth import get_current_user, require_role
from app.database import get_connection
from app.services.audit_service import log_audit_activity
from app.audit_utils import audit_action
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

def resolve_authority(cur, author_name: str, user_id: int) -> int:
    clean_author = " ".join((author_name or "").strip().split())

    if not clean_author or clean_author.casefold() == "unknown":
        cur.execute("""
            SELECT authority_id
            FROM public.authority_records
            WHERE authority_code = 'AUT-U-0001'
            LIMIT 1
        """)
        row = cur.fetchone()

        if not row:
            raise RuntimeError("AUT-U-0001 (Unknown) authority record is missing.")

        return row[0]

    cur.execute("""
        SELECT authority_id
        FROM public.authority_records
        WHERE preferred_name = %s
        ORDER BY authority_id
        LIMIT 1
    """, (clean_author,))

    row = cur.fetchone()

    if row:
        return row[0]

    cur.execute("""
        SELECT COALESCE(
            MAX(CAST(SUBSTRING(authority_code FROM 7) AS INTEGER)),
            0
        ) + 1
        FROM public.authority_records
        WHERE authority_code ~ '^AUT-P-[0-9]+$'
    """)

    next_number = cur.fetchone()[0]
    authority_code = f"AUT-P-{next_number:04d}"

    cur.execute("""
        INSERT INTO public.authority_records (
            authority_code,
            preferred_name,
            authority_type,
            status,
            notes,
            created_by
        )
        VALUES (
            %s,
            %s,
            'PERSON',
            'PROVISIONAL',
            'Automatically created from new work registration; authority identity not yet formally verified.',
            %s
        )
        RETURNING authority_id
    """, (
        authority_code,
        clean_author,
        user_id
    ))

    return cur.fetchone()[0]

@router.get("/next-numbers")
def get_next_numbers(request: Request, language: str, category: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(MAX(serial_no), 0) + 1 FROM public.items")
        next_serial = cur.fetchone()[0]

        lang_prefix = get_language_prefix(language)
        clean_lang = language.strip()
        
        cur.execute("""
            SELECT COALESCE(last_number, 0) + 1
            FROM public.language_registry
            WHERE TRIM(prefix) = %s
        """, (lang_prefix,))
        row = cur.fetchone()
        next_accession_count = row[0] if row else 1
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
def search_authors(request: Request, q: str, current_user: dict = Depends(get_current_user)):
    conn = get_connection(request=request)
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
def search_publishers(request: Request, q: str, current_user: dict = Depends(get_current_user)):
    conn = get_connection(request=request)
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

# ---------------------------------------------------------------------------
# Docket history helpers (read from the hash-chained audit ledger)
# ---------------------------------------------------------------------------
def _audit_norm(value) -> str:
    """Normalises a field value so None, '' and surrounding spaces compare equal."""
    return "" if value is None else str(value).strip()


def _history_event(row: dict) -> Optional[dict]:
    """Turns one audit_activities row into a docket timeline event, or None to skip it."""
    import json

    diff = row.get("diff_payload") or {}
    if isinstance(diff, str):
        try:
            diff = json.loads(diff)
        except ValueError:
            diff = {}

    action = row.get("action_type")

    if action in ("ACCESSION_WORK", "ACCESSION_ITEM"):
        kind = "SUBMITTED"
    elif action == "CURATOR_DECISION":
        kind = "APPROVED" if str(diff.get("decision")).upper() == "APPROVED" else "REJECTED"
    elif action == "ITEM_APPROVE":
        kind = "APPROVED"
    elif action == "ITEM_REJECT":
        kind = "REJECTED"
    elif action in ("WORK_RESUBMIT", "ITEM_RESUBMIT"):
        kind = "RESUBMITTED"
    elif action == "REVIEW_NOTE":
        kind = "NOTE"
    else:
        return None

    at = row.get("timestamp")

    return {
        "id": row.get("id"),
        "type": kind,
        "at": at.isoformat() if at else None,
        "actor": row.get("username"),
        "actor_role": row.get("role"),
        "reason": None if kind == "SUBMITTED" else row.get("justification"),
        "changes": diff.get("changes"),
        "flagged_fields": diff.get("flagged_fields"),
        "correction_note": diff.get("correction_note"),
        "note_kind": diff.get("kind") if kind == "NOTE" else None,
    }

# --- 1. ACCESSION WORK ---
@router.post("/create-work", dependencies=[Depends(require_role(["The Chief", "The Keeper"]))])
@audit_action(
    "ACCESSION_WORK",
    target_entity="Work",
    reason_param="x_change_reason"
)
def create_work(
    payload: WorkCreate, 
    request: Request, 
    current_user: dict = Depends(get_current_user),
    x_change_reason: Optional[str] = Header(default="New registration initialization sequencing"),
    x_device_id: Optional[str] = Header(default="Desktop Browser Workstation"),
    x_ip_address: Optional[str] = Header(default="127.0.0.1")
):
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        token_user_id = current_user.get("user_id")
        cur.execute("SELECT name FROM public.users WHERE user_id = %s", (token_user_id,))
        user_row = cur.fetchone()
        real_name = user_row[0] if user_row else (current_user.get("username") or "Archive Operator")
        real_role = current_user.get("role") or "The Keeper"

        cur.execute("SET LOCAL request.jwt.claim.username = %s;", (real_name,))
        cur.execute("SET LOCAL request.jwt.claim.role = %s;", (real_role,))
        cur.execute("SET LOCAL request.jwt.claim.user_id = %s;", (str(token_user_id),))
        cur.execute("SET LOCAL request.custom.change_reason = %s;", (x_change_reason,))
        cur.execute("SET LOCAL request.custom.device_id = %s;", (x_device_id,))
        cur.execute("SET LOCAL request.custom.ip_address = %s;", (x_ip_address,))

        lang_prefix = get_language_prefix(payload.language)
        clean_lang = payload.language.strip()
        
        cur.execute("""
            UPDATE public.language_registry
            SET last_number = last_number + 1
            WHERE TRIM(prefix) = %s
            RETURNING last_number;
        """, (lang_prefix,))
        row = cur.fetchone()
        if not row:
            cur.execute("""
                INSERT INTO public.language_registry (language, prefix, last_number)
                VALUES (%s, %s, 1)
                RETURNING last_number;
            """, (clean_lang, lang_prefix))
            row = cur.fetchone()
        next_accession_count = row[0]
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
                year, isbn, call_no, status, proposed_by, proposal_reason,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
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
                final_call_no, 
                "APPROVED" if real_role.strip().lower() == "the chief" else "PENDING", 
                token_user_id, 
                x_change_reason
            )
        )

        work_id = cur.fetchone()[0]

        author_name = (
            payload.author.strip()
            if payload.author and payload.author.strip()
            else "Unknown"
        )

        authority_id = resolve_authority(
            cur,
            author_name,
            token_user_id
        )

        cur.execute("""
            INSERT INTO public.work_authorities (
                work_id,
                authority_id,
                relationship_type,
                sequence_no,
                notes,
                created_by
            )
            VALUES (%s, %s, 'AUTHOR', 1, %s, %s)
            ON CONFLICT (work_id, authority_id, relationship_type)
            DO NOTHING
        """, (
            work_id,
            authority_id,
            "Automatically linked during work registration.",
            token_user_id
        ))

        item_query = """
            INSERT INTO public.items (
                work_id, accession_no, call_no, availability_status, is_deleted, created_at
            ) VALUES (%s, %s, %s, %s, 'f', NOW())
            RETURNING serial_no
        """
        initial_item_status = (
            "AVAILABLE"
            if real_role.strip().lower() == "the chief"
            else "PENDING"
        )
        cur.execute(
            item_query,
            (work_id, final_accession_no, final_call_no, initial_item_status)
        )
        created_serial_no = cur.fetchone()[0]

        audit_ok = log_audit_activity(
            request=request,
            user_id=str(token_user_id),
            username=real_name,
            role=real_role,
            designation=real_role,
            category="CATALOGUE",
            action_type="ACCESSION_WORK",
            target_entity="WORK",
            target_id=str(work_id),
            endpoint=request.url.path,
            http_method="POST",
            justification=x_change_reason,
            diff_payload={
                "work_id": work_id,
                "serial_no": created_serial_no,
                "accession_no": final_accession_no,
                "title": payload.title,
                "author": author_name,
                "language": payload.language,
                "call_no": final_call_no
            },
            extra_metadata={
                "work_id": work_id,
                "serial_no": created_serial_no,
                "accession_no": final_accession_no
            },
            conn=conn
        )

        if not audit_ok:
            raise RuntimeError(
                "Audit record could not be written; operation rolled back"
            )
        
        conn.commit()

        return {
            "work_id": work_id,
            "accession_no": final_accession_no,
            "serial_no": created_serial_no
        }
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# --- AUTHORIZED WORK LOOKUP FOR ITEM ACCESSION ---
@router.get("/work/{work_id}")
def get_work_for_item_accession(
    request: Request, work_id: int,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT
                work_id,
                title,
                author,
                language,
                category,
                call_no,
                status
            FROM public.works
            WHERE work_id = %s
              AND status = 'APPROVED'
        """, (work_id,))
        work = cur.fetchone()

        if not work:
            raise HTTPException(
                status_code=404,
                detail="Authorized catalogued work not found in registry."
            )

        return work
    finally:
        cur.close()
        conn.close()


# --- 2. ACCESSION ADDITIONAL COPY ---
@router.post("/create-item", dependencies=[Depends(require_role(["The Chief", "The Keeper"]))])
@audit_action(
    "ACCESSION_ITEM",
    target_entity="Item",
    reason_param="x_change_reason"
)
async def create_item(
    payload: dict,
    request: Request,
    current_user: dict = Depends(get_current_user),
    x_change_reason: Optional[str] = Header(default="New copy accession"),
    x_device_id: Optional[str] = Header(default="Desktop Browser Workstation"),
    x_ip_address: Optional[str] = Header(default="127.0.0.1")
):
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        token_user_id = current_user.get("user_id")
        real_role = current_user.get("role") or "The Keeper"
        work_id = payload.get("work_id")
        language_id = payload.get("language_id")

        if not work_id or not language_id:
            raise HTTPException(
                status_code=400,
                detail="Work ID and Language Profile are required."
            )

        try:
            work_id_int = int(str(work_id).strip())
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="Authorized Work ID must be a numeric Work ID."
            )

        cur.execute("""
            SELECT work_id, title, language, category, call_no, status
            FROM public.works
            WHERE work_id = %s
        """, (work_id_int,))
        work = cur.fetchone()

        if not work:
            raise HTTPException(status_code=404, detail="Authorized catalogued work not found.")

        existing_work_id, title, language, category, call_no, work_status = work

        if str(work_status).upper() != "APPROVED":
            raise HTTPException(
                status_code=409,
                detail="This Work is not yet approved and cannot receive an additional copy."
            )

        cur.execute("""
            SELECT COALESCE(MAX(serial_no), 0) + 1
            FROM public.items
        """)
        serial_no = cur.fetchone()[0]

        lang_prefix = get_language_prefix(language)
        
        cur.execute("""
            UPDATE public.language_registry
            SET last_number = last_number + 1
            WHERE TRIM(prefix) = %s
            RETURNING last_number;
        """, (lang_prefix,))
        row = cur.fetchone()
        if not row:
            cur.execute("""
                INSERT INTO public.language_registry (language, prefix, last_number)
                VALUES (%s, %s, 1)
                RETURNING last_number;
            """, (language.strip(), lang_prefix))
            row = cur.fetchone()
        accession_count = row[0]
        accession_no = f"{lang_prefix}-{accession_count}"

        item_status = (
            "AVAILABLE"
            if real_role.strip().lower() == "the chief"
            else "PENDING"
        )

        cur.execute("""
            INSERT INTO public.items (
                work_id,
                accession_no,
                call_no,
                language_id,
                availability_status,
                is_deleted,
                proposed_by
            )
            VALUES (%s, %s, %s, %s, %s, FALSE, %s)
            RETURNING serial_no
        """, (
            existing_work_id,
            accession_no,
            call_no,
            language_id,
            item_status,
            token_user_id
        ))

        created_serial_no = cur.fetchone()[0]

        audit_ok = log_audit_activity(
            request=request,
            user_id=str(token_user_id),
            username=str(current_user.get("username") or current_user.get("name") or "Archive Operator"),
            role=real_role,
            designation=real_role,
            category="CATALOGUE",
            action_type="ACCESSION_ITEM",
            target_entity="ITEM",
            target_id=str(created_serial_no),
            endpoint=request.url.path,
            http_method="POST",
            justification=x_change_reason,
            diff_payload={
                "serial_no": created_serial_no,
                "work_id": existing_work_id,
                "accession_no": accession_no,
                "title": title,
                "language_id": language_id,
                "availability_status": item_status
            },
            extra_metadata={
                "serial_no": created_serial_no,
                "work_id": existing_work_id,
                "device_id": x_device_id,
                "ip_address": x_ip_address
            },
            conn=conn
        )

        if not audit_ok:
            raise RuntimeError(
                "Audit record could not be written; operation rolled back"
            )
        
        conn.commit()

        return {
            "serial_no": created_serial_no,
            "accession_no": accession_no,
            "work_id": existing_work_id,
            "status": item_status
        }

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# --- KEEPER: MY SUBMISSIONS ---
@router.get(
    "/my-submissions",
    tags=["Keeper Operations"],
    dependencies=[Depends(require_role(["The Keeper"]))]
)
def list_my_submissions(
    request: Request, current_user: dict = Depends(get_current_user)
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        user_id = current_user["user_id"]

        cur.execute("""
            SELECT
                w.work_id,
                w.title,
                w.author,
                w.publisher,
                w.language,
                w.category,
                w.genre,
                w.year,
                w.isbn,
                w.ddc,
                w.call_no,
                w.proposal_reason,
                w.status AS work_status,
                w.approval_reason,
                w.created_at AS work_created_at,

                i.serial_no,
                i.accession_no,
                i.availability_status AS item_status,
                i.created_at AS item_created_at,
                i.deletion_reason AS item_deletion_reason

            FROM public.works w

            LEFT JOIN public.items i
                ON i.work_id = w.work_id
               AND (i.proposed_by = %s OR w.proposed_by = %s)

            WHERE w.proposed_by = %s
            OR i.proposed_by = %s

            ORDER BY w.created_at DESC, w.work_id DESC, i.serial_no DESC
        """, (user_id, user_id, user_id, user_id))

        return cur.fetchall()

    except Exception as e:
        print(f"❌ Keeper submission lookup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to load your submissions."
        )

    finally:
        cur.close()
        conn.close()


# --- KEEPER: CORRECT AND RESUBMIT REJECTED WORK ---
@router.post(
    "/resubmit/{work_id}",
    tags=["Keeper Operations"],
    dependencies=[Depends(require_role(["The Keeper"]))]
)
async def resubmit_work(
    work_id: int,
    payload: dict,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        token_user_id = int(current_user.get("user_id"))

        cur.execute("""
            SELECT
                w.title, w.author, w.category, w.language, w.publisher,
                w.year, w.isbn, w.ddc, w.call_no,
                w.translation_compilation, w.genre, w.original_language,
                w.notes, w.proposal_reason, w.proposed_by, w.status
            FROM public.works w
            WHERE w.work_id = %s
              AND w.proposed_by = %s
            FOR UPDATE
        """, (work_id, token_user_id))

        work = cur.fetchone()

        if not work:
            raise HTTPException(
                status_code=404,
                detail="Rejected submission not found."
            )

        if str(work["status"]).upper() != "REJECTED":
            raise HTTPException(
                status_code=409,
                detail="Only a rejected Work can be corrected and resubmitted."
            )

        if _open_correction(cur, "WORK", work_id):
            raise HTTPException(
                status_code=409,
                detail="This work has fields marked for correction. Use the correction form to resubmit."
            )

        title = str(payload.get("title") or "").strip()
        language = str(payload.get("language") or "").strip()

        if not title or not language:
            raise HTTPException(
                status_code=400,
                detail="Title and language are required."
            )

        new_values = {
            "title": title,
            "author": payload.get("author"),
            "category": payload.get("category"),
            "language": language,
            "publisher": payload.get("publisher"),
            "year": payload.get("year"),
            "isbn": payload.get("isbn"),
            "ddc": payload.get("ddc"),
            "call_no": payload.get("call_no"),
            "translation_compilation": payload.get("translation_compilation"),
            "genre": payload.get("genre"),
            "original_language": payload.get("original_language"),
            "notes": payload.get("notes"),
            "proposal_reason": (
                str(payload.get("proposal_reason") or "").strip()
                or work.get("proposal_reason")
            ),
        }
        field_changes = {
            field: {"from": work.get(field), "to": new_value}
            for field, new_value in new_values.items()
            if _audit_norm(work.get(field)) != _audit_norm(new_value)
        }

        cur.execute("""
            UPDATE public.works
            SET
                title = %s,
                author = %s,
                category = %s,
                language = %s,
                publisher = %s,
                year = %s,
                isbn = %s,
                ddc = %s,
                call_no = %s,
                translation_compilation = %s,
                genre = %s,
                original_language = %s,
                notes = %s,
                status = 'PENDING',
                approval_reason = NULL,
                approved_by = NULL,
                approved_at = NULL,
                proposal_reason = COALESCE(
                    NULLIF(%s, ''),
                    proposal_reason
                )
            WHERE work_id = %s
              AND proposed_by = %s
              AND status = 'REJECTED'
            RETURNING title
        """, (
            title,
            payload.get("author"),
            payload.get("category"),
            language,
            payload.get("publisher"),
            payload.get("year"),
            payload.get("isbn"),
            payload.get("ddc"),
            payload.get("call_no"),
            payload.get("translation_compilation"),
            payload.get("genre"),
            payload.get("original_language"),
            payload.get("notes"),
            str(payload.get("proposal_reason") or "").strip(),
            work_id,
            token_user_id
        ))

        updated = cur.fetchone()

        if not updated:
            raise HTTPException(
                status_code=409,
                detail="The rejected submission changed before it could be resubmitted."
            )

        cur.execute("""
            UPDATE public.items
            SET
                availability_status = 'PENDING',
                is_deleted = FALSE,
                deletion_reason = NULL,
                proposed_by = COALESCE(proposed_by, %s)
            WHERE work_id = %s
        """, (token_user_id, work_id))

        audit_ok = log_audit_activity(
            request=request,
            user_id=str(token_user_id),
            username=str(
                current_user.get("username")
                or current_user.get("name")
                or "Archive Operator"
            ),
            role=str(current_user.get("role") or "The Keeper"),
            designation=str(
                current_user.get("designation")
                or current_user.get("role")
                or "The Keeper"
            ),
            category="ARCHIVAL_GOVERNANCE",
            action_type="WORK_RESUBMIT",
            target_entity="WORK",
            target_id=str(work_id),
            endpoint=request.url.path,
            http_method="POST",
            justification=str(
                payload.get("proposal_reason")
                or "Corrected rejected proposal"
            ),
            diff_payload={
                "work_id": work_id,
                "title": updated["title"],
                "status": "PENDING",
                "changes": field_changes
            },
            extra_metadata={"resubmission": True},
            conn=conn
        )

        if not audit_ok:
            raise RuntimeError(
                "Audit record could not be written; operation rolled back"
            )
        
        conn.commit()

        return {
            "message": (
                f"Work '{updated['title']}' "
                "resubmitted for verification."
            ),
            "work_id": work_id,
            "status": "PENDING"
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        print(f"Work resubmission failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to resubmit the rejected Work."
        )

    finally:
        cur.close()
        conn.close()

# --- KEEPER: CORRECT AND RESUBMIT REJECTED ITEM ---
@router.post(
    "/resubmit-item/{serial_no}",
    tags=["Keeper Operations"],
    dependencies=[Depends(require_role(["The Keeper"]))]
)
async def resubmit_item(
    serial_no: int,
    payload: dict,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        token_user_id = int(current_user.get("user_id"))

        cur.execute("""
            SELECT
                i.serial_no,
                i.accession_no,
                i.work_id,
                i.call_no,
                i.language_id,
                i.availability_status,
                i.is_deleted,
                i.proposed_by,
                w.title,
                w.status AS work_status
            FROM public.items i
            INNER JOIN public.works w
                ON w.work_id = i.work_id
            WHERE i.serial_no = %s
              AND i.proposed_by = %s
        """, (serial_no, token_user_id))

        item = cur.fetchone()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Rejected Item not found."
            )

        if str(item["availability_status"]).upper() != "REJECTED":
            raise HTTPException(
                status_code=409,
                detail="Only a rejected Item can be corrected and resubmitted."
            )

        if str(item["work_status"]).upper() != "APPROVED":
            raise HTTPException(
                status_code=409,
                detail="The parent Work is not approved and this Item cannot be resubmitted."
            )

        if _open_correction(cur, "ITEM", serial_no):
            raise HTTPException(
                status_code=409,
                detail="This item has fields marked for correction. Use the correction form to resubmit."
            )

        cur.execute("""
            UPDATE public.items
            SET
                availability_status = 'PENDING',
                is_deleted = FALSE,
                deletion_reason = NULL
            WHERE serial_no = %s
              AND proposed_by = %s
              AND availability_status = 'REJECTED'
              AND is_deleted = TRUE
            RETURNING
                serial_no,
                accession_no,
                work_id,
                availability_status
        """, (serial_no, token_user_id))

        updated = cur.fetchone()

        if not updated:
            raise HTTPException(
                status_code=409,
                detail="The rejected Item changed before it could be resubmitted."
            )

        audit_ok = log_audit_activity(
            request=request,
            user_id=str(token_user_id),
            username=str(
                current_user.get("username")
                or current_user.get("name")
                or "Archive Operator"
            ),
            role=str(current_user.get("role") or "The Keeper"),
            designation=str(
                current_user.get("designation")
                or current_user.get("role")
                or "The Keeper"
            ),
            category="ARCHIVAL_GOVERNANCE",
            action_type="ITEM_RESUBMIT",
            target_entity="ITEM",
            target_id=str(serial_no),
            endpoint=request.url.path,
            http_method="POST",
            justification=str(
                payload.get("reason")
                or "Corrected rejected Item"
            ),
            diff_payload={
                "serial_no": serial_no,
                "accession_no": updated["accession_no"],
                "work_id": updated["work_id"],
                "status": "PENDING"
            },
            extra_metadata={
                "resubmission": True
            },
            conn=conn
        )

        if not audit_ok:
            raise RuntimeError(
                "Audit record could not be written; operation rolled back"
            )

        conn.commit()

        return {
            "message": f"Item #{serial_no} resubmitted for verification.",
            "serial_no": serial_no,
            "status": "PENDING"
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        print(f"Item resubmission failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to resubmit the rejected Item."
        )

    finally:
        cur.close()
        conn.close()

# --- DOCKET: MATTER HISTORY (from the audit ledger) ---
@router.get(
    "/history/{entity}/{entity_id}",
    tags=["Docket"],
    dependencies=[Depends(require_role(["The Chief", "The Keeper"]))]
)
def get_matter_history(
    entity: str,
    entity_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    entity_key = entity.strip().upper()
    if entity_key not in ("WORK", "ITEM"):
        raise HTTPException(
            status_code=400,
            detail="Entity must be 'work' or 'item'."
        )

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        is_chief = str(current_user.get("role") or "").strip().lower() == "the chief"

        if not is_chief:
            user_id = int(current_user.get("user_id"))

            if entity_key == "WORK":
                cur.execute("""
                    SELECT 1 FROM public.works
                    WHERE work_id = %s AND proposed_by = %s
                """, (entity_id, user_id))
            else:
                cur.execute("""
                    SELECT 1
                    FROM public.items i
                    INNER JOIN public.works w ON w.work_id = i.work_id
                    WHERE i.serial_no = %s
                      AND (i.proposed_by = %s OR w.proposed_by = %s)
                """, (entity_id, user_id, user_id))

            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Matter not found.")

        cur.execute("""
            SELECT id, "timestamp", username, role,
                   action_type, justification, diff_payload
            FROM audit_activities
            WHERE target_entity = %s
              AND target_id = %s
              AND diff_payload IS NOT NULL
              AND action_type IN (
                  'ACCESSION_WORK', 'ACCESSION_ITEM', 'CURATOR_DECISION',
                  'ITEM_APPROVE', 'ITEM_REJECT',
                  'WORK_RESUBMIT', 'ITEM_RESUBMIT',
                  'REVIEW_NOTE'
              )
            ORDER BY sequence_id ASC
        """, (entity_key, str(entity_id)))

        events = [
            event
            for event in (_history_event(row) for row in cur.fetchall())
            if event
        ]
        return events

    except HTTPException:
        raise

    except Exception as e:
        print(f"Matter history lookup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to load the history."
        )

    finally:
        cur.close()
        conn.close()


# --- CHIEF WORK APPROVAL QUEUE ---
@router.get(
    "/pending-works",
    tags=["Admin Operations"],
    dependencies=[Depends(require_role(["The Chief"]))]
)
def list_pending_works(request: Request, current_user: dict = Depends(get_current_user)):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT
                w.work_id,
                w.title,
                w.author,
                w.publisher,
                w.language,
                w.category,
                w.genre,
                w.year,
                w.isbn,
                w.ddc,
                w.call_no,
                w.original_language,
                w.translation_compilation,
                w.notes,
                w.proposed_by,
                w.proposal_reason,
                w.created_at,
                COALESCE(
                    (SELECT MAX(a."timestamp") FROM audit_activities a
                      WHERE a.target_entity = 'WORK'
                        AND a.target_id = w.work_id::text
                        AND a.action_type IN ('ACCESSION_WORK', 'WORK_RESUBMIT')),
                    w.created_at
                ) AS waiting_since,
                u.name AS proposer_name
            FROM public.works w
            LEFT JOIN public.users u
                ON u.user_id = w.proposed_by
            WHERE w.status = 'PENDING'
            ORDER BY w.created_at DESC, w.work_id DESC
        """)
        return cur.fetchall()
    except Exception as e:
        print(f"❌ Pending work lookup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to load pending works."
        )
    finally:
        cur.close()
        conn.close()


# --- CHIEF ITEM APPROVAL QUEUE ---
@router.get(
    "/pending-items",
    tags=["Admin Operations"],
    dependencies=[Depends(require_role(["The Chief"]))]
)
def list_pending_items(request: Request, current_user: dict = Depends(get_current_user)):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT
                i.serial_no,
                i.accession_no,
                i.work_id,
                i.call_no,
                i.language_id,
                i.availability_status,
                i.created_at,
                COALESCE(
                    (SELECT MAX(a."timestamp") FROM audit_activities a
                      WHERE a.target_entity = 'ITEM'
                        AND a.target_id = i.serial_no::text
                        AND a.action_type IN ('ACCESSION_ITEM', 'ITEM_RESUBMIT')),
                    i.created_at
                ) AS waiting_since,
                w.title,
                w.author,
                w.language,
                w.category
            FROM public.items i
            INNER JOIN public.works w
                ON i.work_id = w.work_id
            WHERE i.availability_status = 'PENDING'
              AND i.is_deleted = FALSE
              AND w.status = 'APPROVED'
            ORDER BY i.serial_no DESC
        """)
        return cur.fetchall()
    except Exception as e:
        print(f"❌ Pending item lookup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to load pending items."
        )
    finally:
        cur.close()
        conn.close()


# --- CHIEF ITEM APPROVAL OPERATIONS ---
@router.post(
    "/approve-item/{serial_no}",
    tags=["Admin Operations"],
    dependencies=[Depends(require_role(["The Chief"]))]
)
async def approve_item(
    serial_no: int,
    action: str,
    reason: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    decision = action.strip().upper()
    if decision not in ("APPROVE", "REJECT"):
        raise HTTPException(
            status_code=400,
            detail="Action must be APPROVE or REJECT."
        )

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if decision == "APPROVE":
            cur.execute("""
                UPDATE public.items
                SET availability_status = 'AVAILABLE'
                WHERE serial_no = %s
                  AND availability_status = 'PENDING'
                  AND is_deleted = FALSE
                RETURNING serial_no, accession_no, work_id
            """, (serial_no,))
        else:
            cur.execute("""
                UPDATE public.items
                SET availability_status = 'REJECTED',
                is_deleted = TRUE,
                deletion_reason = %s
                WHERE serial_no = %s
                  AND availability_status = 'PENDING'
                  AND is_deleted = FALSE
                RETURNING serial_no, accession_no, work_id
            """, (reason, serial_no))

        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Pending Item not found."
            )

        notification_message = (
            f"PROPOSAL APPROVED: Item #{serial_no} has been approved by "
            f"The Chief and is now live in the Library Catalogue."
            if decision == "APPROVE"
            else
            f"PROPOSAL REQUIRES CORRECTION: Item #{serial_no} was rejected "
            f"by The Chief.\n\n"
            f"Reason: {reason}\n\n"
            f"Action: Correct the proposal and RESUBMIT FOR VERIFICATION."
        )
        cur.execute("""
            INSERT INTO public.chief_notifications (identity_id, message)
            SELECT u.identity_id, %s
            FROM public.items i
            INNER JOIN public.users u
                ON u.user_id = i.proposed_by
            WHERE i.serial_no = %s
              AND u.identity_id IS NOT NULL
        """, (notification_message, serial_no))

        audit_ok = log_audit_activity(
            request=request,
            user_id=str(current_user.get("user_id", "UNKNOWN")),
            username=str(current_user.get("username") or current_user.get("name") or "Archive Operator"),
            role=str(current_user.get("role", "The Chief")),
            designation=str(current_user.get("role", "The Chief")),
            category="ARCHIVAL_GOVERNANCE",
            action_type=f"ITEM_{decision}",
            target_entity="ITEM",
            target_id=str(serial_no),
            endpoint=request.url.path,
            http_method="POST",
            justification=reason,
            diff_payload={
                "serial_no": serial_no,
                "accession_no": row["accession_no"],
                "work_id": row["work_id"],
                "decision": decision
            },
            extra_metadata={"reason": reason},
            conn=conn
        )

        if not audit_ok:
            raise RuntimeError(
                "Audit record could not be written; operation rolled back"
            )

        conn.commit()

        return {
            "message": f"Item {serial_no} {decision}.",
            "serial_no": row["serial_no"],
            "accession_no": row["accession_no"],
            "work_id": row["work_id"],
            "decision": decision
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"❌ Item approval failed: {e}")
        raise HTTPException(status_code=500, detail="Item approval failed.")
    finally:
        cur.close()
        conn.close()


@router.get("/{serial_no}")
def get_book(request: Request, serial_no: int, current_user: dict = Depends(get_current_user)):
    conn = get_connection(request=request)
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
            WHERE i.serial_no = %s AND i.is_deleted = FALSE AND w.status = 'APPROVED'
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
    request: Request, page: int = 1, 
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
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        user_role = current_user.get('role', 'GUEST')
        offset = (page - 1) * limit
        safe_order = "ASC" if order.lower() == "asc" else "DESC"
        filters = []
        params = []

        filters.append("i.is_deleted = FALSE")
        filters.append("w.status = 'APPROVED'")

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

# --- 2. UPDATE LEDGER RECORD ---
@router.patch("/{serial_no}", dependencies=[Depends(require_role(["The Chief"]))])
@audit_action(
    "UPDATE_LEDGER",
    target_entity="Item",
    target_id_param="serial_no",
    reason_param="x_change_reason"
)
async def update_ledger_record(
    serial_no: int,
    payload: dict,
    request: Request,
    current_user: dict = Depends(get_current_user),
    x_change_reason: Optional[str] = Header(default="Routine operational adjustment"),
    x_device_id: Optional[str] = Header(default="Desktop Browser Workstation"),
    x_ip_address: Optional[str] = Header(default="127.0.0.1")
):    
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        token_user_id = int(current_user.get("user_id"))
        cur.execute("SELECT name FROM public.users WHERE user_id = %s", (token_user_id,))
        user_row = cur.fetchone()
        real_name = user_row[0] if user_row else (current_user.get("username") or "Archive Operator")
        real_role = current_user.get("role") or "The Chief"

        cur.execute("SET LOCAL request.jwt.claim.username = %s;", (real_name,))
        cur.execute("SET LOCAL request.jwt.claim.role = %s;", (real_role,))
        cur.execute("SET LOCAL request.jwt.claim.user_id = %s;", (str(token_user_id),))
        cur.execute("SET LOCAL request.custom.change_reason = %s;", (x_change_reason,))
        cur.execute("SET LOCAL request.custom.device_id = %s;", (x_device_id,))
        cur.execute("SET LOCAL request.custom.ip_address = %s;", (x_ip_address,))

        cur.execute("""
            UPDATE public.items SET 
                shelf = NULLIF(BTRIM(%s), '')
            WHERE serial_no = %s 
            RETURNING work_id
        """, (payload.get('shelf'), serial_no))
        
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

        raw_year = payload.get('year')
        safe_year = None
        if raw_year is not None and str(raw_year).strip() != "":
            try:
                safe_year = int(str(raw_year).strip())
            except ValueError:
                safe_year = None

        cur.execute("""
            UPDATE public.works SET 
                title = COALESCE(NULLIF(BTRIM(%s), ''), title),
                author = COALESCE(NULLIF(BTRIM(%s), ''), 'Unknown'),
                publisher = NULLIF(BTRIM(%s), ''),
                isbn = NULLIF(BTRIM(%s), ''),
                ddc = NULLIF(BTRIM(%s), ''),
                year = %s,
                category = NULLIF(BTRIM(%s), ''),
                genre = NULLIF(BTRIM(%s), ''),
                language = COALESCE(NULLIF(BTRIM(%s), ''), language),
                original_language = NULLIF(BTRIM(%s), ''),
                translation_compilation = NULLIF(BTRIM(%s), ''),
                notes = NULLIF(BTRIM(%s), ''),
                call_no = COALESCE(NULLIF(BTRIM(%s), ''), call_no)
            WHERE work_id = %s
        """, (
            payload.get('title'),
            payload.get('author'),
            payload.get('publisher'),
            payload.get('isbn'),
            payload.get('ddc'),
            safe_year,
            new_cat,
            payload.get('genre'),
            payload.get('language'),
            payload.get('original_language'),
            payload.get('translation_compilation'),
            payload.get('notes'),
            final_call_no,
            work_id
        ))

        if final_call_no:
            cur.execute("UPDATE public.items SET call_no = %s WHERE work_id = %s", (final_call_no, work_id))

        audit_ok = log_audit_activity(
            request=request,
            user_id=str(token_user_id),
            username=real_name,
            role=real_role,
            designation=real_role,
            category="CATALOGUE",
            action_type="UPDATE_LEDGER",
            target_entity="ITEM",
            target_id=str(serial_no),
            endpoint=request.url.path,
            http_method="PATCH",
            justification=x_change_reason,
            diff_payload={
                "serial_no": serial_no,
                "work_id": work_id,
                "updated_fields": {k: v for k, v in payload.items() if v is not None},
                "final_call_no": final_call_no
            },
            extra_metadata={
                "serial_no": serial_no,
                "work_id": work_id,
                "device_id": x_device_id
            },
            conn=conn
        )

        if not audit_ok:
            raise RuntimeError("Audit record could not be written; operation rolled back")
        
        conn.commit()
        return {"status": "success", "call_no": final_call_no}
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# --- 3. CURATOR DECISION ---
@router.post("/approve/{work_id}", tags=["Admin Operations"], dependencies=[Depends(require_role(["The Chief"]))])
@audit_action(
    "CURATOR_DECISION",
    category="ARCHIVAL_GOVERNANCE",
    target_entity="Work",
    target_id_param="work_id",
    reason_param="reason"
)
async def approve_work(
    work_id: int, action: str, reason: str, request: Request,
    current_user: dict = Depends(get_current_user)
):    
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        decision = action.strip().upper()
        if decision not in ("APPROVE", "REJECT"):
            raise HTTPException(
                status_code=400,
                detail="Action must be APPROVE or REJECT."
            )

        new_status = "APPROVED" if decision == "APPROVE" else "REJECTED"

        cur.execute("""
            UPDATE public.works
            SET status = %s,
                approved_by = %s,
                approval_reason = %s,
                approved_at = CURRENT_TIMESTAMP
            WHERE work_id = %s
              AND status = 'PENDING'
            RETURNING title
        """, (new_status, current_user['user_id'], reason, work_id))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Work not found.")

        work_title = row[0]
        if new_status == "APPROVED":
            cur.execute("""
                UPDATE public.items
                SET availability_status = 'AVAILABLE',
                    is_deleted = FALSE
                WHERE work_id = %s
            """, (work_id,))
        else:
            cur.execute("""
                UPDATE public.items
                SET is_deleted = TRUE
                WHERE work_id = %s
            """, (work_id,))

        notification_message = (
            f"PROPOSAL APPROVED: Your proposal '{work_title}' has been "
            f"approved by The Chief and is now live in the Library Catalogue."
            if decision == "APPROVE"
            else
            f"PROPOSAL REQUIRES CORRECTION: Your proposal '{work_title}' "
            f"was rejected by The Chief.\n\n"
            f"Reason: {reason}\n\n"
            f"Action: Correct the proposal and RESUBMIT FOR VERIFICATION."
        )

        cur.execute("""
            INSERT INTO public.chief_notifications (
                identity_id,
                message
            )
            SELECT u.identity_id, %s
            FROM public.works w
            INNER JOIN public.users u
                ON u.user_id = w.proposed_by
            WHERE w.work_id = %s
              AND u.identity_id IS NOT NULL
        """, (notification_message, work_id))

        audit_ok = log_audit_activity(
            request=request,
            user_id=str(current_user.get("user_id", "UNKNOWN")),
            username=str(current_user.get("username") or current_user.get("name") or "Archive Operator"),
            role=str(current_user.get("role", "The Chief")),
            designation=str(current_user.get("designation") or current_user.get("role", "The Chief")),
            category="ARCHIVAL_GOVERNANCE",
            action_type="CURATOR_DECISION",
            target_entity="WORK",
            target_id=str(work_id),
            endpoint=request.url.path,
            http_method="POST",
            justification=reason,
            diff_payload={
                "work_id": work_id,
                "title": work_title,
                "decision": new_status,
                "reason": reason
            },
            extra_metadata={
                "work_id": work_id,
                "decision": new_status
            },
            conn=conn
        )

        if not audit_ok:
            raise RuntimeError(
                "Audit record could not be written; operation rolled back"
            )
        
        conn.commit()

        return {"message": f"Work '{work_title}' {new_status}."}
    except Exception as e:
        if conn: conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# --- 4. DEACCESSION ---
@router.delete("/{book_id}", tags=["Catalogue Operations"], dependencies=[Depends(require_role(["The Chief"]))])
@audit_action(
    "DEACCESSION",
    target_entity="Item",
    target_id_param="book_id",
    reason_param="reason"
)
async def soft_delete_book(
    book_id: int, reason: str, request: Request,
    current_user: dict = Depends(get_current_user)
):    
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE public.items 
            SET is_deleted = TRUE, deletion_reason = %s 
            WHERE serial_no = %s
            RETURNING work_id, accession_no
        """, (reason, book_id))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found.")

        work_id, accession_no = row

        audit_ok = log_audit_activity(
            request=request,
            user_id=str(current_user.get("user_id", "UNKNOWN")),
            username=str(current_user.get("username") or current_user.get("name") or "Archive Operator"),
            role=str(current_user.get("role", "The Chief")),
            designation=str(current_user.get("designation") or current_user.get("role", "The Chief")),
            category="CATALOGUE",
            action_type="DEACCESSION",
            target_entity="ITEM",
            target_id=str(book_id),
            endpoint=request.url.path,
            http_method="DELETE",
            justification=reason,
            diff_payload={
                "serial_no": book_id,
                "work_id": work_id,
                "accession_no": accession_no,
                "is_deleted": True,
                "deletion_reason": reason
            },
            extra_metadata={
                "serial_no": book_id,
                "accession_no": accession_no
            },
            conn=conn
        )

        if not audit_ok:
            raise RuntimeError(
                "Audit record could not be written; operation rolled back"
            )
        
        conn.commit()

        return {"status": "success"}
    except Exception as e:
        if conn: conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

@router.post("/check-duplicate")
def check_duplicate(request: Request, payload: DuplicateCheckRequest, current_user: dict = Depends(get_current_user)):
    conn = get_connection(request=request)
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


# ===========================================================================
# REVIEW & CORRECTION WORKFLOW (Items)
# ===========================================================================
ITEM_CORRECTABLE_FIELDS = ("work_id", "language_id")
MAX_NOTE_LENGTH = 2000

class ItemCorrectionRequest(BaseModel):
    fields: List[str]
    reason: str
    correction_note: Optional[str] = None

class ReviewNoteCreate(BaseModel):
    body: str

class ItemCorrectionSubmit(BaseModel):
    changes: dict = {}
    note: Optional[str] = None

def _actor_info(current_user: dict) -> dict:
    role = str(current_user.get("role") or "").strip()
    return {
        "user_id": int(current_user.get("user_id")),
        "name": str(
            current_user.get("username")
            or current_user.get("name")
            or "Archive Operator"
        ),
        "role": role,
        "is_chief": role.lower() == "the chief",
    }

def _clean_note(text, label: str = "Note", required: bool = False) -> str:
    value = str(text or "").strip()
    if required and not value:
        raise HTTPException(status_code=400, detail=f"{label} is required.")
    if len(value) > MAX_NOTE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"{label} is too long (maximum {MAX_NOTE_LENGTH} characters)."
        )
    return value

def _write_audit(
    request: Request,
    current_user: dict,
    conn,
    action_type: str,
    target_id,
    justification: str,
    diff: dict,
    extra: Optional[dict] = None,
    http_method: str = "POST",
    target_entity: str = "ITEM",
):
    ok = log_audit_activity(
        request=request,
        user_id=str(current_user.get("user_id", "UNKNOWN")),
        username=str(
            current_user.get("username")
            or current_user.get("name")
            or "Archive Operator"
        ),
        role=str(current_user.get("role") or "UNKNOWN"),
        designation=str(
            current_user.get("designation")
            or current_user.get("role")
            or "UNKNOWN"
        ),
        category="ARCHIVAL_GOVERNANCE",
        action_type=action_type,
        target_entity=target_entity,
        target_id=str(target_id),
        endpoint=request.url.path,
        http_method=http_method,
        justification=justification or "No reason given",
        diff_payload=diff,
        extra_metadata=extra or {},
        conn=conn
    )
    if not ok:
        raise RuntimeError(
            "Audit record could not be written; operation rolled back"
        )

def _log_refusal(
    request: Request,
    current_user: dict,
    action_type: str,
    target_id,
    detail: str,
    attempted: dict,
    entity: str = "ITEM",
):
    conn = None
    try:
        conn = get_connection(request=request)
        _write_audit(
            request, current_user, conn,
            action_type=action_type,
            target_id=target_id,
            justification=detail,
            diff={
                ("work_id" if entity == "WORK" else "serial_no"): target_id,
                "refused": True,
                "attempted": attempted,
            },
            extra={"refused": True},
            target_entity=entity,
        )
        conn.commit()
    except Exception as e:
        print(f"Refusal could not be audited: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def _load_item_for_review(cur, serial_no: int, actor: dict) -> dict:
    cur.execute("""
        SELECT
            i.serial_no, i.accession_no, i.work_id, i.call_no, i.language_id,
            i.availability_status, i.is_deleted, i.deletion_reason,
            i.proposed_by, i.created_at,
            w.title, w.author, w.language, w.category,
            w.status AS work_status,
            u.name AS proposer_name
        FROM public.items i
        INNER JOIN public.works w ON w.work_id = i.work_id
        LEFT JOIN public.users u ON u.user_id = i.proposed_by
        WHERE i.serial_no = %s
    """, (serial_no,))
    item = cur.fetchone()

    if not item or (
        not actor["is_chief"] and item["proposed_by"] != actor["user_id"]
    ):
        raise HTTPException(status_code=404, detail="Item not found.")
    return item

def _open_correction(cur, entity: str, entity_id: int):
    cur.execute("""
        SELECT request_id, field_names, requested_by, requested_by_name,
               requested_at, status
        FROM public.correction_requests
        WHERE entity = %s AND entity_id = %s AND status = 'OPEN'
        LIMIT 1
    """, (entity, entity_id))
    return cur.fetchone()

def _notes_for(cur, entity: str, entity_id: int) -> list:
    cur.execute("""
        SELECT note_id, request_id, kind, author_name, author_role,
               body, created_at
        FROM public.review_notes
        WHERE entity = %s AND entity_id = %s
        ORDER BY note_id ASC
    """, (entity, entity_id))
    return [dict(row) for row in cur.fetchall()]

def _item_editable_fields(actor: dict, status_value: str, correction) -> list:
    if actor["is_chief"] or status_value != "REJECTED":
        return []
    if correction:
        return [
            f for f in correction["field_names"] if f in ITEM_CORRECTABLE_FIELDS
        ]
    return list(ITEM_CORRECTABLE_FIELDS)

# --- REVIEW FORM DATA (Chief + owning Keeper) ---
@router.get(
    "/review/item/{serial_no}",
    tags=["Docket"],
    dependencies=[Depends(require_role(["The Chief", "The Keeper"]))]
)
def get_item_review(
    serial_no: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        actor = _actor_info(current_user)
        item = _load_item_for_review(cur, serial_no, actor)
        correction = _open_correction(cur, "ITEM", serial_no)
        notes = _notes_for(cur, "ITEM", serial_no)
        status_value = str(item["availability_status"]).upper()

        _write_audit(
            request, current_user, conn,
            action_type="ITEM_REVIEW_VIEWED",
            target_id=serial_no,
            justification="Opened the item review form",
            diff={"serial_no": serial_no, "status": status_value},
            http_method="GET",
        )
        conn.commit()

        return {
            "serial_no": item["serial_no"],
            "accession_no": item["accession_no"],
            "work_id": item["work_id"],
            "call_no": item["call_no"],
            "language_id": item["language_id"],
            "status": status_value,
            "rejection_reason": item["deletion_reason"],
            "proposed_by": item["proposed_by"],
            "proposer_name": item["proposer_name"],
            "created_at": item["created_at"],
            "work": {
                "title": item["title"],
                "author": item["author"],
                "language": item["language"],
                "category": item["category"],
                "status": item["work_status"],
            },
            "correctable_fields": list(ITEM_CORRECTABLE_FIELDS),
            "correction": (
                {
                    "request_id": correction["request_id"],
                    "fields": list(correction["field_names"]),
                    "requested_by": correction["requested_by_name"],
                    "requested_at": correction["requested_at"],
                }
                if correction else None
            ),
            "legacy_rejection": status_value == "REJECTED" and correction is None,
            "editable_fields": _item_editable_fields(actor, status_value, correction),
            "notes": notes,
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"Item review lookup failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to load the item review.")
    finally:
        cur.close()
        conn.close()

# --- CHIEF: SEND AN ITEM BACK WITH MARKED FIELDS ---
@router.post(
    "/review/item/{serial_no}/request-correction",
    tags=["Admin Operations"],
    dependencies=[Depends(require_role(["The Chief"]))]
)
async def request_item_correction(
    serial_no: int,
    payload: ItemCorrectionRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    reason = _clean_note(payload.reason, "A reason", required=True)
    correction_note = _clean_note(payload.correction_note, "Correction note")

    fields = []
    for field in payload.fields:
        key = str(field).strip()
        if key not in ITEM_CORRECTABLE_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=f"'{key}' is not a field that can be marked for correction."
            )
        if key not in fields:
            fields.append(key)
    if not fields:
        raise HTTPException(
            status_code=400,
            detail="Mark at least one field that needs correction."
        )

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        actor = _actor_info(current_user)

        cur.execute("""
            UPDATE public.items
            SET availability_status = 'REJECTED',
                is_deleted = TRUE,
                deletion_reason = %s
            WHERE serial_no = %s
              AND availability_status = 'PENDING'
              AND is_deleted = FALSE
            RETURNING serial_no, accession_no, work_id
        """, (reason, serial_no))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Pending Item not found.")

        cur.execute("""
            INSERT INTO public.correction_requests
                (entity, entity_id, requested_by, requested_by_name, field_names)
            VALUES ('ITEM', %s, %s, %s, %s)
            RETURNING request_id
        """, (serial_no, actor["user_id"], actor["name"], fields))
        request_id = cur.fetchone()["request_id"]

        if correction_note:
            cur.execute("""
                INSERT INTO public.review_notes
                    (entity, entity_id, request_id, author_id,
                     author_name, author_role, kind, body)
                VALUES ('ITEM', %s, %s, %s, %s, %s, 'CHIEF_CORRECTION_NOTE', %s)
            """, (
                serial_no, request_id, actor["user_id"],
                actor["name"], actor["role"], correction_note
            ))

        message = (
            f"PROPOSAL REQUIRES CORRECTION: Item #{serial_no} was sent back "
            f"by The Chief.\n\nReason: {reason}\n\n"
            f"Fields to correct: {', '.join(fields)}"
        )
        if correction_note:
            message += f"\n\nNote from The Chief: {correction_note}"
        message += "\n\nAction: Correct the marked fields and RESUBMIT."
        cur.execute("""
            INSERT INTO public.chief_notifications (identity_id, message)
            SELECT u.identity_id, %s
            FROM public.items i
            INNER JOIN public.users u ON u.user_id = i.proposed_by
            WHERE i.serial_no = %s AND u.identity_id IS NOT NULL
        """, (message, serial_no))

        _write_audit(
            request, current_user, conn,
            action_type="ITEM_REJECT",
            target_id=serial_no,
            justification=reason,
            diff={
                "serial_no": serial_no,
                "accession_no": row["accession_no"],
                "work_id": row["work_id"],
                "decision": "REJECT",
                "request_id": request_id,
                "flagged_fields": fields,
                "correction_note": correction_note or None,
            },
            extra={"reason": reason, "flagged_fields": fields},
        )

        conn.commit()
        return {
            "message": f"Item #{serial_no} sent back for correction.",
            "serial_no": serial_no,
            "request_id": request_id,
            "flagged_fields": fields,
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"Item correction request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to send the item back for correction."
        )
    finally:
        cur.close()
        conn.close()

# --- NOTES (Chief, or the Keeper who owns the item) ---
@router.post(
    "/review/item/{serial_no}/note",
    tags=["Docket"],
    dependencies=[Depends(require_role(["The Chief", "The Keeper"]))]
)
async def add_item_review_note(
    serial_no: int,
    payload: ReviewNoteCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    body = _clean_note(payload.body, "A note", required=True)

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        actor = _actor_info(current_user)
        _load_item_for_review(cur, serial_no, actor)
        correction = _open_correction(cur, "ITEM", serial_no)
        kind = "CHIEF_NOTE" if actor["is_chief"] else "KEEPER_NOTE"

        cur.execute("""
            INSERT INTO public.review_notes
                (entity, entity_id, request_id, author_id,
                 author_name, author_role, kind, body)
            VALUES ('ITEM', %s, %s, %s, %s, %s, %s, %s)
            RETURNING note_id
        """, (
            serial_no,
            correction["request_id"] if correction else None,
            actor["user_id"], actor["name"], actor["role"], kind, body
        ))
        note_id = cur.fetchone()["note_id"]

        _write_audit(
            request, current_user, conn,
            action_type="REVIEW_NOTE",
            target_id=serial_no,
            justification=body,
            diff={"serial_no": serial_no, "note_id": note_id, "kind": kind},
            extra={"note_id": note_id},
        )

        conn.commit()
        return {"note_id": note_id, "kind": kind}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"Item note failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to save the note.")
    finally:
        cur.close()
        conn.close()

# --- KEEPER: CORRECT THE MARKED FIELDS AND RESUBMIT ---
@router.post(
    "/review/item/{serial_no}/resubmit-corrected",
    tags=["Keeper Operations"],
    dependencies=[Depends(require_role(["The Keeper"]))]
)
async def resubmit_corrected_item(
    serial_no: int,
    payload: ItemCorrectionSubmit,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    note = _clean_note(payload.note, "Note")
    requested = payload.changes or {}

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        actor = _actor_info(current_user)
        item = _load_item_for_review(cur, serial_no, actor)

        if str(item["availability_status"]).upper() != "REJECTED":
            raise HTTPException(
                status_code=409,
                detail="Only a rejected Item can be corrected and resubmitted."
            )
        if str(item["work_status"]).upper() != "APPROVED":
            raise HTTPException(
                status_code=409,
                detail="The parent Work is not approved and this Item cannot be resubmitted."
            )

        correction = _open_correction(cur, "ITEM", serial_no)
        allowed = _item_editable_fields(actor, "REJECTED", correction)

        blocked = [key for key in requested if key not in allowed]
        if blocked:
            detail = (
                "These fields were not marked for correction and cannot be "
                f"changed: {', '.join(blocked)}."
            )
            conn.rollback()
            _log_refusal(
                request, current_user, "ITEM_CORRECTION_REFUSED",
                serial_no, detail, {k: requested[k] for k in blocked}
            )
            raise HTTPException(status_code=403, detail=detail)

        new_values = {}
        if "language_id" in requested:
            language_value = str(requested["language_id"] or "").strip()
            if not language_value:
                raise HTTPException(
                    status_code=400, detail="Language Profile cannot be empty."
                )
            new_values["language_id"] = language_value
        if "work_id" in requested:
            try:
                new_values["work_id"] = int(str(requested["work_id"]).strip())
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail="Authorized Work ID must be a numeric Work ID."
                )

        field_changes = {
            field: {"from": item.get(field), "to": value}
            for field, value in new_values.items()
            if _audit_norm(item.get(field)) != _audit_norm(value)
        }

        if not field_changes and not note:
            raise HTTPException(
                status_code=400,
                detail="Change a marked field or add a note explaining why nothing needs changing."
            )

        accession_no = item["accession_no"]
        call_no = item["call_no"]
        final_work_id = item["work_id"]
        final_language_id = new_values.get("language_id", item["language_id"])

        if "work_id" in field_changes:
            cur.execute("""
                SELECT work_id, language, call_no, status
                FROM public.works WHERE work_id = %s
            """, (new_values["work_id"],))
            new_work = cur.fetchone()
            if not new_work:
                raise HTTPException(
                    status_code=404, detail="Authorized catalogued work not found."
                )
            if str(new_work["status"]).upper() != "APPROVED":
                raise HTTPException(
                    status_code=409,
                    detail="That Work is not yet approved and cannot receive this copy."
                )

            prefix = get_language_prefix(new_work["language"])
            cur.execute("""
                UPDATE public.language_registry
                SET last_number = last_number + 1
                WHERE TRIM(prefix) = %s
                RETURNING last_number;
            """, (prefix,))
            row = cur.fetchone()
            if not row:
                cur.execute("""
                    INSERT INTO public.language_registry (language, prefix, last_number)
                    VALUES (%s, %s, 1)
                    RETURNING last_number;
                """, (new_work["language"].strip(), prefix))
                row = cur.fetchone()
            counter = row[0]
            accession_no = f"{prefix}-{counter}"
            call_no = new_work["call_no"]
            final_work_id = new_work["work_id"]
            field_changes["accession_no"] = {
                "from": item["accession_no"], "to": accession_no
            }
            field_changes["call_no"] = {"from": item["call_no"], "to": call_no}

        cur.execute("""
            UPDATE public.items
            SET work_id = %s,
                accession_no = %s,
                call_no = %s,
                language_id = %s,
                availability_status = 'PENDING',
                is_deleted = FALSE,
                deletion_reason = NULL
            WHERE serial_no = %s
              AND proposed_by = %s
              AND availability_status = 'REJECTED'
            RETURNING serial_no
        """, (
            final_work_id, accession_no, call_no, final_language_id,
            serial_no, actor["user_id"]
        ))
        if not cur.fetchone():
            raise HTTPException(
                status_code=409,
                detail="The rejected Item changed before it could be resubmitted."
            )

        if correction:
            cur.execute("""
                UPDATE public.correction_requests
                SET status = 'RESOLVED', resolved_at = now(), resolved_by = %s
                WHERE request_id = %s AND status = 'OPEN'
            """, (actor["user_id"], correction["request_id"]))

        if note:
            cur.execute("""
                INSERT INTO public.review_notes
                    (entity, entity_id, request_id, author_id,
                     author_name, author_role, kind, body)
                VALUES ('ITEM', %s, %s, %s, %s, %s, 'KEEPER_NOTE', %s)
                RETURNING note_id
            """, (
                serial_no,
                correction["request_id"] if correction else None,
                actor["user_id"], actor["name"], actor["role"], note
            ))
            note_id = cur.fetchone()["note_id"]
            _write_audit(
                request, current_user, conn,
                action_type="REVIEW_NOTE",
                target_id=serial_no,
                justification=note,
                diff={"serial_no": serial_no, "note_id": note_id, "kind": "KEEPER_NOTE"},
                extra={"note_id": note_id},
            )

        _write_audit(
            request, current_user, conn,
            action_type="ITEM_RESUBMIT",
            target_id=serial_no,
            justification=(
                "Corrected the marked fields and resubmitted"
                if field_changes else "Resubmitted without field changes"
            ),
            diff={
                "serial_no": serial_no,
                "accession_no": accession_no,
                "work_id": final_work_id,
                "status": "PENDING",
                "changes": field_changes,
                "request_id": correction["request_id"] if correction else None,
            },
            extra={"resubmission": True, "legacy_rejection": correction is None},
        )

        conn.commit()
        return {
            "message": f"Item #{serial_no} resubmitted for verification.",
            "serial_no": serial_no,
            "status": "PENDING",
            "changed_fields": list(field_changes.keys()),
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"Item correction resubmission failed: {e}")
        raise HTTPException(
            status_code=500, detail="Unable to resubmit the corrected Item."
        )
    finally:
        cur.close()
        conn.close()


# ===========================================================================
# REVIEW & CORRECTION WORKFLOW (Works)
# ===========================================================================
WORK_CORRECTABLE_FIELDS = (
    "title", "author", "category", "language", "publisher", "year", "isbn",
    "ddc", "call_no", "translation_compilation", "genre",
    "original_language", "notes", "proposal_reason",
)

class WorkCorrectionRequest(BaseModel):
    fields: List[str]
    reason: str
    correction_note: Optional[str] = None

class WorkCorrectionSubmit(BaseModel):
    changes: dict = {}
    note: Optional[str] = None

def _work_editable_fields(actor: dict, status_value: str, correction) -> list:
    if actor["is_chief"] or status_value != "REJECTED":
        return []
    if correction:
        return [
            f for f in correction["field_names"] if f in WORK_CORRECTABLE_FIELDS
        ]
    return list(WORK_CORRECTABLE_FIELDS)

def _load_work_for_review(cur, work_id: int, actor: dict) -> dict:
    cur.execute("""
        SELECT
            w.work_id, w.title, w.author, w.category, w.language,
            w.publisher, w.year, w.isbn, w.ddc, w.call_no,
            w.translation_compilation, w.genre, w.original_language,
            w.notes, w.proposal_reason, w.status, w.approval_reason,
            w.proposed_by, w.created_at,
            u.name AS proposer_name,
            (SELECT COUNT(*) FROM public.items i
              WHERE i.work_id = w.work_id) AS item_count
        FROM public.works w
        LEFT JOIN public.users u ON u.user_id = w.proposed_by
        WHERE w.work_id = %s
        FOR UPDATE OF w
    """, (work_id,))
    work = cur.fetchone()

    if not work or (
        not actor["is_chief"] and work["proposed_by"] != actor["user_id"]
    ):
        raise HTTPException(status_code=404, detail="Work not found.")
    return work

def _clean_work_value(key: str, value):
    if key == "year":
        text = str(value if value is not None else "").strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            raise HTTPException(status_code=400, detail="Year must be a whole number.")
    text = str(value if value is not None else "").strip()
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail=f"'{key}' is too long.")
    if key in ("title", "language") and not text:
        raise HTTPException(
            status_code=400,
            detail="Title and language cannot be empty."
        )
    return text or None

# --- REVIEW FORM DATA (Chief + owning Keeper) ---
@router.get(
    "/review/work/{work_id}",
    tags=["Docket"],
    dependencies=[Depends(require_role(["The Chief", "The Keeper"]))]
)
def get_work_review(
    work_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        actor = _actor_info(current_user)
        work = _load_work_for_review(cur, work_id, actor)
        correction = _open_correction(cur, "WORK", work_id)
        status_value = str(work["status"] or "").upper()

        _write_audit(
            request, current_user, conn,
            action_type="WORK_REVIEW_VIEWED",
            target_id=work_id,
            justification="Opened the work review form",
            diff={"work_id": work_id, "status": status_value},
            http_method="GET",
            target_entity="WORK",
        )
        conn.commit()

        values = {key: work[key] for key in WORK_CORRECTABLE_FIELDS}
        return {
            "work_id": work["work_id"],
            "status": status_value,
            "values": values,
            "rejection_reason": (
                work["approval_reason"] if status_value == "REJECTED" else None
            ),
            "proposed_by": work["proposed_by"],
            "proposer_name": work["proposer_name"],
            "created_at": work["created_at"],
            "item_count": work["item_count"],
            "correctable_fields": list(WORK_CORRECTABLE_FIELDS),
            "correction": (
                {
                    "request_id": correction["request_id"],
                    "fields": list(correction["field_names"]),
                    "requested_by": correction["requested_by_name"],
                    "requested_at": correction["requested_at"],
                }
                if correction else None
            ),
            "legacy_rejection": status_value == "REJECTED" and correction is None,
            "editable_fields": _work_editable_fields(actor, status_value, correction),
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"Work review lookup failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to load the work review.")
    finally:
        cur.close()
        conn.close()

# --- CHIEF: SEND A WORK BACK WITH MARKED FIELDS ---
@router.post(
    "/review/work/{work_id}/request-correction",
    tags=["Admin Operations"],
    dependencies=[Depends(require_role(["The Chief"]))]
)
async def request_work_correction(
    work_id: int,
    payload: WorkCorrectionRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    reason = _clean_note(payload.reason, "A reason", required=True)
    correction_note = _clean_note(payload.correction_note, "Correction note")

    fields = []
    for field in payload.fields:
        key = str(field).strip()
        if key not in WORK_CORRECTABLE_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=f"'{key}' is not a field that can be marked for correction."
            )
        if key not in fields:
            fields.append(key)
    if not fields:
        raise HTTPException(
            status_code=400,
            detail="Mark at least one field that needs correction."
        )

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        actor = _actor_info(current_user)

        cur.execute("""
            UPDATE public.works
            SET status = 'REJECTED',
                approved_by = %s,
                approval_reason = %s,
                approved_at = CURRENT_TIMESTAMP
            WHERE work_id = %s
              AND status = 'PENDING'
            RETURNING title
        """, (actor["user_id"], reason, work_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Pending Work not found.")
        work_title = row["title"]

        cur.execute("""
            UPDATE public.items SET is_deleted = TRUE WHERE work_id = %s
        """, (work_id,))

        cur.execute("""
            INSERT INTO public.correction_requests
                (entity, entity_id, requested_by, requested_by_name, field_names)
            VALUES ('WORK', %s, %s, %s, %s)
            RETURNING request_id
        """, (work_id, actor["user_id"], actor["name"], fields))
        request_id = cur.fetchone()["request_id"]

        if correction_note:
            cur.execute("""
                INSERT INTO public.review_notes
                    (entity, entity_id, request_id, author_id,
                     author_name, author_role, kind, body)
                VALUES ('WORK', %s, %s, %s, %s, %s, 'CHIEF_CORRECTION_NOTE', %s)
            """, (
                work_id, request_id, actor["user_id"],
                actor["name"], actor["role"], correction_note
            ))

        message = (
            f"PROPOSAL REQUIRES CORRECTION: Your proposal '{work_title}' "
            f"was sent back by The Chief.\n\nReason: {reason}\n\n"
            f"Fields to correct: {', '.join(fields)}"
        )
        if correction_note:
            message += f"\n\nNote from The Chief: {correction_note}"
        message += "\n\nAction: Correct the marked fields and RESUBMIT."
        cur.execute("""
            INSERT INTO public.chief_notifications (identity_id, message)
            SELECT u.identity_id, %s
            FROM public.works w
            INNER JOIN public.users u ON u.user_id = w.proposed_by
            WHERE w.work_id = %s AND u.identity_id IS NOT NULL
        """, (message, work_id))

        _write_audit(
            request, current_user, conn,
            action_type="CURATOR_DECISION",
            target_id=work_id,
            justification=reason,
            diff={
                "work_id": work_id,
                "title": work_title,
                "decision": "REJECTED",
                "reason": reason,
                "request_id": request_id,
                "flagged_fields": fields,
                "correction_note": correction_note or None,
            },
            extra={"work_id": work_id, "decision": "REJECTED", "flagged_fields": fields},
            target_entity="WORK",
        )

        conn.commit()
        return {
            "message": f"Work '{work_title}' sent back for correction.",
            "work_id": work_id,
            "request_id": request_id,
            "flagged_fields": fields,
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"Work correction request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to send the work back for correction."
        )
    finally:
        cur.close()
        conn.close()

# --- KEEPER: CORRECT THE MARKED FIELDS AND RESUBMIT ---
@router.post(
    "/review/work/{work_id}/resubmit-corrected",
    tags=["Keeper Operations"],
    dependencies=[Depends(require_role(["The Keeper"]))]
)
async def resubmit_corrected_work(
    work_id: int,
    payload: WorkCorrectionSubmit,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    note = _clean_note(payload.note, "Note")
    requested = payload.changes or {}

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        actor = _actor_info(current_user)
        work = _load_work_for_review(cur, work_id, actor)

        if str(work["status"] or "").upper() != "REJECTED":
            raise HTTPException(
                status_code=409,
                detail="Only a rejected Work can be corrected and resubmitted."
            )

        correction = _open_correction(cur, "WORK", work_id)
        allowed = _work_editable_fields(actor, "REJECTED", correction)

        blocked = [key for key in requested if key not in allowed]
        if blocked:
            detail = (
                "These fields were not marked for correction and cannot be "
                f"changed: {', '.join(blocked)}."
            )
            conn.rollback()
            _log_refusal(
                request, current_user, "WORK_CORRECTION_REFUSED",
                work_id, detail, {k: requested[k] for k in blocked},
                entity="WORK"
            )
            raise HTTPException(status_code=403, detail=detail)

        new_values = {
            key: _clean_work_value(key, value)
            for key, value in requested.items()
        }
        field_changes = {
            key: {"from": work.get(key), "to": value}
            for key, value in new_values.items()
            if _audit_norm(work.get(key)) != _audit_norm(value)
        }

        if not field_changes and not note:
            raise HTTPException(
                status_code=400,
                detail="Change a marked field or add a note explaining why nothing needs changing."
            )

        assignments = ", ".join(f"{key} = %s" for key in field_changes)
        params = [change["to"] for change in field_changes.values()]
        set_sql = (assignments + ", ") if assignments else ""
        cur.execute(f"""
            UPDATE public.works
            SET {set_sql}
                status = 'PENDING',
                approval_reason = NULL,
                approved_by = NULL,
                approved_at = NULL
            WHERE work_id = %s
              AND proposed_by = %s
              AND status = 'REJECTED'
            RETURNING title
        """, (*params, work_id, actor["user_id"]))
        updated = cur.fetchone()
        if not updated:
            raise HTTPException(
                status_code=409,
                detail="The rejected Work changed before it could be resubmitted."
            )

        cur.execute("""
            UPDATE public.items
            SET availability_status = 'PENDING',
                is_deleted = FALSE,
                deletion_reason = NULL,
                proposed_by = COALESCE(proposed_by, %s)
            WHERE work_id = %s
        """, (actor["user_id"], work_id))

        if correction:
            cur.execute("""
                UPDATE public.correction_requests
                SET status = 'RESOLVED', resolved_at = now(), resolved_by = %s
                WHERE request_id = %s AND status = 'OPEN'
            """, (actor["user_id"], correction["request_id"]))

        if note:
            cur.execute("""
                INSERT INTO public.review_notes
                    (entity, entity_id, request_id, author_id,
                     author_name, author_role, kind, body)
                VALUES ('WORK', %s, %s, %s, %s, %s, 'KEEPER_NOTE', %s)
                RETURNING note_id
            """, (
                work_id,
                correction["request_id"] if correction else None,
                actor["user_id"], actor["name"], actor["role"], note
            ))
            note_id = cur.fetchone()["note_id"]
            _write_audit(
                request, current_user, conn,
                action_type="REVIEW_NOTE",
                target_id=work_id,
                justification=note,
                diff={"work_id": work_id, "note_id": note_id, "kind": "KEEPER_NOTE"},
                extra={"note_id": note_id},
                target_entity="WORK",
            )

        _write_audit(
            request, current_user, conn,
            action_type="WORK_RESUBMIT",
            target_id=work_id,
            justification=(
                "Corrected the marked fields and resubmitted"
                if field_changes else "Resubmitted without field changes"
            ),
            diff={
                "work_id": work_id,
                "title": updated["title"],
                "status": "PENDING",
                "changes": field_changes,
                "request_id": correction["request_id"] if correction else None,
            },
            extra={"resubmission": True, "legacy_rejection": correction is None},
            target_entity="WORK",
        )

        conn.commit()
        return {
            "message": f"Work '{updated['title']}' resubmitted for verification.",
            "work_id": work_id,
            "status": "PENDING",
            "changed_fields": list(field_changes.keys()),
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"Work correction resubmission failed: {e}")
        raise HTTPException(
            status_code=500, detail="Unable to resubmit the corrected Work."
        )
    finally:
        cur.close()
        conn.close()