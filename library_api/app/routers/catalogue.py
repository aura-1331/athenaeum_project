# app/routers/catalogue.py

from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.auth import get_current_user, require_role
from app.database import get_connection
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor
from typing import Optional, List
from app.routers.accession_utils import get_language_prefix, get_category_code
from app.routers.authority import search_authority_records
from datetime import datetime

router = APIRouter(prefix="/catalogue", tags=["catalogue"])
class DuplicateCheckRequest(BaseModel):
    title: str
    author: Optional[str] = None
    language: Optional[str] = None
    isbn: Optional[str] = None
    
def generate_record_id(serial_no: int):
    year = datetime.now().year
    return f"AO-REC-{year}-{str(serial_no).zfill(6)}"


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

@router.get("/authors/search", response_model=List[str])
def search_authors(request: Request, q: str, current_user: dict = Depends(get_current_user)):
    """Legacy author lookup, backed by authority records rather than raw Work text."""
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        matches = search_authority_records(cur, q, limit=10, usable_only=True)
        return [match["preferred_name"] for match in matches if match.get("preferred_name")]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Author lookup failed: {type(e).__name__}: {e}")
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


def _history_event(row: dict) -> Optional[dict]:
    """Turn one audit_activities row into a docket timeline event, or skip it."""
    import json

    diff = row.get("diff_payload") or {}
    if isinstance(diff, str):
        try:
            diff = json.loads(diff)
        except (TypeError, ValueError):
            diff = {}
    if not isinstance(diff, dict):
        diff = {}

    action = row.get("action_type")

    if action in ("ACCESSION_WORK", "ACCESSION_ITEM"):
        registration_mode = str(diff.get("registration_mode") or "").upper()
        kind = "APPROVED" if registration_mode == "DIRECT_CHIEF" else "SUBMITTED"
    elif action == "CURATOR_DECISION":
        kind = "APPROVED" if str(diff.get("decision") or "").upper() == "APPROVED" else "REJECTED"
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
        "decision_action": diff.get("decision_action"),
        "at": at.isoformat() if hasattr(at, "isoformat") else (str(at) if at else None),
        "actor": row.get("username"),
        "actor_role": row.get("role"),
        "reason": None if kind == "SUBMITTED" else row.get("justification"),
        "changes": diff.get("changes"),
        "flagged_fields": diff.get("flagged_fields"),
        "correction_note": diff.get("correction_note"),
        "note_kind": diff.get("kind") if kind == "NOTE" else None,
    }


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
              AND (
                  target_entity <> 'WORK'
                  OR "timestamp" >= COALESCE(
                      (SELECT w.created_at FROM public.works w
                       WHERE w.work_id::text = audit_activities.target_id),
                      '-infinity'::timestamp
                  ) - interval '2 seconds'
              )
              AND diff_payload IS NOT NULL
              AND COALESCE(extra_metadata->>'audit_source', '') <> 'audit_action'
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


