# app/routers/items.py

from typing import Optional
from app.routers.authority import resolve_or_create_authority, validate_work_authority
from app.routers.accession_utils import get_language_prefix, get_category_code
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from app.database import get_connection
from app.auth import get_current_user, require_role
from app.audit_utils import audit_action
from app.services.audit_service import log_audit_activity

from pydantic import BaseModel, Field
from typing import List
from psycopg2.extras import RealDictCursor
from app.routers.review_utils import (
    _actor_info, _clean_note, _write_audit, _log_refusal, _open_correction,
    _notes_for, _audit_ledger_diff,
)

router = APIRouter(prefix="/items", tags=["items"])


# Catalogue-facing Item lifecycle routes are kept in this module so Item state
# changes remain owned by the Item layer while legacy /catalogue URLs remain intact.
catalogue_item_router = APIRouter(prefix="/catalogue", tags=["catalogue"])

ITEM_CORRECTABLE_FIELDS = (
    "work_id",
    "language_id",
    "shelf",
    "extent_page_count",
    "physical_dimensions",
    "date_acquired",
    "collection_fonds",
    "physical_condition",
    "binding_type",
    "provenance_source",
    "artifactual_notes",
    "access_restrictions",
    "digital_scan_available",
    "ocr_status",
)


@router.get("/{serial_no}")
def get_item(
    request: Request, serial_no: int,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT 
                i.serial_no,
                i.work_id,
                i.accession_no,
                i.call_no,
                i.shelf,
                i.language_id,
                i.extent_page_count,
                i.physical_dimensions,
                i.date_acquired,
                i.collection_fonds,
                i.physical_condition,
                i.binding_type,
                i.provenance_source,
                i.artifactual_notes,
                i.access_restrictions,
                i.digital_scan_available,
                i.ocr_status,
                i.availability_status,
                w.title,
                w.author,
                w.language,
                w.publisher,
                w.year,
                w.genre,
                w.notes
            FROM public.items i
            JOIN public.works w ON i.work_id = w.work_id
            WHERE i.serial_no = %s
              AND COALESCE(i.is_deleted, FALSE) = FALSE
              AND UPPER(BTRIM(COALESCE(w.status, ''))) = 'APPROVED'
              AND UPPER(BTRIM(COALESCE(i.availability_status, ''))) NOT IN ('PENDING', 'REJECTED')
        """, (serial_no,))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Holding not found")
            
        return row
    finally:
        cur.close()
        conn.close()


@router.put(
    "/{serial_no}",
    dependencies=[Depends(require_role(["The Chief"]))]
)
@audit_action(
    "UPDATE_HOLDING",
    category="CATALOG_API",
    target_entity="ITEM",
    target_id_param="serial_no",
    reason_param="x_change_reason",
    log_success=False
)
def update_item(
    serial_no: int,
    payload: dict,
    request: Request,
    current_user: dict = Depends(get_current_user),
    x_change_reason: Optional[str] = Header(default="Direct holding record revision")
):
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT i.work_id, w.title, w.author, w.language, w.publisher, w.year, w.genre, w.notes, i.shelf
            FROM public.items i
            JOIN public.works w ON i.work_id = w.work_id
            WHERE i.serial_no = %s
        """, (serial_no,))
        
        item_row = cur.fetchone()
        if not item_row:
            raise HTTPException(status_code=404, detail="Holding not found")
            
        work_id = item_row[0]

        for required_field in ("title", "language"):
            if required_field in payload and not str(payload.get(required_field) or "").strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"{required_field.title()} cannot be empty."
                )
        safe_year = None
        year_is_set = "year" in payload and payload.get("year") is not None
        if year_is_set and str(payload.get("year")).strip() != "":
            try:
                safe_year = int(str(payload.get("year")).strip())
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="Year must be a whole number or blank.")

        old_state = {
            "title": item_row[1],
            "author": item_row[2],
            "language": item_row[3],
            "publisher": item_row[4],
            "year": item_row[5],
            "genre": item_row[6],
            "notes": item_row[7],
            "shelf": item_row[8]
        }

        requested_author = payload.get("author")
        authority_id = payload.get("authority_id")
        resolved_author = None
        resolved_authority_id = None
        if requested_author is not None or authority_id is not None:
            author_text = str(requested_author or "").strip() or "Unknown"
            if authority_id is not None:
                try:
                    authority_id_int = int(str(authority_id).strip())
                except (TypeError, ValueError):
                    raise HTTPException(status_code=400, detail="Authority ID must be numeric.")
                cur.execute("""
                    SELECT authority_id, preferred_name, status, COALESCE(is_deleted, FALSE)
                    FROM public.authority_records
                    WHERE authority_id = %s
                    FOR SHARE
                """, (authority_id_int,))
                authority_row = cur.fetchone()
                if not authority_row:
                    raise HTTPException(status_code=400, detail="Selected authority record was not found.")
                resolved_authority_id, preferred_name, authority_status, authority_deleted = authority_row
                if authority_deleted:
                    raise HTTPException(status_code=409, detail="The selected authority record is inactive/deleted and cannot be linked to a Work.")
                if str(authority_status or "").upper() == "REJECTED":
                    raise HTTPException(status_code=409, detail="The selected authority record is rejected and cannot be linked to a Work. Reopen it first.")
                resolved_author = preferred_name or author_text
            else:
                resolved_author = author_text
                resolved_authority_id = resolve_or_create_authority(
                    cur, resolved_author, current_user.get("user_id")
                )

            cur.execute("""
                DELETE FROM public.work_authorities
                WHERE work_id = %s AND relationship_type = 'AUTHOR'
            """, (work_id,))
            cur.execute("""
                INSERT INTO public.work_authorities (
                    work_id, authority_id, relationship_type, sequence_no, notes, created_by
                ) VALUES (%s, %s, 'AUTHOR', 1, %s, %s)
                ON CONFLICT (work_id, authority_id, relationship_type) DO NOTHING
            """, (
                work_id, resolved_authority_id,
                "Author authority synchronized during holding edit.",
                current_user.get("user_id")
            ))

        cur.execute("""
            UPDATE public.works 
            SET title = COALESCE(%s, title),
                author = COALESCE(%s, author),
                language = COALESCE(%s, language),
                publisher = COALESCE(%s, publisher),
                year = CASE WHEN %s THEN %s ELSE year END,
                genre = COALESCE(%s, genre),
                notes = COALESCE(%s, notes),
                updated_at = NOW()
            WHERE work_id = %s
        """, (
            payload.get("title"), resolved_author if (requested_author is not None or authority_id is not None) else None, payload.get("language"),
            payload.get("publisher"), year_is_set, safe_year, payload.get("genre"),
            payload.get("notes"), work_id
        ))

        if "shelf" in payload:
            cur.execute("""
                UPDATE public.items 
                SET shelf = NULLIF(BTRIM(%s), '')
                WHERE serial_no = %s
            """, (payload.get("shelf"), serial_no))

        actor_id = str(current_user.get("user_id", "UNKNOWN"))
        actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
        actor_role = str(current_user.get("role", "The Keeper"))

        audit_ok = log_audit_activity(
            request=request,
            user_id=actor_id,
            username=actor_name,
            role=actor_role,
            designation=str(current_user.get("designation") or actor_role),
            category="INVENTORY",
            action_type="UPDATE_HOLDING",
            target_entity="ITEM",
            target_id=str(serial_no),
            endpoint=request.url.path,
            http_method="PUT",
            justification=x_change_reason,
            diff_payload={
                "serial_no": serial_no,
                "work_id": work_id,
                "previous": old_state,
                "updated": {k: v for k, v in payload.items() if v is not None},
                "authority_id": resolved_authority_id
            },
            extra_metadata={
                "serial_no": serial_no,
                "work_id": work_id
            },
            conn=conn
        )

        if not audit_ok:
            raise RuntimeError(
                "Audit record could not be written; operation rolled back"
            )
        
        conn.commit()

        return {"status": "success", "serial_no": serial_no, "work_id": work_id}

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cur.close()
        conn.close()


