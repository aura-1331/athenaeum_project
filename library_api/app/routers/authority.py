# app/routers/authority.py

from enum import Enum
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator

from app.auth import get_current_user, require_role
from app.database import get_db_connection
from app.audit_utils import audit_action
from app.services.audit_service import log_audit_activity


# ============================================================
# ROUTER INITIALIZATION
# ============================================================

router = APIRouter(
    prefix="/authority",
    tags=["Authority Management"],
    dependencies=[Depends(require_role(["The Chief"]))]
)


# ============================================================
# ENUMS & MANDATORY AUDIT SCHEMAS
# ============================================================

class AuthorityStatus(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class AuthorityActionPayload(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000, description="Mandatory audit justification")

    @field_validator("reason", mode="before")
    @classmethod
    def validate_mandatory_reason(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("An explicit reason/justification is strictly mandatory.")
        return value.strip()


class UpdateAuthorityPayload(BaseModel):
    preferred_name: Optional[str] = Field(None, min_length=1, max_length=255)
    authority_type: Optional[str] = Field(None, min_length=1, max_length=50)
    authority_code: Optional[str] = Field(None, min_length=1, max_length=50)
    notes: Optional[str] = Field(None, max_length=2000)
    reason: str = Field(..., min_length=3, max_length=1000, description="Mandatory reason for modifying records")

    @field_validator("preferred_name", "authority_type", "authority_code", "reason", mode="before")
    @classmethod
    def strip_and_validate(cls, value: Optional[str]) -> Optional[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or only whitespace.")
            return stripped
        return value


class VariantCreatePayload(BaseModel):
    variant_name: str = Field(..., min_length=1, max_length=255)
    variant_type: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=2000)
    reason: str = Field(..., min_length=3, max_length=1000, description="Mandatory reason for adding alias")

    @field_validator("variant_name", "reason", mode="before")
    @classmethod
    def strip_and_validate(cls, value: Optional[str]) -> Optional[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or only whitespace.")
            return stripped
        return value


class VariantUpdatePayload(BaseModel):
    variant_name: Optional[str] = Field(None, min_length=1, max_length=255)
    variant_type: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=2000)
    reason: str = Field(..., min_length=3, max_length=1000, description="Mandatory reason for editing alias")

    @field_validator("reason", mode="before")
    @classmethod
    def strip_and_validate(cls, value: Optional[str]) -> Optional[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Reason cannot be empty or only whitespace.")
            return stripped
        return value


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _transition_authority_status(
    cur,
    authority_id: int,
    target_status: AuthorityStatus,
    disallowed_current_status: AuthorityStatus,
    conflict_detail: str,
    note_tag: str,
    user_id: Any,
    reason: str
) -> Dict[str, Any]:
    """Locks the record, validates state, appends audit reason to notes, and updates DB."""
    if not reason or not reason.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A non-empty reason is strictly required."
        )

    cur.execute(
        """
        SELECT authority_id, status, notes
        FROM public.authority_records
        WHERE authority_id = %s
        FOR UPDATE
        """,
        (authority_id,)
    )
    row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority record not found."
        )

    current_status, existing_notes = row[1], row[2] or ""

    if current_status == disallowed_current_status.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=conflict_detail
        )

    append_note = f"[{note_tag} by User {user_id}]: {reason.strip()}"
    updated_notes = f"{existing_notes}\n{append_note}".strip()

    is_verified = (target_status == AuthorityStatus.VERIFIED)
    numeric_user_id = int(user_id)

    cur.execute(
        """
        UPDATE public.authority_records
        SET
            status = %s,
            notes = %s,
            verified_at = (CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END),
            verified_by = (CASE WHEN %s THEN %s::integer ELSE NULL END),
            updated_at = CURRENT_TIMESTAMP,
            updated_by = %s::integer
        WHERE authority_id = %s
        RETURNING
            authority_id,
            authority_code,
            preferred_name,
            authority_type,
            status,
            notes,
            verified_at,
            verified_by,
            updated_at,
            updated_by
        """,
        (
            target_status.value,
            updated_notes,
            is_verified,
            is_verified,
            numeric_user_id,
            numeric_user_id,
            authority_id
        )
    )

    columns = [desc[0] for desc in cur.description]
    res_dict = dict(zip(columns, cur.fetchone()))
    res_dict["_previous_status"] = current_status
    return res_dict


