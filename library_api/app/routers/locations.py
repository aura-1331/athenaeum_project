from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.auth import get_current_user, require_role # 1. Import require_role
from app.database import get_connection
from app.audit_utils import audit_action

router = APIRouter(prefix="/locations", tags=["Item Location Tracking"])

class MoveRequest(BaseModel):
    serial_no: int
    location_name: str
    notes: str = ""

# -------------------------
# MOVE ITEM
# -------------------------
@audit_action("MOVE_ITEM")
@router.post("/move", dependencies=[Depends(require_role(["The Keeper", "The Chief"]))]) # 2. Add Security Guard
async def move_item(
    payload: MoveRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    # 3. Manual 'if current_user["role"]...' check removed
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT serial_no FROM items WHERE serial_no = %s", (payload.serial_no,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Item not found.")

        cur.execute("""
            INSERT INTO item_locations (serial_no, location_name, moved_by, notes)
            VALUES (%s, %s, %s, %s) RETURNING location_id
        """, (payload.serial_no, payload.location_name, current_user["user_id"], payload.notes))

        location_id = cur.fetchone()[0]
        conn.commit()
        return {"message": "Item moved successfully", "location_id": location_id}
    finally:
        cur.close(); conn.close()

# -------------------------
# CURRENT LOCATION
# -------------------------
@audit_action("VIEW_CURRENT_LOCATION")
@router.get("/current/{serial_no}")
def current_location(serial_no: int, request: Request, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT location_name, moved_at, notes FROM item_locations 
            WHERE serial_no = %s ORDER BY moved_at DESC LIMIT 1
        """, (serial_no,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No location history found.")
        return {"serial_no": serial_no, "current_location": row[0], "last_moved_at": row[1], "notes": row[2]}
    finally:
        cur.close(); conn.close()

# -------------------------
# LOCATION HISTORY
# -------------------------
@audit_action("VIEW_LOCATION_HISTORY")
@router.get("/history/{serial_no}")
def location_history(serial_no: int, request: Request, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT location_name, moved_by, moved_at, notes FROM item_locations 
            WHERE serial_no = %s ORDER BY moved_at DESC
        """, (serial_no,))
        return [{"location": r[0], "moved_by": r[1], "moved_at": r[2], "notes": r[3]} for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()