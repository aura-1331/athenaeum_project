# app/routers/items.py

from typing import Optional
from app.routers.authority import resolve_or_create_authority, validate_work_authority
from app.routers.accession_utils import get_language_prefix, get_category_code
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from app.database import get_connection
from app.auth import get_current_user, require_role
from app.audit_utils import audit_action
from app.services.audit_service import log_audit_activity

from pydantic import BaseModel
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

ITEM_CORRECTABLE_FIELDS = ("work_id", "language_id")



@router.get("/{serial_no}")
def get_item(
    request: Request, serial_no: int,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT w.title, w.author, w.language, w.publisher, w.year, w.genre, w.notes
            FROM public.items i
            JOIN public.works w ON i.work_id = w.work_id
            WHERE i.serial_no = %s AND i.is_deleted = FALSE
        """, (serial_no,))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Holding not found")
            
        return {
            "title": row[0],
            "author": row[1],
            "language": row[2],
            "publisher": row[3],
            "year": row[4],
            "genre": row[5],
            "notes": row[6]
        }
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
    target_entity="Item",
    target_id_param="serial_no",
    reason_param="x_change_reason"
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
        # 1. Resolve work_id and capture existing state for audit diff
        cur.execute("""
            SELECT i.work_id, w.title, w.author, w.language, w.publisher, w.year, w.genre, w.notes
            FROM public.items i
            JOIN public.works w ON i.work_id = w.work_id
            WHERE i.serial_no = %s
        """, (serial_no,))
        
        item_row = cur.fetchone()
        if not item_row:
            raise HTTPException(status_code=404, detail="Holding not found")
            
        work_id = item_row[0]
        old_state = {
            "title": item_row[1],
            "author": item_row[2],
            "language": item_row[3],
            "publisher": item_row[4],
            "year": item_row[5],
            "genre": item_row[6],
            "notes": item_row[7]
        }

        # 2. Keep Work author text and the AUTHOR authority relationship synchronized.
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

        # 3. Update bibliographic attributes on WORKS.
        cur.execute("""
            UPDATE public.works 
            SET title = COALESCE(%s, title),
                author = COALESCE(%s, author),
                language = COALESCE(%s, language),
                publisher = COALESCE(%s, publisher),
                year = COALESCE(%s, year),
                genre = COALESCE(%s, genre),
                notes = COALESCE(%s, notes),
                updated_at = NOW()
            WHERE work_id = %s
        """, (
            payload.get("title"), resolved_author if (requested_author is not None or authority_id is not None) else None, payload.get("language"),
            payload.get("publisher"), payload.get("year"), payload.get("genre"),
            payload.get("notes"), work_id
        ))

        # 3. Update denormalized attributes on ITEMS
        cur.execute("""
            UPDATE public.items 
            SET title = COALESCE(%s, title),
                author = COALESCE(%s, author),
                publisher = COALESCE(%s, publisher),
                year = COALESCE(%s, year),
                genre = COALESCE(%s, genre),
                notes = COALESCE(%s, notes)
            WHERE serial_no = %s
        """, (
            payload.get("title"), resolved_author if (requested_author is not None or authority_id is not None) else None, payload.get("publisher"),
            payload.get("year"), payload.get("genre"), payload.get("notes"),
            serial_no
        ))


        # 4. Cryptographic ledger anchor
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

# ---------------------------------------------------------------------------
# Legacy /catalogue Item lifecycle endpoints
# ---------------------------------------------------------------------------
@catalogue_item_router.post("/create-item", dependencies=[Depends(require_role(["The Chief", "The Keeper"]))])
@audit_action(
    "ACCESSION_ITEM",
    target_entity="Item",
    reason_param="x_change_reason"
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

        if str(work_status).upper() != "APPROVED":
            raise HTTPException(
                status_code=409,
                detail="This Work is not yet approved and cannot receive an additional copy."
            )

        # An approved Work must still have a usable author authority before a
        # new physical Item can be attached to it.
        validate_work_authority(cur, existing_work_id)

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
                language_id,
                availability_status,
                is_deleted,
                proposed_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s)
        """, (
            created_serial_no,
            existing_work_id,
            accession_no,
            call_no,
            language_id,
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

        # The parent Work may still be APPROVED in its own status while its
        # author authority has subsequently been rejected or deactivated.
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
              -- The initial copy for a pending Work is not a separate Item request.
              -- Work approval/rejection decides that initial copy's state.
              AND UPPER(TRIM(w.status)) = 'APPROVED'
              AND (
                    %s = 'The Chief'
                    OR i.proposed_by = %s
                  )
            ORDER BY i.serial_no DESC
        """, (
            str(current_user.get("role") or ""),
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
            # An Item may only become AVAILABLE while its parent Work is still approved.
            # Re-check the Work here because its status may have changed since accession.
            cur.execute("""
                UPDATE public.items i
                SET availability_status = 'AVAILABLE'
                FROM public.works w
                WHERE i.serial_no = %s
                  AND i.work_id = w.work_id
                  AND i.availability_status = 'PENDING'
                  AND i.is_deleted = FALSE
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
                  AND i.availability_status = 'PENDING'
                  AND i.is_deleted = FALSE
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
            # Guard direct API calls as well as the filtered UI queue: both
            # APPROVE and REJECT must wait for the parent Work's decision.
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


@catalogue_item_router.patch("/{serial_no}", dependencies=[Depends(require_role(["The Chief"]))])
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


class ItemCorrectionRequest(BaseModel):
    fields: List[str]
    reason: str
    correction_note: Optional[str] = None


class ReviewNoteCreate(BaseModel):
    body: str


class ItemCorrectionSubmit(BaseModel):
    changes: dict = {}
    note: Optional[str] = None


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

            validate_work_authority(cur, new_work["work_id"])

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

@catalogue_item_router.get("/{serial_no}")
def get_catalogue_book(request: Request, serial_no: int, current_user: dict = Depends(get_current_user)):
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

