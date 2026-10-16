# app/routers/admin_config.py

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_role
from app.database import get_connection
from app.routers.review_utils import _audit_ledger
from app.services.audit_service import verify_audit_ledger

logger = logging.getLogger(__name__)

# Root router exported to app/main.py
router = APIRouter()

audit_router = APIRouter(prefix="/admin/audit", tags=["Admin Audit & Security"])
config_router = APIRouter(prefix="/admin/config", tags=["System Configuration"])


class LedgerHealthResponse(BaseModel):
    status: str = Field(..., description="Ledger state: 'VALID', 'EMPTY', 'PARTIAL', or 'COMPROMISED'")
    inspected_count: Optional[int] = Field(None, description="Total verified ledger nodes")
    latest_head_hash: Optional[str] = Field(None, description="Cryptographic SHA-256 head hash")
    reason: Optional[str] = Field(None, description="Failure reason if compromised or incomplete")
    sequence_id: Optional[int] = Field(None, description="Sequence ID where breach occurred")
    record_id: Optional[str] = Field(None, description="UUID of compromised entry")
    expected_hash: Optional[str] = Field(None, description="Expected cryptographic signature")
    stored_hash: Optional[str] = Field(None, description="Found tampered signature")


@audit_router.get(
    "/health",
    response_model=LedgerHealthResponse,
    summary="Cryptographic Ledger Integrity Health Check",
    description=(
        "Traverses audit_activities sequentially, verifying prev_hash links "
        "and SHA-256 payload integrity."
    ),
    dependencies=[Depends(require_role(["The Chief"]))],
)
async def check_audit_ledger_health():
    result = verify_audit_ledger()

    ledger_status = result.get("status")
    if ledger_status in {"COMPROMISED", "PARTIAL"}:
        message = (
            "Audit ledger cryptographic integrity check failed: potential tampering detected."
            if ledger_status == "COMPROMISED"
            else "Audit ledger integrity could not be fully verified because one or more records are unhashed or incomplete."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": message,
                "diagnostics": result,
            },
        )

    return result


@config_router.patch("/{key}", dependencies=[Depends(require_role(["The Chief"]))])
async def update_config(
    key: str,
    new_value: float,
    request: Request,
    current_user: dict = Depends(get_current_user),
    x_change_reason: Optional[str] = Header(
        default="System configuration parameter adjustment"
    ),
):
    conn = None
    cur = None
    try:
        conn = get_connection(request=request)
        cur = conn.cursor()
        normalized_key = key.upper().strip()

        if not normalized_key:
            raise HTTPException(status_code=422, detail="Configuration key is required.")

        # Lock the row while reading its prior value and applying the update.
        cur.execute(
            "SELECT config_value FROM system_config WHERE config_key = %s FOR UPDATE",
            (normalized_key,),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration key '{normalized_key}' not found.",
            )

        old_value = row[0]

        cur.execute(
            """
            UPDATE system_config
            SET
                config_value = %s,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = %s
            WHERE config_key = %s
            RETURNING config_key
            """,
            (new_value, current_user["user_id"], normalized_key),
        )
        updated_row = cur.fetchone()
        if not updated_row:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Configuration could not be updated.",
            )

        reason = (x_change_reason or "").strip()
        if not reason:
            reason = f"Modified {normalized_key} from {old_value} to {new_value}"

        actor_id = str(current_user.get("user_id", "UNKNOWN"))
        _audit_ledger(
            request=request,
            current_user=current_user,
            conn=conn,
            action_type="UPDATE_CONFIG",
            target_entity="SYSTEM_CONFIG",
            target_id=normalized_key,
            category="SYSTEM_CONFIGURATION",
            http_method="PATCH",
            justification=reason,
            diff={
                "config_key": normalized_key,
                "old_value": old_value,
                "new_value": new_value,
            },
            before={"config_value": old_value},
            after={"config_value": new_value},
            extra={
                "config_key": normalized_key,
                "updated_by": actor_id,
            },
        )

        # Commit the configuration mutation and audit record atomically.
        conn.commit()

        return {
            "status": "success",
            "message": f"{normalized_key} updated to {new_value}",
            "previous_value": old_value,
            "current_value": new_value,
        }

    except HTTPException:
        if conn is not None:
            conn.rollback()
        raise
    except Exception as exc:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                logger.exception("Rollback failed after configuration update error")
        logger.exception("Configuration update failed for key %s", key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration.",
        ) from exc
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                logger.warning("Failed to close configuration cursor", exc_info=True)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                logger.warning("Failed to close configuration database connection", exc_info=True)


# Mount both sub-routers onto the exported router.
router.include_router(audit_router)
router.include_router(config_router)