@router.get("")
def get_catalogue_exact(
    request: Request,
    page: int = 1,
    limit: int = 50,
    sort_by: str = "serial_no",
    order: str = "asc",
    title: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    language: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    return get_catalogue(
        request=request,
        page=page,
        limit=limit,
        sort_by=sort_by,
        order=order,
        title=title,
        author=author,
        genre=genre,
        language=language,
        category=category,
        q=q,
        current_user=current_user,
    )


@router.get("/")
def get_catalogue(
    request: Request,
    page: int = 1,
    limit: int = 50,
    sort_by: str = "serial_no",
    order: str = "asc",
    title: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    language: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be at least 1.")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100.")

    normalized_order = str(order or "").strip().lower()
    if normalized_order not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Order must be 'asc' or 'desc'.")
    safe_order = "ASC" if normalized_order == "asc" else "DESC"

    sort_columns = {
        "serial_no": "i.serial_no",
        "accession_no": "i.accession_no",
        "work_id": "i.work_id",
        "title": "w.title",
        "author": "w.author",
        "category": "w.category",
        "genre": "w.genre",
        "year": "w.year",
        "publisher": "w.publisher",
        "language": "w.language",
    }
    sort_key = str(sort_by or "serial_no").strip().lower()
    sort_column = sort_columns.get(sort_key)
    if not sort_column:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported sort field. Choose one of: {', '.join(sort_columns)}.",
        )

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        offset = (page - 1) * limit
        filters = [
            "i.is_deleted = FALSE",
            "UPPER(BTRIM(COALESCE(w.status, ''))) = 'APPROVED'",
            "UPPER(BTRIM(COALESCE(i.availability_status, ''))) NOT IN ('PENDING', 'REJECTED')",
        ]
        params = []

        if title:
            filters.append("w.title ILIKE %s")
            params.append(f"%{title}%")
        if author:
            filters.append("w.author ILIKE %s")
            params.append(f"%{author}%")
        if genre:
            filters.append("w.genre ILIKE %s")
            params.append(f"%{genre}%")
        # Exact (case-insensitive) match, so "Fiction" does not match "Non-Fiction".
        if language:
            filters.append("LOWER(BTRIM(w.language)) = LOWER(BTRIM(%s))")
            params.append(language)
        if category:
            filters.append("LOWER(BTRIM(w.category)) = LOWER(BTRIM(%s))")
            params.append(category)
        # One search box: title, author, call no., ISBN, publisher, accession no.
        if q and q.strip():
            like = f"%{q.strip()}%"
            filters.append(
                "(w.title ILIKE %s OR w.author ILIKE %s OR w.call_no ILIKE %s "
                "OR w.isbn ILIKE %s OR w.publisher ILIKE %s OR i.accession_no ILIKE %s)"
            )
            params.extend([like] * 6)

        where_clause = " AND ".join(filters)
        count_query = f"""
            SELECT COUNT(*)
            FROM public.items i
            INNER JOIN public.works w ON i.work_id = w.work_id
            WHERE {where_clause}
        """
        cur.execute(count_query, tuple(params))
        total_records = cur.fetchone()["count"]

        tie_breaker = "" if sort_column == "i.serial_no" else ", i.serial_no ASC"
        query = f"""
            SELECT
                i.serial_no, i.accession_no, i.work_id, w.title, w.author,
                w.category, w.genre, w.year, w.publisher,
                i.shelf, w.language AS language, w.isbn,
                w.ddc, w.call_no,
                w.notes, w.original_language, w.translation_compilation,
                w.original_author, w.original_title, w.translator, w.compiler_editor, w.work_nature,
                w.edition_statement, w.series_title, w.series_volume, w.lccn, w.oclc_no,
                w.subject_headings, w.target_audience_era, w.copyright_status,
                i.physical_condition, i.binding_type, i.provenance_source, 
                i.artifactual_notes, i.access_restrictions,
                i.extent_page_count, i.physical_dimensions,
                i.date_acquired, i.collection_fonds,
                i.digital_scan_available, i.ocr_status
            FROM public.items i
            INNER JOIN public.works w ON i.work_id = w.work_id
            WHERE {where_clause}
            ORDER BY {sort_column} {safe_order}{tie_breaker}
            LIMIT %s OFFSET %s
        """
        cur.execute(query, tuple(params + [limit, offset]))
        items = cur.fetchall()
        for item in items:
            item["record_id"] = generate_record_id(item["serial_no"])

        return {
            "data": items,
            "total": total_records,
            "page": page,
            "limit": limit,
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Catalogue lookup failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="Unable to load the catalogue.")
    finally:
        cur.close()
        conn.close()