def _verify_editable_authority(cur, authority_id: int):
    """Verifies that parent authority exists and is PROVISIONAL."""
    cur.execute(
        """
        SELECT authority_id, status
        FROM public.authority_records
        WHERE authority_id = %s
        FOR UPDATE
        """,
        (authority_id,)
    )
    row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority record not found."
        )

    current_status = row[1]
    if current_status != "PROVISIONAL":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot modify data for an authority in '{current_status}' status. Reopen to PROVISIONAL first."
        )


# ============================================================
# AUTHORITY RECORD ENDPOINTS
# ============================================================

@router.get("/")
def list_authorities(
    status_filter: Optional[AuthorityStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user)
):
    conn, cur = db
    params: List[Any] = []
    where_clause = ""

    if status_filter:
        where_clause = "WHERE status = %s"
        params.append(status_filter.value)

    cur.execute(f"SELECT COUNT(*) FROM public.authority_records {where_clause}", tuple(params))
    total_count = cur.fetchone()[0]

    query = f"""
        SELECT
            authority_id, authority_code, preferred_name,
            authority_type, status, notes, created_at,
            updated_at, created_by, updated_by, verified_at, verified_by
        FROM public.authority_records
        {where_clause}
        ORDER BY authority_id
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    cur.execute(query, tuple(params))

    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]

    return {"data": rows, "total": total_count, "limit": limit, "offset": offset}


@router.get("/{authority_id}")
def get_authority(
    authority_id: int,
    db = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user)
):
    conn, cur = db

    cur.execute(
        """
        SELECT
            authority_id, authority_code, preferred_name,
            authority_type, status, notes, created_at,
            updated_at, created_by, updated_by, verified_at, verified_by
        FROM public.authority_records
        WHERE authority_id = %s
        """,
        (authority_id,)
    )
    main_row = cur.fetchone()
    if not main_row:
        raise HTTPException(status_code=404, detail="Authority record not found.")

    columns = [desc[0] for desc in cur.description]
    authority = dict(zip(columns, main_row))

    # Variants
    cur.execute(
        """
        SELECT variant_id, variant_name, variant_type, notes, created_at, created_by
        FROM public.authority_variants
        WHERE authority_id = %s
        ORDER BY variant_id
        """,
        (authority_id,)
    )
    v_cols = [desc[0] for desc in cur.description]
    authority["variants"] = [dict(zip(v_cols, row)) for row in cur.fetchall()]

    # Connected Works
    cur.execute(
        """
        SELECT wa.work_id, wa.relationship_type, wa.sequence_no, w.title, w.author
        FROM public.work_authorities wa
        LEFT JOIN public.works w ON w.work_id = wa.work_id
        WHERE wa.authority_id = %s
        ORDER BY wa.sequence_no, wa.work_id
        """,
        (authority_id,)
    )
    w_cols = [desc[0] for desc in cur.description]
    authority["works"] = [dict(zip(w_cols, row)) for row in cur.fetchall()]

    return authority


@router.put("/{authority_id}")
@audit_action(
    "AUTHORITY_UPDATE",
    category="AUTHORITY_CONTROL",
    target_entity="Authority",
    target_id_param="authority_id",
    reason_param="payload.reason"
)
def update_authority_details(
    authority_id: int,
    request: Request,
    payload: UpdateAuthorityPayload,
    db = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user)
):
    conn, cur = db
    _verify_editable_authority(cur, authority_id)

    cur.execute(
        """
        SELECT preferred_name, authority_type, authority_code, notes
        FROM public.authority_records
        WHERE authority_id = %s
        """,
        (authority_id,)
    )
    row = cur.fetchone()

    old_state = {
        "preferred_name": row[0],
        "authority_type": row[1],
        "authority_code": row[2],
        "notes": row[3]
    }

    updated_preferred_name = payload.preferred_name if payload.preferred_name is not None else row[0]
    updated_authority_type = payload.authority_type if payload.authority_type is not None else row[1]
    updated_authority_code = payload.authority_code if payload.authority_code is not None else row[2]
    
    existing_notes = row[3] or ""
    append_note = f"[UPDATED by User {current_user['user_id']}]: {payload.reason.strip()}"
    final_notes = f"{payload.notes or existing_notes}\n{append_note}".strip()

    cur.execute(
        """
        UPDATE public.authority_records
        SET
            preferred_name = %s,
            authority_type = %s,
            authority_code = %s,
            notes = %s,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = %s::integer
        WHERE authority_id = %s
        RETURNING
            authority_id, authority_code, preferred_name,
            authority_type, status, notes, created_at,
            updated_at, created_by, updated_by, verified_at, verified_by
        """,
        (
            updated_preferred_name,
            updated_authority_type,
            updated_authority_code,
            final_notes,
            int(current_user["user_id"]),
            authority_id
        )
    )

    result = cur.fetchone()

    columns = [desc[0] for desc in cur.description]
    authority_data = dict(zip(columns, result))

    actor_id = str(current_user.get("user_id", "UNKNOWN"))
    actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
    actor_role = str(current_user.get("role", "The Chief"))

    audit_ok = log_audit_activity(
        request=request,
        user_id=actor_id,
        username=actor_name,
        role=actor_role,
        designation=str(current_user.get("designation") or actor_role),
        category="AUTHORITY_CONTROL",
        action_type="AUTHORITY_UPDATE",
        target_entity="AUTHORITY",
        target_id=str(authority_id),
        endpoint=request.url.path,
        http_method="PUT",
        justification=payload.reason,
        diff_payload={
            "authority_id": authority_id,
            "previous": old_state,
            "updated": {
                "preferred_name": updated_preferred_name,
                "authority_type": updated_authority_type,
                "authority_code": updated_authority_code,
                "notes": final_notes
            }
        },
        extra_metadata={
            "authority_id": authority_id,
            "authority_code": updated_authority_code
        },
        conn=conn
    )

    if not audit_ok:
        raise RuntimeError(
            "Audit record could not be written; operation rolled back"
        )
    
    conn.commit()

    return {
        "status": "success",
        "message": "Authority record updated successfully.",
        "authority": authority_data
    }


@router.patch("/{authority_id}/verify")
@audit_action(
    "AUTHORITY_VERIFY",
    category="AUTHORITY_CONTROL",
    target_entity="Authority",
    target_id_param="authority_id",
    reason_param="payload.reason"
)
def verify_authority(
    authority_id: int,
    request: Request,
    payload: AuthorityActionPayload,
    db = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user)
):
    conn, cur = db
    result = _transition_authority_status(
        cur=cur,
        authority_id=authority_id,
        target_status=AuthorityStatus.VERIFIED,
        disallowed_current_status=AuthorityStatus.VERIFIED,
        conflict_detail="Authority is already verified.",
        note_tag="VERIFIED",
        user_id=current_user["user_id"],
        reason=payload.reason
    )
    prev_status = result.pop("_previous_status", "PROVISIONAL")

    actor_id = str(current_user.get("user_id", "UNKNOWN"))
    actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
    actor_role = str(current_user.get("role", "The Chief"))

    audit_ok = log_audit_activity(
        request=request,
        user_id=actor_id,
        username=actor_name,
        role=actor_role,
        designation=str(current_user.get("designation") or actor_role),
        category="AUTHORITY_CONTROL",
        action_type="AUTHORITY_VERIFY",
        target_entity="AUTHORITY",
        target_id=str(authority_id),
        endpoint=request.url.path,
        http_method="PATCH",
        justification=payload.reason,
        diff_payload={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code"),
            "preferred_name": result.get("preferred_name"),
            "status_transition": {"from": prev_status, "to": "VERIFIED"}
        },
        extra_metadata={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code")
        },
        conn=conn
    )

    if not audit_ok:
        raise RuntimeError(
            "Audit record could not be written; operation rolled back"
        )
    
    conn.commit()

    return {"status": "success", "message": "Authority verified successfully.", "authority": result}


@router.patch("/{authority_id}/reject")
@audit_action(
    "AUTHORITY_REJECT",
    category="AUTHORITY_CONTROL",
    target_entity="Authority",
    target_id_param="authority_id",
    reason_param="payload.reason"
)
def reject_authority(
    authority_id: int,
    request: Request,
    payload: AuthorityActionPayload,
    db = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user)
):
    conn, cur = db
    result = _transition_authority_status(
        cur=cur,
        authority_id=authority_id,
        target_status=AuthorityStatus.REJECTED,
        disallowed_current_status=AuthorityStatus.REJECTED,
        conflict_detail="Authority is already rejected.",
        note_tag="REJECTED",
        user_id=current_user["user_id"],
        reason=payload.reason
    )
    prev_status = result.pop("_previous_status", "PROVISIONAL")

    actor_id = str(current_user.get("user_id", "UNKNOWN"))
    actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
    actor_role = str(current_user.get("role", "The Chief"))

    audit_ok = log_audit_activity(
        request=request,
        user_id=actor_id,
        username=actor_name,
        role=actor_role,
        designation=str(current_user.get("designation") or actor_role),
        category="AUTHORITY_CONTROL",
        action_type="AUTHORITY_REJECT",
        target_entity="AUTHORITY",
        target_id=str(authority_id),
        endpoint=request.url.path,
        http_method="PATCH",
        justification=payload.reason,
        diff_payload={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code"),
            "preferred_name": result.get("preferred_name"),
            "status_transition": {"from": prev_status, "to": "REJECTED"}
        },
        extra_metadata={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code")
        },
        conn=conn
    )

    if not audit_ok:
        raise RuntimeError(
            "Audit record could not be written; operation rolled back"
        )
    
    conn.commit()

    return {"status": "success", "message": "Authority rejected successfully.", "authority": result}


@router.patch("/{authority_id}/reopen")
@audit_action(
    "AUTHORITY_REOPEN",
    category="AUTHORITY_CONTROL",
    target_entity="Authority",
    target_id_param="authority_id",
    reason_param="payload.reason"
)
def reopen_authority(
    authority_id: int,
    request: Request,
    payload: AuthorityActionPayload,
    db = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user)
):
    conn, cur = db
    result = _transition_authority_status(
        cur=cur,
        authority_id=authority_id,
        target_status=AuthorityStatus.PROVISIONAL,
        disallowed_current_status=AuthorityStatus.PROVISIONAL,
        conflict_detail="Authority is already provisional.",
        note_tag="REOPENED FOR REVIEW",
        user_id=current_user["user_id"],
        reason=payload.reason
    )
    prev_status = result.pop("_previous_status", "UNKNOWN")

    actor_id = str(current_user.get("user_id", "UNKNOWN"))
    actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
    actor_role = str(current_user.get("role", "The Chief"))

    audit_ok = log_audit_activity(
        request=request,
        user_id=actor_id,
        username=actor_name,
        role=actor_role,
        designation=str(current_user.get("designation") or actor_role),
        category="AUTHORITY_CONTROL",
        action_type="AUTHORITY_REOPEN",
        target_entity="AUTHORITY",
        target_id=str(authority_id),
        endpoint=request.url.path,
        http_method="PATCH",
        justification=payload.reason,
        diff_payload={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code"),
            "preferred_name": result.get("preferred_name"),
            "status_transition": {"from": prev_status, "to": "PROVISIONAL"}
        },
        extra_metadata={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code")
        },
        conn=conn
    )

    if not audit_ok:
        raise RuntimeError(
            "Audit record could not be written; operation rolled back"
        )
    
    conn.commit()

    return {"status": "success", "message": "Authority re-opened for provisional review.", "authority": result}


# ============================================================
# VARIANT MANAGEMENT ENDPOINTS
# ============================================================

@router.post("/{authority_id}/variants", status_code=status.HTTP_201_CREATED)
@audit_action(
    "AUTHORITY_VARIANT_CREATE",
    category="AUTHORITY_CONTROL",
    target_entity="AuthorityVariant",
    target_id_param="authority_id",
    reason_param="payload.reason"
)
def create_variant(
    authority_id: int,
    request: Request,
    payload: VariantCreatePayload,
    db = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user)
):
    conn, cur = db
    _verify_editable_authority(cur, authority_id)

    formatted_notes = f"[ADDED: {payload.reason.strip()}]"
    if payload.notes:
        formatted_notes = f"{payload.notes}\n{formatted_notes}".strip()

    cur.execute(
        """
        INSERT INTO public.authority_variants (
            authority_id,
            variant_name,
            variant_type,
            notes,
            created_at,
            created_by
        )
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s::integer)
        RETURNING
            variant_id,
            authority_id,
            variant_name,
            variant_type,
            notes,
            created_at,
            created_by
        """,
        (
            authority_id,
            payload.variant_name,
            payload.variant_type,
            formatted_notes,
            int(current_user["user_id"])
        )
    )

    result = cur.fetchone()

    columns = [desc[0] for desc in cur.description]
    variant_data = dict(zip(columns, result))

    actor_id = str(current_user.get("user_id", "UNKNOWN"))
    actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
    actor_role = str(current_user.get("role", "The Chief"))

    audit_ok = log_audit_activity(
        request=request,
        user_id=actor_id,
        username=actor_name,
        role=actor_role,
        designation=str(current_user.get("designation") or actor_role),
        category="AUTHORITY_CONTROL",
        action_type="AUTHORITY_VARIANT_CREATE",
        target_entity="AUTHORITY_VARIANT",
        target_id=str(variant_data["variant_id"]),
        endpoint=request.url.path,
        http_method="POST",
        justification=payload.reason,
        diff_payload={
            "authority_id": authority_id,
            "variant_id": variant_data["variant_id"],
            "variant_name": payload.variant_name,
            "variant_type": payload.variant_type,
            "notes": formatted_notes
        },
        extra_metadata={
            "authority_id": authority_id,
            "variant_id": variant_data["variant_id"]
        },
        conn=conn
    )

    if not audit_ok:
        raise RuntimeError(
            "Audit record could not be written; operation rolled back"
        )
    
    conn.commit()

    return {
        "status": "success",
        "message": "Variant created successfully.",
        "variant": variant_data
    }


@router.put("/{authority_id}/variants/{variant_id}")
@audit_action(
    "AUTHORITY_VARIANT_UPDATE",
    category="AUTHORITY_CONTROL",
    target_entity="AuthorityVariant",
    target_id_param="variant_id",
    reason_param="payload.reason"
)
def update_variant(
    authority_id: int,
    variant_id: int,
    request: Request,
    payload: VariantUpdatePayload,
    db = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user)
):
    conn, cur = db
    _verify_editable_authority(cur, authority_id)

    cur.execute(
        """
        SELECT variant_id, variant_name, variant_type, notes
        FROM public.authority_variants
        WHERE variant_id = %s AND authority_id = %s
        FOR UPDATE
        """,
        (variant_id, authority_id)
    )
    v_row = cur.fetchone()

    if not v_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant record not found for this authority."
        )

    old_variant_state = {
        "variant_name": v_row[1],
        "variant_type": v_row[2],
        "notes": v_row[3]
    }

    updated_name = payload.variant_name if payload.variant_name is not None else v_row[1]
    updated_type = payload.variant_type if payload.variant_type is not None else v_row[2]
    
    existing_notes = v_row[3] or ""
    append_note = f"[UPDATED by User {current_user['user_id']}]: {payload.reason.strip()}"
    updated_notes = f"{payload.notes or existing_notes}\n{append_note}".strip()

    cur.execute(
        """
        UPDATE public.authority_variants
        SET
            variant_name = %s,
            variant_type = %s,
            notes = %s
        WHERE variant_id = %s AND authority_id = %s
        RETURNING
            variant_id,
            authority_id,
            variant_name,
            variant_type,
            notes,
            created_at,
            created_by
        """,
        (
            updated_name,
            updated_type,
            updated_notes,
            variant_id,
            authority_id
        )
    )

    result = cur.fetchone()

    columns = [desc[0] for desc in cur.description]
    variant_data = dict(zip(columns, result))

    actor_id = str(current_user.get("user_id", "UNKNOWN"))
    actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
    actor_role = str(current_user.get("role", "The Chief"))

    audit_ok = log_audit_activity(
        request=request,
        user_id=actor_id,
        username=actor_name,
        role=actor_role,
        designation=str(current_user.get("designation") or actor_role),
        category="AUTHORITY_CONTROL",
        action_type="AUTHORITY_VARIANT_UPDATE",
        target_entity="AUTHORITY_VARIANT",
        target_id=str(variant_id),
        endpoint=request.url.path,
        http_method="PUT",
        justification=payload.reason,
        diff_payload={
            "authority_id": authority_id,
            "variant_id": variant_id,
            "previous": old_variant_state,
            "updated": {
                "variant_name": updated_name,
                "variant_type": updated_type,
                "notes": updated_notes
            }
        },
        extra_metadata={
            "authority_id": authority_id,
            "variant_id": variant_id
        },
        conn=conn
    )

    if not audit_ok:
        raise RuntimeError(
            "Audit record could not be written; operation rolled back"
        )
    
    conn.commit()

    return {
        "status": "success",
        "message": "Variant updated successfully.",
        "variant": variant_data
    }


@router.delete("/{authority_id}/variants/{variant_id}")
@audit_action(
    "AUTHORITY_VARIANT_DELETE",
    category="AUTHORITY_CONTROL",
    target_entity="AuthorityVariant",
    target_id_param="variant_id",
    reason_param="payload.reason"
)
def delete_variant(
    authority_id: int,
    variant_id: int,
    request: Request,
    payload: AuthorityActionPayload,
    db = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user)
):
    conn, cur = db
    _verify_editable_authority(cur, authority_id)

    cur.execute(
        """
        SELECT variant_id, variant_name, variant_type, notes
        FROM public.authority_variants
        WHERE variant_id = %s AND authority_id = %s
        FOR UPDATE
        """,
        (variant_id, authority_id)
    )
    v_row = cur.fetchone()

    if not v_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant record not found for this authority."
        )

    deleted_variant_info = {
        "variant_name": v_row[1],
        "variant_type": v_row[2],
        "notes": v_row[3]
    }

    cur.execute(
        """
        DELETE FROM public.authority_variants
        WHERE variant_id = %s AND authority_id = %s
        RETURNING variant_id
        """,
        (variant_id, authority_id)
    )
    cur.fetchone()

    actor_id = str(current_user.get("user_id", "UNKNOWN"))
    actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
    actor_role = str(current_user.get("role", "The Chief"))

    audit_ok = log_audit_activity(
        request=request,
        user_id=actor_id,
        username=actor_name,
        role=actor_role,
        designation=str(current_user.get("designation") or actor_role),
        category="AUTHORITY_CONTROL",
        action_type="AUTHORITY_VARIANT_DELETE",
        target_entity="AUTHORITY_VARIANT",
        target_id=str(variant_id),
        endpoint=request.url.path,
        http_method="DELETE",
        justification=payload.reason,
        diff_payload={
            "authority_id": authority_id,
            "variant_id": variant_id,
            "deleted": deleted_variant_info
        },
        extra_metadata={
            "authority_id": authority_id,
            "variant_id": variant_id
        },
        conn=conn
    )

    if not audit_ok:
        raise RuntimeError(
            "Audit record could not be written; operation rolled back"
        )
    
    conn.commit()

    return {
        "status": "success",
        "message": f"Variant ID {variant_id} deleted successfully."
    }