# app/routers/review_utils.py
"""Shared review/correction and audit helpers used by Work and Item modules.

This module intentionally contains no FastAPI router. Audit events are written
through the application's existing ``log_audit_activity`` service; these helpers
standardize payloads and metadata without implementing a second ledger or hash
chain.
"""

from typing import Optional

from fastapi import HTTPException, Request

from app.database import get_connection
from app.services.audit_service import log_audit_activity

MAX_NOTE_LENGTH = 2000


def _audit_norm(value) -> str:
    """Normalize a field value for audit/change comparisons."""
    return "" if value is None else str(value).strip()


def _audit_diff(before: Optional[dict], after: Optional[dict]) -> dict:
    """Return ``{field: {from, to}}`` for supplied fields that changed.

    ``after`` is treated as a partial update: keys omitted from it are not
    considered changed. The normalization matches the project's existing
    audit comparison behavior.
    """
    before = before or {}
    after = after or {}
    changes = {}

    for field, new_value in after.items():
        old_value = before.get(field)
        if _audit_norm(old_value) != _audit_norm(new_value):
            changes[field] = {"from": old_value, "to": new_value}

    return changes


def _audit_ledger_diff(before: Optional[dict], after: Optional[dict]) -> dict:
    """Build a reusable field-diff summary for audit/ledger payloads.

    This helper prepares comparison data only. It does not write an entry or
    calculate cryptographic hashes; the existing audit service owns that work.
    """
    fields = _audit_diff(before, after)
    return {
        "fields": fields,
        "changed_fields": sorted(fields.keys()),
        "changed_count": len(fields),
    }


def _audit_payload(
    *,
    action_type: str,
    target_entity: str,
    target_id,
    diff: Optional[dict] = None,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
) -> dict:
    """Prepare a backward-compatible ``diff_payload`` for the audit service.

    Existing payload keys are retained. If before/after values are supplied,
    a structured ``change_set`` is added; action/entity/target identifiers stay
    in the audit table's normal columns rather than being duplicated here.
    """
    payload = dict(diff or {})
    if before is not None or after is not None:
        payload["change_set"] = _audit_ledger_diff(before or {}, after or {})
    return payload


def _audit_metadata(
    request: Request,
    current_user: dict,
    extra: Optional[dict] = None,
    http_method: Optional[str] = None,
) -> dict:
    """Add consistent actor and request context without dropping custom keys."""
    metadata = dict(extra or {})
    context = dict(metadata.get("audit_context") or {})
    context["actor"] = {
        "user_id": str(current_user.get("user_id", "UNKNOWN")),
        "username": str(
            current_user.get("username")
            or current_user.get("name")
            or "Archive Operator"
        ),
        "role": str(current_user.get("role") or "UNKNOWN"),
        "designation": str(
            current_user.get("designation")
            or current_user.get("role")
            or "UNKNOWN"
        ),
    }
    context["request"] = {
        "endpoint": request.url.path,
        "http_method": http_method or request.method,
    }
    metadata["audit_context"] = context
    return metadata


def _audit_ledger_metadata(
    request: Request,
    current_user: dict,
    *,
    action_type: str,
    target_entity: str,
    target_id,
    category: str,
    extra: Optional[dict] = None,
    http_method: Optional[str] = None,
) -> dict:
    """Prepare event metadata to accompany an existing audit-ledger write.

    Hashes, sequence numbers, and ledger verification remain the responsibility
    of ``log_audit_activity`` and the application's ledger verification code.
    """
    metadata = _audit_metadata(
        request=request,
        current_user=current_user,
        extra=extra,
        http_method=http_method,
    )
    metadata["audit_event"] = {
        "action_type": str(action_type),
        "target_entity": str(target_entity).upper(),
        "target_id": str(target_id),
        "category": str(category),
    }
    return metadata


def _audit_ledger(
    request: Request,
    current_user: dict,
    conn,
    *,
    action_type: str,
    target_id,
    justification: str,
    diff: Optional[dict] = None,
    extra: Optional[dict] = None,
    http_method: str = "POST",
    target_entity: str = "ITEM",
    category: str = "ARCHIVAL_GOVERNANCE",
    before: Optional[dict] = None,
    after: Optional[dict] = None,
) -> bool:
    """Write a standardized event via the existing audit service."""
    role = str(current_user.get("role") or "UNKNOWN")
    designation = str(current_user.get("designation") or role or "UNKNOWN")

    diff_payload = _audit_payload(
        action_type=action_type,
        target_entity=target_entity,
        target_id=target_id,
        diff=diff,
        before=before,
        after=after,
    )
    extra_metadata = _audit_ledger_metadata(
        request,
        current_user,
        action_type=action_type,
        target_entity=target_entity,
        target_id=target_id,
        category=category,
        extra=extra,
        http_method=http_method,
    )

    ok = log_audit_activity(
        request=request,
        user_id=str(current_user.get("user_id", "UNKNOWN")),
        username=str(
            current_user.get("username")
            or current_user.get("name")
            or "Archive Operator"
        ),
        role=role,
        designation=designation,
        category=category,
        action_type=action_type,
        target_entity=str(target_entity).upper(),
        target_id=str(target_id),
        endpoint=request.url.path,
        http_method=http_method,
        justification=justification or "No reason given",
        diff_payload=diff_payload,
        extra_metadata=extra_metadata,
        conn=conn,
    )
    if not ok:
        raise RuntimeError("Audit record could not be written; operation rolled back")
    return True


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
            detail=f"{label} is too long (maximum {MAX_NOTE_LENGTH} characters).",
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
    """Compatibility wrapper used by existing Work/Item review endpoints."""
    return _audit_ledger(
        request=request,
        current_user=current_user,
        conn=conn,
        action_type=action_type,
        target_id=target_id,
        justification=justification,
        diff=diff,
        extra=extra,
        http_method=http_method,
        target_entity=target_entity,
        category="ARCHIVAL_GOVERNANCE",
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
    """Write a separate audit event for a refused action, if possible."""
    conn = None
    try:
        conn = get_connection(request=request)
        _write_audit(
            request,
            current_user,
            conn,
            action_type=action_type,
            target_id=target_id,
            justification=detail,
            diff={
                ("work_id" if str(entity).upper() == "WORK" else "serial_no"): target_id,
                "refused": True,
                "attempted": attempted,
            },
            extra={"refused": True},
            target_entity=str(entity).upper(),
        )
        conn.commit()
    except Exception as e:
        print(f"Refusal could not be audited: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def _open_correction(cur, entity: str, entity_id: int):
    cur.execute(
        """
        SELECT request_id, field_names, requested_by, requested_by_name,
               requested_at, status
        FROM public.correction_requests
        WHERE entity = %s AND entity_id = %s AND status = 'OPEN'
        LIMIT 1
        """,
        (entity, entity_id),
    )
    return cur.fetchone()


def _notes_for(cur, entity: str, entity_id: int) -> list:
    cur.execute(
        """
        SELECT note_id, request_id, kind, author_name, author_role,
               body, created_at
        FROM public.review_notes
        WHERE entity = %s AND entity_id = %s
        ORDER BY note_id ASC
        """,
        (entity, entity_id),
    )
    return [dict(row) for row in cur.fetchall()]