@router.post("/check-duplicate")
def check_duplicate(request: Request, payload: DuplicateCheckRequest, current_user: dict = Depends(get_current_user)):
    title = payload.title.strip()
    author = (payload.author or "").strip()
    language = (payload.language or "").strip()
    isbn = "".join(ch for ch in (payload.isbn or "") if ch.isalnum()).upper()

    if not title:
        return {"severity": "none", "is_duplicate": False, "matches": []}

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        candidate_clauses = ["title ILIKE %s"]
        candidate_params = [f"%{title}%"]
        if isbn:
            candidate_clauses.append("UPPER(REGEXP_REPLACE(COALESCE(isbn, ''), '[^0-9Xx]', '', 'g')) = %s")
            candidate_params.append(isbn)

        cur.execute(f"""
            SELECT
                work_id, title, author, language, isbn, category, publisher, year, status
            FROM public.works
            WHERE ({' OR '.join(candidate_clauses)})
              AND COALESCE(status, '') <> 'REJECTED'
            ORDER BY work_id DESC
            LIMIT 50
        """, tuple(candidate_params))
        rows = cur.fetchall()

        def norm(value):
            return " ".join(str(value or "").strip().lower().split())

        def norm_isbn(value):
            return "".join(ch for ch in str(value or "") if ch.isalnum()).upper()

        matches = []
        for row in rows:
            evidence = []
            score = 0

            row_title = norm(row.get("title"))
            row_author = norm(row.get("author"))
            row_language = norm(row.get("language"))
            row_isbn = norm_isbn(row.get("isbn"))

            if isbn and row_isbn and isbn == row_isbn:
                evidence.append("Same ISBN")
                score += 70
            if title and row_title == norm(title):
                evidence.append("Same title")
                score += 45
            elif title and (norm(title) in row_title or row_title in norm(title)):
                evidence.append("Similar title")
                score += 25
            if author and row_author == norm(author):
                evidence.append("Same author")
                score += 30
            elif author and author.lower() in row_author:
                evidence.append("Similar author")
                score += 15
            if language and row_language == norm(language):
                evidence.append("Same language")
                score += 10

            if score < 25:
                continue

            matches.append({
                "work_id": row.get("work_id"),
                "title": row.get("title"),
                "author": row.get("author"),
                "language": row.get("language"),
                "isbn": row.get("isbn"),
                "category": row.get("category"),
                "publisher": row.get("publisher"),
                "year": row.get("year"),
                "status": row.get("status"),
                "score": min(score, 100),
                "evidence": evidence,
            })

        matches.sort(key=lambda item: item["score"], reverse=True)
        matches = matches[:10]

        top_score = matches[0]["score"] if matches else 0
        severity = "strong" if top_score >= 70 else "medium" if top_score >= 45 else "none"

        return {
            "severity": severity,
            "is_duplicate": severity == "strong",
            "score": top_score,
            "evidence": matches[0]["evidence"] if matches else [],
            "matches": matches,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Duplicate check failure: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Duplicate verification failed")
    finally:
        cur.close()
        conn.close()

@router.get("/{serial_no:int}")
def get_catalogue_item_detail(
    serial_no: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT
                i.serial_no, i.accession_no, i.work_id, w.title, w.author,
                w.category, w.genre, w.year, w.publisher,
                i.shelf, w.language AS language, w.isbn,
                w.ddc, w.call_no,
                w.notes, w.original_language, w.translation_compilation,
                w.original_author, w.original_title, w.translator, w.compiler_editor, w.work_nature,
                w.edition_statement, w.series_title, w.series_volume, w.lccn, w.oclc_no,
                w.subject_headings, w.target_audience_era, w.copyright_status,
                i.physical_condition, i.binding_type, i.provenance_source, 
                i.artifactual_notes, i.access_restrictions,
                i.extent_page_count, i.physical_dimensions,
                i.date_acquired, i.collection_fonds,
                i.digital_scan_available, i.ocr_status
            FROM public.items i
            INNER JOIN public.works w ON i.work_id = w.work_id
            WHERE i.serial_no = %s
              AND COALESCE(i.is_deleted, FALSE) = FALSE
              AND UPPER(BTRIM(COALESCE(w.status, ''))) = 'APPROVED'
              AND UPPER(BTRIM(COALESCE(i.availability_status, ''))) NOT IN ('PENDING', 'REJECTED')
        """, (serial_no,))
        
        item = cur.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Catalogue record not found.")
            
        item["record_id"] = generate_record_id(item["serial_no"])
        return item
        
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Catalogue item detail lookup failed: {exc}")
        raise HTTPException(status_code=500, detail="Unable to load the catalogue record.")
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
    "original_author", "original_title", "translator", "compiler_editor", "work_nature",
    "edition_statement", "series_title", "series_volume", "lccn", "oclc_no",
    "subject_headings", "target_audience_era", "copyright_status",
)