@catalogue_item_router.post("/create-item", dependencies=[Depends(require_role(["The Chief", "The Keeper"]))])
@audit_action(
    "ACCESSION_ITEM",
    target_entity="ITEM",
    reason_param="x_change_reason",
    log_success=False
)
async def create_item(
    payload: dict,
    request: Request,
    current_user: dict = Depends(get_current_user),
    x_change_reason: Optional[str] = Header(default=None),
    x_registration_mode: Optional[str] = Header(default=None),
    x_device_id: Optional[str] = Header(default="Desktop Browser Workstation"),
    x_ip_address: Optional[str] = Header(default="127.0.0.1")
):
    role_key = str(current_user.get("role") or "").strip().lower()
    reason = str(x_change_reason or "").strip()
    mode = str(x_registration_mode or "").strip().upper()
    if role_key == "the chief":
        if mode != "DIRECT_CHIEF":
            raise HTTPException(status_code=403, detail="Chief Item registration must use the explicit direct-registration path.")
        if not reason:
            raise HTTPException(status_code=400, detail="A specific reason is required for direct Chief registration.")
    elif role_key == "the keeper":
        if mode not in ("", "KEEPER_SUBMISSION"):
            raise HTTPException(status_code=403, detail="The Keeper may only submit an Item for Chief review.")
        reason = reason or "Keeper submission for Chief verification"
    else:
        raise HTTPException(status_code=403, detail="This role cannot register an Item.")
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

        # Check how many copies currently exist for this Work
        cur.execute("SELECT COUNT(*) FROM public.items WHERE work_id = %s AND is_deleted = FALSE", (existing_work_id,))
        existing_copies_count = cur.fetchone()[0]

        is_approved = str(work_status or "").strip().upper() == "APPROVED"

        # Allow adding a copy if the Work is approved, OR if it's the very first copy for a pending Work
        if not is_approved and existing_copies_count > 0:
            raise HTTPException(
                status_code=409,
                detail="This Work is not yet approved and cannot receive additional copies."
            )

        normalized_work_language = str(language or "").strip().casefold()
        normalized_item_language = str(language_id or "").strip().casefold()
        if not normalized_work_language or normalized_item_language != normalized_work_language:
            raise HTTPException(
                status_code=400,
                detail="The Item language must match the approved Work's language. Reload the Work and try again."
            )

        validate_work_authority(cur, existing_work_id)

        lang_prefix = get_language_prefix(language)
        
        cur.execute("""
            INSERT INTO public.language_registry (language, prefix, last_number)
            VALUES (%s, %s, 1)
            ON CONFLICT (prefix)
            DO UPDATE SET last_number = public.language_registry.last_number + 1
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

        request.state.error_operation = "CREATE_ITEM"
        request.state.error_stage = "ALLOCATE_ITEM_SERIAL"
        cur.execute("SELECT public.next_item_serial_no()")
        created_serial_no = cur.fetchone()[0]

        request.state.error_stage = "CREATE_ITEM_RECORD"
        cur.execute("""
            INSERT INTO public.items (
                serial_no,
                work_id,
                accession_no,
                call_no,
                shelf,
                language_id,
                extent_page_count,
                physical_dimensions,
                date_acquired,
                collection_fonds,
                physical_condition,
                binding_type,
                provenance_source,
                artifactual_notes,
                access_restrictions,
                digital_scan_available,
                ocr_status,
                availability_status,
                is_deleted,
                proposed_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s)
        """, (
            created_serial_no,
            existing_work_id,
            accession_no,
            call_no,
            payload.get("shelf"),
            language_id,
            payload.get("extent_page_count"),
            payload.get("physical_dimensions"),
            payload.get("date_acquired"),
            payload.get("collection_fonds"),
            payload.get("physical_condition"),
            payload.get("binding_type"),
            payload.get("provenance_source"),
            payload.get("artifactual_notes"),
            payload.get("access_restrictions"),
            payload.get("digital_scan_available", False),
            payload.get("ocr_status"),
            item_status,
            token_user_id
        ))

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
            justification=reason,
            diff_payload={
                "serial_no": created_serial_no,
                "work_id": existing_work_id,
                "accession_no": accession_no,
                "title": title,
                "language_id": language_id,
                "availability_status": item_status,
                "registration_mode": "DIRECT_CHIEF" if role_key == "the chief" else "KEEPER_SUBMISSION",
                "workflow_outcome": "AVAILABLE" if role_key == "the chief" else "PENDING_REVIEW"
            },
            extra_metadata={
                "serial_no": created_serial_no,
                "work_id": existing_work_id,
                "registration_mode": "DIRECT_CHIEF" if role_key == "the chief" else "KEEPER_SUBMISSION",
                "workflow_outcome": "AVAILABLE" if role_key == "the chief" else "PENDING_REVIEW",
                "justification_required": role_key == "the chief",
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
            "item_id": created_serial_no,
            "accession_no": accession_no,
            "work_id": existing_work_id,
            "title": title,
            "status": item_status,
            "availability_status": item_status,
        }

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Item creation failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Unable to create Item. No changes were committed.")
    finally:
        cur.close()
        conn.close()


@catalogue_item_router.post(
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

        if str(item["availability_status"] or "").strip().upper() != "REJECTED":
            raise HTTPException(
                status_code=409,
                detail="Only a rejected Item can be corrected and resubmitted."
            )

        if str(item["work_status"] or "").strip().upper() != "APPROVED":
            raise HTTPException(
                status_code=409,
                detail="The parent Work is not approved and this Item cannot be resubmitted."
            )

        validate_work_authority(cur, item["work_id"])

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


@catalogue_item_router.get(
    "/pending-items",
    tags=["Admin Operations"],
    dependencies=[Depends(require_role(["The Chief", "The Keeper"]))]
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
              AND UPPER(TRIM(w.status)) = 'APPROVED'
              AND (
                    LOWER(TRIM(%s)) = 'the chief'
                    OR i.proposed_by = %s
                  )
            ORDER BY i.serial_no DESC
        """, (
            str(current_user.get("role") or "").strip().lower(),
            int(current_user.get("user_id")),
        ))
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


