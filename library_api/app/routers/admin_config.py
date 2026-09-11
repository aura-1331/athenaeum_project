# app/routers/admin_config.py

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_role
from app.database import get_connection
from app.audit_utils import audit_action
from app.services.audit_service import log_audit_activity, verify_audit_ledger

# Root router exported to app/main.py
router = APIRouter()

audit_router = APIRouter(prefix="/admin/audit", tags=["Admin Audit & Security"])
config_router = APIRouter(prefix="/admin/config", tags=["System Configuration"])


class LedgerHealthResponse(BaseModel):
    status: str = Field(..., description="Ledger state: 'VALID', 'EMPTY', or 'COMPROMISED'")
    inspected_count: Optional[int] = Field(None, description="Total verified ledger nodes")
    latest_head_hash: Optional[str] = Field(None, description="Cryptographic SHA-256 head hash")
    reason: Optional[str] = Field(None, description="Failure reason if compromised")
    sequence_id: Optional[int] = Field(None, description="Sequence ID where breach occurred")
    record_id: Optional[str] = Field(None, description="UUID of compromised entry")
    expected_hash: Optional[str] = Field(None, description="Expected cryptographic signature")
    stored_hash: Optional[str] = Field(None, description="Found tampered signature")


@audit_router.get(
    "/health",
    response_model=LedgerHealthResponse,
    summary="Cryptographic Ledger Integrity Health Check",
    description="Traverses audit_activities sequentially, verifying prev_hash links and SHA-256 payload integrity.",
    dependencies=[Depends(require_role(["The Chief"]))],
)
async def check_audit_ledger_health():
    result = verify_audit_ledger()

    if result.get("status") == "COMPROMISED":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Audit ledger cryptographic integrity check failed: potential tampering detected.",
                "diagnostics": result,
            },
        )

    return result


@audit_action("UPDATE_CONFIG")
@config_router.patch("/{key}", dependencies=[Depends(require_role(["The Chief"]))])
async def update_config(
    key: str,
    new_value: float,
    request: Request,
    current_user: dict = Depends(get_current_user),
    x_change_reason: Optional[str] = Header(default="System configuration parameter adjustment")
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        normalized_key = key.upper().strip()

        # 1. Fetch baseline configuration before mutation
        cur.execute(
            "SELECT config_value FROM system_config WHERE config_key = %s",
            (normalized_key,)
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Configuration key '{normalized_key}' not found."
            )

        old_value = row[0]

        # 2. Mutate system configuration
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
            (
                new_value,
                current_user["user_id"],
                normalized_key
            )
        )

        conn.commit()

        # 3. Anchor state transition into cryptographic ledger
        actor_id = str(current_user.get("user_id", "UNKNOWN"))
        actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
        actor_role = str(current_user.get("role", "The Chief"))

        log_audit_activity(
            request=request,
            user_id=actor_id,
            username=actor_name,
            role=actor_role,
            designation=str(current_user.get("designation") or actor_role),
            category="SYSTEM_CONFIGURATION",
            action_type="UPDATE_CONFIG",
            target_entity="SYSTEM_CONFIG",
            target_id=normalized_key,
            endpoint=request.url.path,
            http_method="PATCH",
            justification=x_change_reason or f"Modified {normalized_key} from {old_value} to {new_value}",
            diff_payload={
                "config_key": normalized_key,
                "old_value": old_value,
                "new_value": new_value
            },
            extra_metadata={
                "config_key": normalized_key,
                "updated_by": actor_id
            }
        )

        return {
            "status": "success",
            "message": f"{normalized_key} updated to {new_value}",
            "previous_value": old_value,
            "current_value": new_value
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"Config Update Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update configuration."
        )
    finally:
        cur.close()
        conn.close()


# Mount both sub-routers onto the exported router
router.include_router(audit_router)
router.include_router(config_router)