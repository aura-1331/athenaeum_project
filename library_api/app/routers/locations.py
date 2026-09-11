# app/routers/locations.py

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.database import get_connection
from app.auth import get_current_user, require_role
from app.audit_utils import audit_action
from app.services.audit_service import log_audit_activity

router = APIRouter(prefix="/locations", tags=["Vault Locations"])


class MoveRequest(BaseModel):
    serial_no: int
    location_name: str
    notes: Optional[str] = "Physical shelf relocation"


# -------------------------
# PHYSICAL MOVEMENT / RELOCATION
# -------------------------
@router.post("/move", dependencies=[Depends(require_role(["The Keeper", "The Chief"]))])
@audit_action(
    "RELOCATE_HOLDING",
    category="VAULT_OPS",
    target_entity="Item",
    target_id_param="payload.serial_no",
    reason_param="payload.notes"
)
async def move_item(
    payload: MoveRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Verify item existence
        cur.execute("SELECT serial_no FROM public.items WHERE serial_no = %s", (payload.serial_no,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Holding record not found.")

        # 2. Retrieve previous physical location for ledger diff
        cur.execute("""
            SELECT location_name 
            FROM public.item_locations
            WHERE serial_no = %s
            ORDER BY moved_at DESC
            LIMIT 1
        """, (payload.serial_no,))
        prev_row = cur.fetchone()
        previous_location = prev_row[0] if prev_row else "UNASSIGNED"

        # 3. Record new physical placement
        cur.execute("""
            INSERT INTO public.item_locations (serial_no, location_name, moved_by, notes)
            VALUES (%s, %s, %s, %s) RETURNING location_id
        """, (payload.serial_no, payload.location_name, current_user["user_id"], payload.notes))

        location_id = cur.fetchone()[0]
        conn.commit()

        # 4. Cryptographic ledger anchor
        actor_id = str(current_user.get("user_id", "UNKNOWN"))
        actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
        actor_role = str(current_user.get("role", "The Keeper"))

        log_audit_activity(
            request=request,
            user_id=actor_id,
            username=actor_name,
            role=actor_role,
            designation=str(current_user.get("designation") or actor_role),
            category="VAULT_OPS",
            action_type="RELOCATE_HOLDING",
            target_entity="ITEM",
            target_id=str(payload.serial_no),
            endpoint=request.url.path,
            http_method="POST",
            justification=payload.notes or f"Relocated holding {payload.serial_no} to {payload.location_name}",
            diff_payload={
                "serial_no": payload.serial_no,
                "location_id": location_id,
                "from_location": previous_location,
                "to_location": payload.location_name,
                "notes": payload.notes
            },
            extra_metadata={
                "serial_no": payload.serial_no,
                "location_id": location_id
            }
        )

        return {"message": "Holding relocated successfully", "location_id": location_id}
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# -------------------------
# CURRENT LOCATION (READ-ONLY)
# -------------------------
@router.get("/current/{serial_no}")
def current_location(
    serial_no: int,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT location_name, moved_at, notes 
            FROM public.item_locations
            WHERE serial_no = %s 
            ORDER BY moved_at DESC 
            LIMIT 1
        """, (serial_no,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No relocation history for this holding.")

        return {
            "serial_no": serial_no,
            "location_name": row[0],
            "moved_at": row[1],
            "notes": row[2]
        }
    finally:
        cur.close()
        conn.close()