@catalogue_item_router.post(
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
                UPDATE public.items i
                SET availability_status = 'AVAILABLE'
                FROM public.works w
                WHERE i.serial_no = %s
                  AND i.work_id = w.work_id
                  AND UPPER(BTRIM(COALESCE(i.availability_status, ''))) = 'PENDING'
                  AND COALESCE(i.is_deleted, FALSE) = FALSE
                  AND UPPER(TRIM(w.status)) = 'APPROVED'
                RETURNING i.serial_no, i.accession_no, i.work_id
            """, (serial_no,))
        else:
            cur.execute("""
                UPDATE public.items i
                SET availability_status = 'REJECTED',
                    is_deleted = TRUE,
                    deletion_reason = %s
                WHERE i.serial_no = %s
                  AND UPPER(BTRIM(COALESCE(i.availability_status, ''))) = 'PENDING'
                  AND COALESCE(i.is_deleted, FALSE) = FALSE
                  AND EXISTS (
                      SELECT 1
                      FROM public.works w
                      WHERE w.work_id = i.work_id
                        AND UPPER(TRIM(w.status)) = 'APPROVED'
                  )
                RETURNING i.serial_no, i.accession_no, i.work_id
            """, (reason, serial_no))

        row = cur.fetchone()
        if not row:
            cur.execute("""
                SELECT i.serial_no, w.status AS work_status
                FROM public.items i
                LEFT JOIN public.works w ON w.work_id = i.work_id
                WHERE i.serial_no = %s
                  AND i.availability_status = 'PENDING'
                  AND i.is_deleted = FALSE
            """, (serial_no,))
            pending_item = cur.fetchone()
            if pending_item and str(pending_item.get("work_status") or '').strip().upper() != 'APPROVED':
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "This is the initial Item for a Work that has not been approved yet. "
                        "Approve or reject the parent Work first."
                    )
                )
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


# app/routers/items.py (Replace update_ledger_record and get_catalogue_book)

@catalogue_item_router.patch("/{serial_no}", dependencies=[Depends(require_role(["The Chief"]))])
@audit_action(
    "UPDATE_LEDGER",
    target_entity="ITEM",
    target_id_param="serial_no",
    reason_param="x_change_reason",
    log_success=False
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

        # Update items table fields
        cur.execute("""
            UPDATE public.items SET
                shelf = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE shelf END,
                extent_page_count = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE extent_page_count END,
                physical_dimensions = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE physical_dimensions END,
                date_acquired = CASE WHEN %s THEN NULLIF(BTRIM(%s), '')::date ELSE date_acquired END,
                collection_fonds = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE collection_fonds END,
                physical_condition = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE physical_condition END,
                binding_type = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE binding_type END,
                provenance_source = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE provenance_source END,
                artifactual_notes = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE artifactual_notes END,
                access_restrictions = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE access_restrictions END,
                digital_scan_available = CASE WHEN %s THEN %s::boolean ELSE digital_scan_available END,
                ocr_status = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE ocr_status END
            WHERE serial_no = %s
            RETURNING work_id
        """, (
            "shelf" in payload, payload.get("shelf"),
            "extent_page_count" in payload, str(payload.get("extent_page_count") or ""),
            "physical_dimensions" in payload, payload.get("physical_dimensions"),
            "date_acquired" in payload and bool(payload.get("date_acquired")), str(payload.get("date_acquired") or ""),
            "collection_fonds" in payload, payload.get("collection_fonds"),
            "physical_condition" in payload, payload.get("physical_condition"),
            "binding_type" in payload, payload.get("binding_type"),
            "provenance_source" in payload, payload.get("provenance_source"),
            "artifactual_notes" in payload, payload.get("artifactual_notes"),
            "access_restrictions" in payload, payload.get("access_restrictions"),
            "digital_scan_available" in payload, bool(payload.get("digital_scan_available")),
            "ocr_status" in payload, payload.get("ocr_status"),
            serial_no
        ))
        
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

            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"call_no:{clean_lang.casefold()}:{new_cat.casefold()}",)
            )
            cur.execute("""
                SELECT COUNT(*) + 1 
                FROM public.works 
                WHERE language = %s AND category = %s
            """, (clean_lang, new_cat))
            next_call_count = cur.fetchone()[0]
            final_call_no = f"{lang_initial}-{cat_code}-{next_call_count}.0"

        raw_year = payload.get("year")
        safe_year = None
        if "year" in payload:
            if raw_year is None or str(raw_year).strip() == "":
                safe_year = None
            else:
                try:
                    safe_year = int(str(raw_year).strip())
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=400,
                        detail="Year must be a whole number or blank. Existing data was not changed."
                    )

        # Update all fields on public.works
        cur.execute("""
            UPDATE public.works SET
                title = CASE WHEN %s THEN COALESCE(NULLIF(BTRIM(%s), ''), title) ELSE title END,
                author = CASE WHEN %s THEN COALESCE(NULLIF(BTRIM(%s), ''), author) ELSE author END,
                publisher = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE publisher END,
                isbn = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE isbn END,
                ddc = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE ddc END,
                year = CASE WHEN %s THEN %s ELSE year END,
                category = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE category END,
                genre = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE genre END,
                language = CASE WHEN %s THEN COALESCE(NULLIF(BTRIM(%s), ''), language) ELSE language END,
                original_language = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE original_language END,
                original_title = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE original_title END,
                original_author = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE original_author END,
                translator = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE translator END,
                compiler_editor = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE compiler_editor END,
                work_nature = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE work_nature END,
                edition_statement = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE edition_statement END,
                series_title = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE series_title END,
                series_volume = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE series_volume END,
                lccn = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE lccn END,
                oclc_no = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE oclc_no END,
                subject_headings = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE subject_headings END,
                target_audience_era = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE target_audience_era END,
                copyright_status = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE copyright_status END,
                translation_compilation = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE translation_compilation END,
                notes = CASE WHEN %s THEN NULLIF(BTRIM(%s), '') ELSE notes END,
                call_no = CASE WHEN %s THEN COALESCE(NULLIF(BTRIM(%s), ''), call_no) ELSE call_no END,
                updated_at = NOW()
            WHERE work_id = %s
        """, (
            "title" in payload, payload.get("title"),
            "author" in payload, payload.get("author"),
            "publisher" in payload, payload.get("publisher"),
            "isbn" in payload, payload.get("isbn"),
            "ddc" in payload, payload.get("ddc"),
            "year" in payload, safe_year,
            "category" in payload, new_cat,
            "genre" in payload, payload.get("genre"),
            "language" in payload, payload.get("language"),
            "original_language" in payload, payload.get("original_language"),
            "original_title" in payload, payload.get("original_title"),
            "original_author" in payload, payload.get("original_author"),
            "translator" in payload, payload.get("translator"),
            "compiler_editor" in payload, payload.get("compiler_editor"),
            "work_nature" in payload, payload.get("work_nature"),
            "edition_statement" in payload, payload.get("edition_statement"),
            "series_title" in payload, payload.get("series_title"),
            "series_volume" in payload, payload.get("series_volume"),
            "lccn" in payload, payload.get("lccn"),
            "oclc_no" in payload, payload.get("oclc_no"),
            "subject_headings" in payload, payload.get("subject_headings"),
            "target_audience_era" in payload, payload.get("target_audience_era"),
            "copyright_status" in payload, payload.get("copyright_status"),
            "translation_compilation" in payload, payload.get("translation_compilation"),
            "notes" in payload, payload.get("notes"),
            ("call_no" in payload or "category" in payload), final_call_no,
            work_id
        ))

        # Handle relational series group updates
        s_name = str(payload.get("series_name") or "").strip()
        s_num = str(payload.get("series_number") or "").strip() or None
        v_num_raw = str(payload.get("volume_number") or "").strip()
        v_num = int(v_num_raw) if v_num_raw and v_num_raw.isdigit() else None
        rel_work_raw = str(payload.get("related_work_id") or "").strip()
        rel_work_id = int(rel_work_raw) if rel_work_raw and rel_work_raw.isdigit() else None

        if s_name:
            cur.execute("""
                SELECT series_id FROM public.work_series_groups
                WHERE LOWER(BTRIM(series_name)) = LOWER(BTRIM(%s))
                FOR UPDATE
            """, (s_name,))
            s_row = cur.fetchone()
            if s_row:
                s_id = s_row[0]
            else:
                cur.execute("""
                    INSERT INTO public.work_series_groups (series_name, created_by)
                    VALUES (%s, %s)
                    RETURNING series_id
                """, (s_name, token_user_id))
                s_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO public.work_series_members (work_id, series_id, series_number, volume_number, related_work_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (work_id) DO UPDATE SET
                    series_id = EXCLUDED.series_id,
                    series_number = EXCLUDED.series_number,
                    volume_number = EXCLUDED.volume_number,
                    related_work_id = EXCLUDED.related_work_id
            """, (work_id, s_id, s_num, v_num, rel_work_id))

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

