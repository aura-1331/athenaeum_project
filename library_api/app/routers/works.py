# app/routers/works.py
"""Work lifecycle and Work creation transaction support.

The public /catalogue/create-work endpoint currently delegates here so endpoint
compatibility is preserved while Work responsibility moves out of catalogue.py.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel, Field

from app.database import get_connection
from app.auth import get_current_user, require_role
from app.audit_utils import audit_action
from psycopg2.extras import RealDictCursor
from typing import List
from app.routers.authority import resolve_or_create_authority, validate_work_authority
from app.routers.accession_utils import get_language_prefix, get_category_code
from app.routers.review_utils import (
    _actor_info,
    _clean_note,
    _write_audit,
    _log_refusal,
    _open_correction,
    _notes_for,
    _audit_norm,
    _audit_diff,
    _audit_ledger,
    _audit_ledger_diff,
)


work_router = APIRouter(prefix="/catalogue", tags=["Works"])


class WorkCreate(BaseModel):
    title: str
    author: Optional[str] = "Unknown"
    authority_id: Optional[int] = None
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
    original_title: Optional[str] = None
    original_author: Optional[str] = None
    translator: Optional[str] = None
    compiler_editor: Optional[str] = None
    work_nature: Optional[str] = None
    edition_statement: Optional[str] = None
    series_title: Optional[str] = None
    series_volume: Optional[str] = None
    lccn: Optional[str] = None
    oclc_no: Optional[str] = None
    subject_headings: Optional[str] = None
    target_audience_era: Optional[str] = None
    copyright_status: Optional[str] = None
    notes: Optional[str] = None
    shelf: Optional[str] = None
    series_name: Optional[str] = None
    series_number: Optional[str] = None
    volume_number: Optional[str] = None
    related_work_id: Optional[int] = None
    
    # --- Incoming form fields for the initial physical copy ---
    extent_page_count: Optional[str] = None
    physical_dimensions: Optional[str] = None
    date_acquired: Optional[str] = None
    collection_fonds: Optional[str] = None
    physical_condition: Optional[str] = None
    binding_type: Optional[str] = None
    provenance_source: Optional[str] = None
    artifactual_notes: Optional[str] = None
    access_restrictions: Optional[str] = None
    digital_scan_available: Optional[bool] = False
    ocr_status: Optional[str] = "Unindexed"


class WorkDraftAuditPayload(BaseModel):
    draft_id: str
    action: str
    title: Optional[str] = None
    mode: Optional[str] = None
    fields: Optional[List[str]] = None
    changes: Optional[dict] = None
    saved_at: Optional[str] = None
    note: Optional[str] = None


def create_work_transaction(
    payload: WorkCreate,
    request: Request,
    current_user: dict,
    x_change_reason: Optional[str] = "New registration initialization sequencing",
    x_device_id: Optional[str] = "Desktop Browser Workstation",
    x_ip_address: Optional[str] = "127.0.0.1",
):
    """Create Work, authority relationship, initial Item and audit atomically.

    No commit occurs until every step succeeds. The existing /catalogue/create-work
    route remains the compatibility boundary during the refactor.

    Important: Work and Item business identifiers are database-managed by the
    transactional numbering functions installed by the Create Work migration.
    This function deliberately does not call nextval() itself.
    """
    request.state.error_operation = "CREATE_WORK"
    request.state.error_stage = "INITIALIZATION"
    request.state.error_context = {
        "user_id": current_user.get("user_id"),
        "role": current_user.get("role"),
        "title": payload.title,
        "language": payload.language,
        "category": payload.category or None,
        "isbn": payload.isbn or None,
        "author_present": bool(payload.author and payload.author.strip()),
        "series_present": bool(payload.series_name and payload.series_name.strip()),
    }
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        request.state.error_stage = "LOAD_ACTOR"
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

        request.state.error_stage = "ALLOCATE_ACCESSION"
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
        if payload.category and (not final_call_no or final_call_no.endswith("-")):
            cat_code = get_category_code(payload.category)
            lang_initial = lang_prefix if len(lang_prefix) == 2 else payload.language[0].upper()
            # Serialize call-number allocation for this language/category pair.
            # Every allocator must take this transaction-scoped lock before counting.
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"call_no:{clean_lang.casefold()}:{payload.category.casefold()}",)
            )
            cur.execute("""
                SELECT COUNT(*) + 1
                FROM public.works
                WHERE language = %s AND category = %s
            """, (clean_lang, payload.category))
            next_call_count = cur.fetchone()[0]
            final_call_no = f"{lang_initial}-{cat_code}-{next_call_count}.0"

        request.state.error_stage = "ALLOCATE_WORK_ID"
        cur.execute("SELECT public.next_work_id()")
        work_id = cur.fetchone()[0]

        request.state.error_stage = "CREATE_WORK_RECORD"
        raw_year = str(payload.year or "").strip()
        if raw_year:
            try:
                safe_year = int(raw_year)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail="Year must be a whole number or blank."
                )
        else:
            safe_year = None
        work_status = "APPROVED" if real_role.strip().lower() == "the chief" else "PENDING"

        cur.execute("""
            INSERT INTO public.works (
                work_id,
                title, language, category, genre, author, publisher,
                original_language, original_title, original_author, translator,
                compiler_editor, work_nature, edition_statement, series_title,
                series_volume, lccn, oclc_no, subject_headings, target_audience_era,
                copyright_status, ddc, notes, translation_compilation,
                year, isbn, call_no, status, proposed_by, proposal_reason,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                NOW(), NOW()
            )
            RETURNING work_id
        """, (
            work_id,
            payload.title,
            payload.language,
            payload.category or None,
            payload.genre if (payload.genre and payload.genre.strip() != "") else None,
            payload.author if (payload.author and payload.author.strip() != "") else "Unknown",
            payload.publisher or None,
            payload.original_language or None,
            payload.original_title or None,
            payload.original_author or None,
            payload.translator or None,
            payload.compiler_editor or None,
            payload.work_nature or None,
            payload.edition_statement or None,
            payload.series_title or None,
            payload.series_volume or None,
            payload.lccn or None,
            payload.oclc_no or None,
            payload.subject_headings or None,
            payload.target_audience_era or None,
            payload.copyright_status or None,
            payload.ddc or None,
            payload.notes or None,
            payload.translation_compilation or None,
            safe_year,
            payload.isbn or None,
            final_call_no,
            work_status,
            token_user_id,
            x_change_reason,
        ))

        request.state.error_stage = "SERIES_LINKING"
        # Series / multi-volume context is optional. The migration creates two small
        # relation tables so the Work itself stays bibliographically clean while
        # related volumes can be discovered as a group.
        series_name = str(payload.series_name or "").strip()
        series_number = str(payload.series_number or "").strip() or None
        raw_volume_number = str(payload.volume_number or "").strip()
        volume_number = None
        if raw_volume_number:
            try:
                volume_number = int(raw_volume_number)
            except ValueError:
                raise HTTPException(status_code=400, detail="Volume number must be a whole number.")
            if volume_number <= 0:
                raise HTTPException(status_code=400, detail="Volume number must be greater than zero.")
        related_work_id = payload.related_work_id

        if series_name or series_number or volume_number or related_work_id is not None:
            cur.execute("SELECT to_regclass('public.work_series_groups'), to_regclass('public.work_series_members')")
            series_tables = cur.fetchone()
            if not series_tables or not series_tables[0] or not series_tables[1]:
                raise HTTPException(
                    status_code=503,
                    detail="Series linking is not enabled yet. Run the Create Work series migration first."
                )

        if related_work_id is not None:
            if int(related_work_id) == int(work_id):
                raise HTTPException(status_code=400, detail="A Work cannot be related to itself.")
            cur.execute("SELECT 1 FROM public.works WHERE work_id = %s", (related_work_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="The related Work was not found.")

        if series_name:
            cur.execute("""
                SELECT series_id
                FROM public.work_series_groups
                WHERE LOWER(BTRIM(series_name)) = LOWER(BTRIM(%s))
                FOR UPDATE
            """, (series_name,))
            series_row = cur.fetchone()
            if series_row:
                series_id = series_row[0]
            else:
                cur.execute("""
                    INSERT INTO public.work_series_groups (series_name, created_by)
                    VALUES (%s, %s)
                    RETURNING series_id
                """, (series_name, token_user_id))
                series_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO public.work_series_members (
                    work_id, series_id, series_number, volume_number, related_work_id
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (work_id) DO UPDATE SET
                    series_id = EXCLUDED.series_id,
                    series_number = EXCLUDED.series_number,
                    volume_number = EXCLUDED.volume_number,
                    related_work_id = EXCLUDED.related_work_id
            """, (work_id, series_id, series_number, volume_number, related_work_id))
        elif related_work_id is not None:
            # A related Work can be provided even when the series name is not known yet.
            cur.execute("""
                SELECT series_id
                FROM public.work_series_members
                WHERE work_id = %s
            """, (related_work_id,))
            related_series = cur.fetchone()
            if related_series:
                cur.execute("""
                    INSERT INTO public.work_series_members (
                        work_id, series_id, series_number, volume_number, related_work_id
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (work_id) DO UPDATE SET
                        series_id = EXCLUDED.series_id,
                        series_number = EXCLUDED.series_number,
                        volume_number = EXCLUDED.volume_number,
                        related_work_id = EXCLUDED.related_work_id
                """, (work_id, related_series[0], series_number, volume_number, related_work_id))
            else:
                raise HTTPException(
                    status_code=400,
                    detail="The related Work is not part of a series yet. Enter a Series name to create the group."
                )

        request.state.error_stage = "AUTHORITY_RESOLUTION"
        author_name = payload.author.strip() if payload.author and payload.author.strip() else "Unknown"
        if payload.authority_id is not None:
            cur.execute("""
                SELECT authority_id, preferred_name, status
                FROM public.authority_records
                WHERE authority_id = %s
                FOR SHARE
            """, (payload.authority_id,))
            authority_row = cur.fetchone()
            if not authority_row:
                raise HTTPException(status_code=400, detail="Selected authority record was not found")

            authority_id, selected_name, authority_status = authority_row
            normalized_authority_status = str(authority_status or "").upper()
            if normalized_authority_status == "REJECTED":
                raise HTTPException(
                    status_code=409,
                    detail="The selected authority record is rejected and cannot be linked to a Work. Reopen it first."
                )
            if normalized_authority_status not in {"PROVISIONAL", "VERIFIED"}:
                raise HTTPException(
                    status_code=409,
                    detail="The selected authority record is not in a usable status and cannot be linked to a Work."
                )
            author_name = (selected_name or author_name).strip() or "Unknown"
            cur.execute("""
                UPDATE public.works
                SET author = %s
                WHERE work_id = %s
            """, (author_name, work_id))
        else:
            authority_id = resolve_or_create_authority(cur, author_name, token_user_id)

        request.state.error_stage = "AUTHORITY_LINK"
        cur.execute("""
            INSERT INTO public.work_authorities (
                work_id, authority_id, relationship_type, sequence_no, notes, created_by
            )
            VALUES (%s, %s, 'AUTHOR', 1, %s, %s)
            ON CONFLICT (work_id, authority_id, relationship_type)
            DO NOTHING
        """, (
            work_id,
            authority_id,
            "Automatically linked during work registration.",
            token_user_id,
        ))

        request.state.error_stage = "ALLOCATE_ITEM_SERIAL"
        cur.execute("SELECT public.next_item_serial_no()")
        created_serial_no = cur.fetchone()[0]

        request.state.error_stage = "CREATE_INITIAL_ITEM"
        initial_item_status = "AVAILABLE" if real_role.strip().lower() == "the chief" else "PENDING"
        
        cur.execute("""
            INSERT INTO public.items (
                serial_no, work_id, accession_no, call_no, shelf, 
                extent_page_count, physical_dimensions, date_acquired, collection_fonds,
                physical_condition, binding_type, provenance_source, artifactual_notes,
                access_restrictions, digital_scan_available, ocr_status,
                availability_status, is_deleted, created_at, proposed_by
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'f', NOW(), %s
            )
        """, (
            created_serial_no, work_id, final_accession_no, final_call_no, payload.shelf or None,
            payload.extent_page_count or None, payload.physical_dimensions or None,
            payload.date_acquired or None, payload.collection_fonds or None,
            payload.physical_condition or None, payload.binding_type or None,
            payload.provenance_source or None, payload.artifactual_notes or None,
            payload.access_restrictions or None, payload.digital_scan_available or False,
            payload.ocr_status or "Unindexed", initial_item_status, token_user_id
        ))
        request.state.error_stage = "WRITE_AUDIT"
        registration_mode = (
            "DIRECT_CHIEF"
            if real_role.strip().lower() == "the chief"
            else "KEEPER_SUBMISSION"
        )
        workflow_outcome = (
            "APPROVED"
            if real_role.strip().lower() == "the chief"
            else "PENDING_REVIEW"
        )
        audit_actor = {
            **current_user,
            "username": real_name,
            "role": real_role,
            "designation": real_role,
        }
        _audit_ledger(
            request=request,
            current_user=audit_actor,
            conn=conn,
            category="CATALOGUE",
            action_type="ACCESSION_WORK",
            target_entity="WORK",
            target_id=work_id,
            http_method="POST",
            justification=x_change_reason,
            diff={
                "work_id": work_id,
                "serial_no": created_serial_no,
                "accession_no": final_accession_no,
                "title": payload.title,
                "author": author_name,
                "language": payload.language,
                "registration_mode": registration_mode,
                "workflow_outcome": workflow_outcome,
                "call_no": final_call_no,
                "shelf": payload.shelf or None,
                "series": {
                    "name": series_name or None,
                    "number": series_number,
                    "volume": volume_number,
                    "related_work_id": related_work_id,
                },
            },
            extra={
                "work_id": work_id,
                "serial_no": created_serial_no,
                "accession_no": final_accession_no,
                "registration_mode": registration_mode,
                "workflow_outcome": workflow_outcome,
                "justification_required": real_role.strip().lower() == "the chief",
                "device_id": x_device_id,
                "ip_address": x_ip_address,
            },
        )

        request.state.error_stage = "COMMIT"
        conn.commit()
        request.state.error_stage = "COMPLETED"
        return {
            "work_id": work_id,
            "accession_no": final_accession_no,
            "serial_no": created_serial_no,
            "series": {
                "name": series_name or None,
                "number": series_number,
                "volume": volume_number,
                "related_work_id": related_work_id,
            },
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# ===========================================================================
# WORK LIFECYCLE ENDPOINTS (moved from catalogue.py; public URLs preserved)
# ===========================================================================

@work_router.post("/create-work", dependencies=[Depends(require_role(["The Chief", "The Keeper"]))])
@audit_action(
    "ACCESSION_WORK",
    target_entity="Work",
    reason_param="x_change_reason"
)
def create_work(
    payload: WorkCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    x_change_reason: Optional[str] = Header(default=None),
    x_registration_mode: Optional[str] = Header(default=None),
    x_device_id: Optional[str] = Header(default="Desktop Browser Workstation"),
    x_ip_address: Optional[str] = Header(default="127.0.0.1")
):
    role = str(current_user.get("role") or "").strip().lower()
    reason = str(x_change_reason or "").strip()
    mode = str(x_registration_mode or "").strip().upper()
    if role == "the chief":
        if mode != "DIRECT_CHIEF":
            raise HTTPException(status_code=403, detail="Chief Work registration must use the explicit direct-registration path.")
        if not reason:
            raise HTTPException(status_code=400, detail="A specific reason is required for direct Chief registration.")
    elif role == "the keeper":
        if mode not in ("", "KEEPER_SUBMISSION"):
            raise HTTPException(status_code=403, detail="The Keeper may only submit Work for Chief review.")
        reason = reason or "Keeper submission for Chief review"
    else:
        raise HTTPException(status_code=403, detail="This role cannot register a Work.")
    return create_work_transaction(
        payload=payload,
        request=request,
        current_user=current_user,
        x_change_reason=reason,
        x_device_id=x_device_id,
        x_ip_address=x_ip_address,
    )


@work_router.post(
    "/draft-audit",
    tags=["Docket"],
    dependencies=[Depends(require_role(["The Chief", "The Keeper"]))],
)
def audit_local_work_draft(
    payload: WorkDraftAuditPayload,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    action = str(payload.action or "").strip().upper()
    if action not in {"SAVED", "UPDATED", "RESTORED", "DISCARDED"}:
        raise HTTPException(status_code=400, detail="Unsupported Work draft audit action.")
    draft_id = str(payload.draft_id or "").strip()
    if not draft_id or len(draft_id) > 160:
        raise HTTPException(status_code=400, detail="A valid local draft identifier is required.")
    fields = [str(field)[:100] for field in (payload.fields or [])[:80]]
    changes = payload.changes or {}
    if not isinstance(changes, dict):
        raise HTTPException(status_code=400, detail="Draft changes must be an object.")
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        _write_audit(
            request, current_user, conn,
            action_type=f"WORK_DRAFT_{action}",
            target_id=draft_id,
            justification=_clean_note(payload.note, "Draft audit note") or f"Local Work draft {action.lower()}",
            diff={
                "draft_id": draft_id,
                "action": action,
                "title": _clean_note(payload.title, "Draft title") or None,
                "draft_mode": _clean_note(payload.mode, "Draft mode") or None,
                "field_names": fields,
                "changes": changes,
                "saved_at": payload.saved_at,
            },
            extra={"local_draft": True, "draft_id": draft_id, "action": action},
            target_entity="WORK_DRAFT",
        )
        conn.commit()
        return {"status": "success", "action": action, "draft_id": draft_id}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        print(f"Work draft audit failed: {exc}")
        raise HTTPException(status_code=500, detail="Unable to record the Work draft audit event.")
    finally:
        cur.close()
        conn.close()


@work_router.get("/work/{work_id}")
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

@work_router.get(
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

@work_router.post(
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

        if str(work["status"] or "").strip().upper() != "REJECTED":
            raise HTTPException(
                status_code=409,
                detail="Only a rejected Work can be corrected and resubmitted."
            )

        if _is_finally_rejected_work(cur, work_id):
            raise HTTPException(
                status_code=409,
                detail="This Work was finally rejected and cannot be resubmitted."
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

        raw_year = str(payload.get("year") or "").strip()
        if raw_year:
            try:
                safe_year = int(raw_year)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="Year must be a whole number or blank.")
        else:
            safe_year = None

        new_values = {
            "title": title,
            "author": payload.get("author"),
            "category": payload.get("category"),
            "language": language,
            "publisher": payload.get("publisher"),
            "year": safe_year,
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
        field_changes = _audit_diff(work, new_values)

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
            safe_year,
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
              AND availability_status = 'REJECTED'
              AND is_deleted = TRUE
        """, (token_user_id, work_id))

        _audit_ledger(
            request=request,
            current_user=current_user,
            conn=conn,
            category="ARCHIVAL_GOVERNANCE",
            action_type="WORK_RESUBMIT",
            target_entity="WORK",
            target_id=work_id,
            http_method="POST",
            justification=str(
                payload.get("proposal_reason")
                or "Corrected rejected proposal"
            ),
            diff={
                "work_id": work_id,
                "title": updated["title"],
                "status": "PENDING",
                "changes": field_changes,
            },
            extra={"resubmission": True},
            before={
                **{field: work.get(field) for field in new_values},
                "status": work.get("status"),
            },
            after={**new_values, "status": "PENDING"},
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

@work_router.get(
    "/pending-works",
    tags=["Admin Operations"],
    dependencies=[Depends(require_role(["The Chief", "The Keeper"]))]
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
              AND (
                    %s = 'The Chief'
                    OR w.proposed_by = %s
                  )
            ORDER BY w.created_at DESC, w.work_id DESC
        """, (
            str(current_user.get("role") or ""),
            int(current_user.get("user_id")),
        ))
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

@work_router.get(
    "/review/final-rejections",
    tags=["Docket"],
    dependencies=[Depends(require_role(["The Chief"]))]
)
def list_final_rejections(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Read-only list of permanently rejected Works, for The Chief."""
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT w.work_id, w.title, w.author, w.language, w.category,
                   u.name AS proposer_name,
                   a.timestamp AS rejected_at,
                   a.username AS rejected_by,
                   a.justification AS reason
            FROM public.works w
            JOIN LATERAL (
                SELECT x.timestamp, x.username, x.justification
                FROM public.audit_activities x
                WHERE x.target_entity = 'WORK'
                  AND x.target_id = w.work_id::text
                  AND x.action_type = 'CURATOR_DECISION'
                  AND x.diff_payload->>'decision_action' = 'REJECT_FINAL'
                  AND x.timestamp >= w.created_at - interval '2 seconds'
                ORDER BY x.sequence_id DESC
                LIMIT 1
            ) a ON TRUE
            LEFT JOIN public.users u ON u.user_id = w.proposed_by
            WHERE w.status = 'REJECTED'
            ORDER BY a.timestamp DESC
        """)
        return cur.fetchall()
    except Exception as e:
        print(f"Final rejection list failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to load permanently rejected works."
        )
    finally:
        cur.close()
        conn.close()

@work_router.get(
    "/review/my-final-rejections",
    tags=["Docket"],
    dependencies=[Depends(require_role(["The Keeper"]))]
)
def list_my_final_rejections(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Read-only list of the calling Keeper's own permanently rejected Works."""
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT w.work_id, w.title, w.author, w.language, w.category,
                   a.timestamp AS rejected_at,
                   a.username AS rejected_by,
                   a.justification AS reason
            FROM public.works w
            JOIN LATERAL (
                SELECT x.timestamp, x.username, x.justification
                FROM public.audit_activities x
                WHERE x.target_entity = 'WORK'
                  AND x.target_id = w.work_id::text
                  AND x.action_type = 'CURATOR_DECISION'
                  AND x.diff_payload->>'decision_action' = 'REJECT_FINAL'
                  AND x.timestamp >= w.created_at - interval '2 seconds'
                ORDER BY x.sequence_id DESC
                LIMIT 1
            ) a ON TRUE
            WHERE w.status = 'REJECTED'
              AND w.proposed_by = %s
            ORDER BY a.timestamp DESC
        """, (int(current_user.get("user_id")),))
        return cur.fetchall()
    except Exception as e:
        print(f"My final rejection list failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to load your permanently rejected works."
        )
    finally:
        cur.close()
        conn.close()

@work_router.get(
    "/review/field-options",
    tags=["Docket"],
    dependencies=[Depends(require_role(["The Chief", "The Keeper"]))]
)
def get_field_options(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Read-only lists used by the correction form dropdowns."""
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT TRIM(language) FROM public.language_registry
            WHERE language IS NOT NULL AND TRIM(language) <> ''
        """)
        registry = {r[0] for r in cur.fetchall()}

        cur.execute("""
            SELECT DISTINCT TRIM(original_language) FROM public.works
            WHERE original_language IS NOT NULL AND TRIM(original_language) <> ''
        """)
        original = registry | {r[0] for r in cur.fetchall()}

        cur.execute("""
            SELECT DISTINCT ON (lower(g)) g
            FROM (
                SELECT TRIM(unnest(string_to_array(genre, '/'))) AS g
                FROM public.works WHERE genre IS NOT NULL
            ) s
            WHERE g <> '' AND lower(g) <> 'no genre yet'
            ORDER BY lower(g), g
        """)
        genres = [r[0] for r in cur.fetchall()]

        return {
            "languages": sorted(registry, key=str.lower),
            "original_languages": sorted(original, key=str.lower),
            "genres": genres,
            "categories": ["Fiction", "Non-Fiction", "Reference", "Religious", "Poetry"],
        }
    except Exception as e:
        print(f"Field options failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to load the field lists.")
    finally:
        cur.close()
        conn.close()

@work_router.post("/approve/{work_id}", tags=["Admin Operations"], dependencies=[Depends(require_role(["The Chief"]))])
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
            authority = validate_work_authority(cur, work_id)
            cur.execute("""
                UPDATE public.items
                SET availability_status = 'AVAILABLE',
                    is_deleted = FALSE
                WHERE work_id = %s
                  AND availability_status = 'PENDING'
                  AND is_deleted = FALSE
            """, (work_id,))
        else:
            cur.execute("""
                UPDATE public.items
                SET availability_status = 'REJECTED',
                    is_deleted = TRUE
                WHERE work_id = %s
                  AND availability_status = 'PENDING'
                  AND is_deleted = FALSE
            """, (work_id,))

        notification_message = (
            f"PROPOSAL APPROVED: Your proposal '{work_title}' has been "
            f"approved by The Chief and is now live in the Library Catalogue."
            if decision == "APPROVE"
            else
            f"PROPOSAL REJECTED: Your proposal '{work_title}' was rejected by The Chief.\n\n"
            f"Reason: {reason}\n\n"
            f"This is a final rejection. The Work will not be reopened for correction."
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

        _audit_ledger(
            request=request,
            current_user=current_user,
            conn=conn,
            category="ARCHIVAL_GOVERNANCE",
            action_type="CURATOR_DECISION",
            target_entity="WORK",
            target_id=work_id,
            http_method="POST",
            justification=reason,
            diff={
                "work_id": work_id,
                "title": work_title,
                "decision": new_status,
                "decision_action": "APPROVE" if decision == "APPROVE" else "REJECT_FINAL",
                "reason": reason,
                "authority_id": authority["authority_id"] if new_status == "APPROVED" else None,
                "authority_name": authority["preferred_name"] if new_status == "APPROVED" else None,
            },
            extra={
                "work_id": work_id,
                "decision": new_status,
                "decision_action": "APPROVE" if decision == "APPROVE" else "REJECT_FINAL",
            },
            before={"status": "PENDING"},
            after={"status": new_status},
        )
        
        conn.commit()

        return {"message": f"Work '{work_title}' {new_status}."}
    except Exception as e:
        if conn: conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

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
    changes: dict = Field(default_factory=dict)
    note: Optional[str] = None

def _is_finally_rejected_work(cur, work_id: int) -> bool:
    """Return True for a Work with an explicitly audited final REJECT decision.

    Older records have no decision_action marker and retain their legacy
    correction behavior. A return-for-correction also has its own marker and
    remains resubmittable through its open correction request.
    """
    import json

    cur.execute("""
        SELECT diff_payload
        FROM audit_activities
        WHERE target_entity = 'WORK'
          AND target_id = %s
          AND action_type = 'CURATOR_DECISION'
    """, (str(work_id),))
    for row in cur.fetchall():
        diff = row.get("diff_payload") if hasattr(row, "get") else row[0]
        if isinstance(diff, str):
            try:
                diff = json.loads(diff)
            except (TypeError, ValueError):
                continue
        if isinstance(diff, dict) and str(diff.get("decision_action") or "").upper() == "REJECT_FINAL":
            return True
    return False


def _work_editable_fields(actor: dict, status_value: str, correction, final_rejection: bool = False) -> list:
    if actor["is_chief"] or status_value != "REJECTED" or final_rejection:
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

def _sync_work_authority(cur, work_id: int, author_name: str, user_id):
    """Resolve and synchronize the primary AUTHOR relationship for a Work.

    The authority resolver participates in the caller's transaction. Existing
    AUTHOR relationships are replaced so the bibliographic author and
    work-authority relationship cannot drift apart.
    """
    clean_name = author_name.strip() if author_name and author_name.strip() else "Unknown"
    authority_id = resolve_or_create_authority(cur, clean_name, user_id)

    cur.execute("""
        DELETE FROM public.work_authorities
        WHERE work_id = %s
          AND relationship_type = 'AUTHOR'
    """, (work_id,))

    cur.execute("""
        INSERT INTO public.work_authorities (
            work_id, authority_id, relationship_type, sequence_no, notes, created_by
        )
        VALUES (%s, %s, 'AUTHOR', 1, %s, %s)
    """, (
        work_id,
        authority_id,
        "Synchronized during Work author correction.",
        user_id,
    ))
    return authority_id


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

@work_router.get(
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
        final_rejection = status_value == "REJECTED" and _is_finally_rejected_work(cur, work_id)

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
            "final_rejection": final_rejection,
            "legacy_rejection": status_value == "REJECTED" and correction is None and not final_rejection,
            "editable_fields": _work_editable_fields(actor, status_value, correction, final_rejection),
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

@work_router.post(
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
        if _open_correction(cur, "WORK", work_id):
            raise HTTPException(
                status_code=409,
                detail="This Work already has an open correction request."
            )

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
            UPDATE public.items
            SET availability_status = 'REJECTED',
                is_deleted = TRUE,
                deletion_reason = %s
            WHERE work_id = %s
              AND availability_status = 'PENDING'
              AND is_deleted = FALSE
        """, (reason, work_id))

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
                "decision_action": "RETURN_FOR_CORRECTION",
                "reason": reason,
                "request_id": request_id,
                "flagged_fields": fields,
                "correction_note": correction_note or None,
            },
            extra={
                "work_id": work_id,
                "decision": "REJECTED",
                "decision_action": "RETURN_FOR_CORRECTION",
                "flagged_fields": fields
            },
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

@work_router.post(
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
        final_rejection = _is_finally_rejected_work(cur, work_id)
        if final_rejection:
            detail = "This Work was finally rejected and cannot be resubmitted."
            conn.rollback()
            _log_refusal(
                request, current_user, "WORK_FINAL_REJECTION_RESUBMIT_REFUSED",
                work_id, detail, {"requested_fields": list(requested.keys())},
                entity="WORK"
            )
            raise HTTPException(status_code=409, detail=detail)
        allowed = _work_editable_fields(actor, "REJECTED", correction, final_rejection)

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
        ledger_change_set = _audit_ledger_diff(work, new_values)
        field_changes = ledger_change_set["fields"]

        if not field_changes and not note:
            raise HTTPException(
                status_code=400,
                detail="Change a marked field or add a note explaining why nothing needs changing."
            )

        authority_id = None
        if "author" in field_changes:
            corrected_author = (field_changes["author"]["to"] or "").strip() or "Unknown"
            field_changes["author"]["to"] = corrected_author
            authority_id = _sync_work_authority(
                cur, work_id, corrected_author, actor["user_id"]
            )
        else:
            validate_work_authority(cur, work_id)

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
              AND availability_status = 'REJECTED'
              AND is_deleted = TRUE
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
                "change_summary": {
                    "changed_fields": ledger_change_set["changed_fields"],
                    "changed_count": ledger_change_set["changed_count"],
                },
                "request_id": correction["request_id"] if correction else None,
                "authority_id": authority_id,
            },
            extra={
                "resubmission": True,
                "legacy_rejection": correction is None,
                "authority_id": authority_id,
            },
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
