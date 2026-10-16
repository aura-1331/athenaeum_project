"""Physical item location tracking for Athenaeum."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_role
from app.database import get_connection
from app.routers.review_utils import _audit_ledger

router = APIRouter(prefix="/locations", tags=["Vault Locations"])


class MoveRequest(BaseModel):
    serial_no: int
    location_name: str
    notes: Optional[str] = "Physical shelf relocation"


# -------------------------
# PHYSICAL MOVEMENT / RELOCATION
# -------------------------
@router.post(
    "/move",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))],
)
async def move_item(
    payload: MoveRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    location_name = str(payload.location_name or "").strip()
    if not location_name:
        raise HTTPException(status_code=400, detail="A destination location is required.")

    notes = str(payload.notes or "").strip()
    if len(notes) > 2000:
        raise HTTPException(status_code=400, detail="Notes are too long (maximum 2000 characters).")

    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        # Verify that the holding exists before recording a movement.
        cur.execute(
            """
            SELECT serial_no
            FROM public.items
            WHERE serial_no = %s
            """,
            (payload.serial_no,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Holding record not found.")

        # Capture the previous location for the audit change set.
        cur.execute(
            """
            SELECT location_name
            FROM public.item_locations
            WHERE serial_no = %s
            ORDER BY moved_at DESC, location_id DESC
            LIMIT 1
            """,
            (payload.serial_no,),
        )
        prev_row = cur.fetchone()
        previous_location = prev_row[0] if prev_row else None

        # Record the new physical placement in the same transaction as its audit.
        cur.execute(
            """
            INSERT INTO public.item_locations
                (serial_no, location_name, moved_by, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING location_id
            """,
            (payload.serial_no, location_name, current_user["user_id"], notes or None),
        )
        location_id = cur.fetchone()[0]

        _audit_ledger(
            request=request,
            current_user=current_user,
            conn=conn,
            action_type="RELOCATE_HOLDING",
            target_entity="ITEM",
            target_id=payload.serial_no,
            category="VAULT_OPS",
            http_method="POST",
            justification=notes or f"Relocated holding {payload.serial_no} to {location_name}",
            diff={
                "serial_no": payload.serial_no,
                "location_id": location_id,
                "from_location": previous_location or "UNASSIGNED",
                "to_location": location_name,
                "notes": notes or None,
            },
            extra={
                "serial_no": payload.serial_no,
                "location_id": location_id,
            },
            before={"location_name": previous_location},
            after={"location_name": location_name},
        )

        conn.commit()
        return {
            "message": "Holding relocated successfully",
            "location_id": location_id,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        print(f"Item relocation failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="Unable to relocate the holding.") from exc
    finally:
        cur.close()
        conn.close()


# -------------------------
# CURRENT LOCATION (READ-ONLY)
# -------------------------
@router.get(
    "/current/{serial_no}",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))],
)
def current_location(
    request: Request,
    serial_no: int,
    current_user: dict = Depends(get_current_user),
):
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT location_name, moved_at, notes
            FROM public.item_locations
            WHERE serial_no = %s
            ORDER BY moved_at DESC, location_id DESC
            LIMIT 1
            """,
            (serial_no,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail="No relocation history for this holding.",
            )

        return {
            "serial_no": serial_no,
            "location_name": row[0],
            "moved_at": row[1],
            "notes": row[2],
        }
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        print(f"Current location lookup failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="Unable to retrieve the current location.") from exc
    finally:
        cur.close()
        conn.close()