@catalogue_item_router.delete("/{book_id}", tags=["Catalogue Operations"], dependencies=[Depends(require_role(["The Chief"]))])
@audit_action(
    "DEACCESSION",
    target_entity="ITEM",
    target_id_param="book_id",
    reason_param="reason",
    log_success=False
)
async def soft_delete_book(
    book_id: int, reason: str, request: Request,
    current_user: dict = Depends(get_current_user)
):    
    reason = str(reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="A deaccession reason is required.")

    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE public.items
            SET is_deleted = TRUE, deletion_reason = %s
            WHERE serial_no = %s
              AND COALESCE(is_deleted, FALSE) = FALSE
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


class ItemCorrectionRequest(BaseModel):
    fields: List[str]
    reason: str
    correction_note: Optional[str] = None


class ReviewNoteCreate(BaseModel):
    body: str


class ItemCorrectionSubmit(BaseModel):
    changes: dict = Field(default_factory=dict)
    note: Optional[str] = None


def _load_item_for_review(cur, serial_no: int, actor: dict) -> dict:
    cur.execute("""
        SELECT
            i.serial_no, i.accession_no, i.work_id, i.call_no, i.shelf, i.language_id,
            i.extent_page_count, i.physical_dimensions, i.date_acquired, i.collection_fonds,
            i.physical_condition, i.binding_type, i.provenance_source, i.artifactual_notes,
            i.access_restrictions, i.digital_scan_available, i.ocr_status,
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


def _item_editable_fields(actor: dict, status_value: str, correction) -> list:
    if actor["is_chief"] or status_value != "REJECTED":
        return []
    if correction:
        return [
            f for f in correction["field_names"] if f in ITEM_CORRECTABLE_FIELDS
        ]
    return list(ITEM_CORRECTABLE_FIELDS)


@catalogue_item_router.get(
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
            "shelf": item["shelf"],
            "language_id": item["language_id"],
            "extent_page_count": item["extent_page_count"],
            "physical_dimensions": item["physical_dimensions"],
            "date_acquired": item["date_acquired"],
            "collection_fonds": item["collection_fonds"],
            "physical_condition": item["physical_condition"],
            "binding_type": item["binding_type"],
            "provenance_source": item["provenance_source"],
            "artifactual_notes": item["artifactual_notes"],
            "access_restrictions": item["access_restrictions"],
            "digital_scan_available": item["digital_scan_available"],
            "ocr_status": item["ocr_status"],
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


@catalogue_item_router.post(
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
        if _open_correction(cur, "ITEM", serial_no):
            raise HTTPException(
                status_code=409,
                detail="This Item already has an open correction request."
            )

        cur.execute("""
            UPDATE public.items AS i
            SET availability_status = 'REJECTED',
                is_deleted = TRUE,
                deletion_reason = %s
            FROM public.works AS w
            WHERE i.serial_no = %s
              AND i.work_id = w.work_id
              AND UPPER(TRIM(w.status)) = 'APPROVED'
              AND i.availability_status = 'PENDING'
              AND i.is_deleted = FALSE
            RETURNING i.serial_no, i.accession_no, i.work_id
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


@catalogue_item_router.post(
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


@catalogue_item_router.post(
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

        if str(item["availability_status"] or "").strip().upper() != "REJECTED":
            raise HTTPException(
                status_code=409,
                detail="Only a rejected Item can be corrected and resubmitted."
            )
        if str(item["work_status"] or "").strip().upper() != "APPROVED":
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
        for key in allowed:
            if key in requested:
                val = requested[key]
                if key == "work_id":
                    try:
                        new_values["work_id"] = int(str(val).strip())
                    except (TypeError, ValueError):
                        raise HTTPException(
                            status_code=400,
                            detail="Authorized Work ID must be a numeric Work ID."
                        )
                elif key == "language_id":
                    language_value = str(val or "").strip()
                    if not language_value:
                        raise HTTPException(
                            status_code=400, detail="Language Profile cannot be empty."
                        )
                    new_values["language_id"] = language_value
                elif key == "digital_scan_available":
                    new_values["digital_scan_available"] = bool(val)
                elif key in ("shelf", "extent_page_count", "physical_dimensions",
                             "date_acquired", "collection_fonds", "physical_condition",
                             "binding_type", "provenance_source", "artifactual_notes",
                             "access_restrictions", "ocr_status"):
                    text_val = str(val if val is not None else "").strip()
                    new_values[key] = text_val or None

        target_work_id = new_values.get("work_id", item["work_id"])
        cur.execute(
            "SELECT work_id, language, call_no, status FROM public.works WHERE work_id = %s FOR SHARE",
            (target_work_id,)
        )
        target_work_language_row = cur.fetchone()
        if not target_work_language_row:
            raise HTTPException(status_code=404, detail="Authorized catalogued work not found.")
        if str(target_work_language_row["status"] or "").strip().upper() != "APPROVED":
            raise HTTPException(
                status_code=409,
                detail="That Work is not approved and cannot receive this Item."
            )
        validate_work_authority(cur, target_work_id)
        target_work_language = str(target_work_language_row["language"] or "").strip()
        requested_language = new_values.get("language_id", target_work_language)
        if str(requested_language or "").strip().casefold() != target_work_language.casefold():
            raise HTTPException(
                status_code=400,
                detail="The Item language must match the selected Work's language."
            )
        new_values["language_id"] = target_work_language

        ledger_change_set = _audit_ledger_diff(item, new_values)
        field_changes = ledger_change_set["fields"]

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
                INSERT INTO public.language_registry (language, prefix, last_number)
                VALUES (%s, %s, 1)
                ON CONFLICT (prefix)
                DO UPDATE SET last_number = public.language_registry.last_number + 1
                RETURNING last_number;
            """, (new_work["language"].strip(), prefix))
            counter = cur.fetchone()[0]
            accession_no = f"{prefix}-{counter}"
            call_no = new_work["call_no"]
            final_work_id = new_work["work_id"]
            field_changes["accession_no"] = {
                "from": item["accession_no"], "to": accession_no
            }
            field_changes["call_no"] = {"from": item["call_no"], "to": call_no}

        item_updates = {}
        for k in ("shelf", "extent_page_count", "physical_dimensions", "date_acquired",
                  "collection_fonds", "physical_condition", "binding_type",
                  "provenance_source", "artifactual_notes", "access_restrictions",
                  "digital_scan_available", "ocr_status"):
            if k in field_changes:
                item_updates[k] = field_changes[k]["to"]

        set_clauses = [
            "work_id = %s",
            "accession_no = %s",
            "call_no = %s",
            "language_id = %s",
            "availability_status = 'PENDING'",
            "is_deleted = FALSE",
            "deletion_reason = NULL"
        ]
        params = [final_work_id, accession_no, call_no, final_language_id]

        for col, val in item_updates.items():
            set_clauses.append(f"{col} = %s")
            params.append(val)

        params.extend([serial_no, actor["user_id"]])

        cur.execute(f"""
            UPDATE public.items
            SET {', '.join(set_clauses)}
            WHERE serial_no = %s
              AND proposed_by = %s
              AND availability_status = 'REJECTED'
            RETURNING serial_no
        """, tuple(params))

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
                "change_summary": {
                    "changed_fields": sorted(field_changes.keys()),
                    "changed_count": len(field_changes),
                },
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


def _generate_record_id(serial_no: int) -> str:
    from datetime import datetime
    return f"AO-REC-{datetime.now().year}-{str(serial_no).zfill(6)}"


@catalogue_item_router.get("/holding/{serial_no}")
def get_catalogue_book(request: Request, serial_no: int, current_user: dict = Depends(get_current_user)):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = """
            SELECT  
                i.item_id,
                i.serial_no, 
                i.accession_no, 
                i.shelf, 
                i.work_id, 
                i.extent_page_count,
                i.physical_dimensions,
                i.date_acquired,
                i.collection_fonds,
                i.physical_condition,
                i.binding_type,
                i.provenance_source,
                i.artifactual_notes,
                i.access_restrictions,
                i.digital_scan_available,
                i.ocr_status,
                i.availability_status,
                w.language, 
                w.title, 
                w.author, 
                w.publisher, 
                w.year, 
                w.isbn, 
                w.ddc, 
                w.call_no, 
                w.original_language, 
                w.original_title,
                w.original_author,
                w.translator,
                w.compiler_editor,
                w.work_nature,
                w.edition_statement,
                w.series_title,
                w.series_volume,
                w.lccn,
                w.oclc_no,
                w.subject_headings,
                w.target_audience_era,
                w.copyright_status,
                w.notes, 
                w.category, 
                w.genre, 
                w.translation_compilation,
                sg.series_name,
                sm.series_number,
                sm.volume_number,
                sm.related_work_id
            FROM public.items i
            INNER JOIN public.works w ON i.work_id = w.work_id
            LEFT JOIN public.work_series_members sm ON sm.work_id = w.work_id
            LEFT JOIN public.work_series_groups sg ON sg.series_id = sm.series_id
            WHERE i.serial_no = %s
              AND COALESCE(i.is_deleted, FALSE) = FALSE
              AND UPPER(BTRIM(COALESCE(w.status, ''))) = 'APPROVED'
              AND UPPER(BTRIM(COALESCE(i.availability_status, ''))) NOT IN ('PENDING', 'REJECTED')
        """
        cur.execute(query, (serial_no,))
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Book Record not found"
            )
            
        result["record_id"] = _generate_record_id(result["serial_no"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Database Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        cur.close()
        conn.close()