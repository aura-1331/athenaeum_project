from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth import get_current_user
from app.database import get_connection, record_audit

router = APIRouter(
    prefix="/locations",
    tags=["Item Location Tracking"]
)


class MoveRequest(BaseModel):
    serial_no: int
    location_name: str
    notes: str = ""


# -------------------------
# MOVE ITEM
# -------------------------
@router.post("/move")
async def move_item(
    payload: MoveRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["The Keeper", "The Chief"]:
        raise HTTPException(
            status_code=403,
            detail="Only archive staff can move items."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        # verify item exists
        cur.execute(
            """
            SELECT serial_no
            FROM items
            WHERE serial_no = %s
            """,
            (payload.serial_no,)
        )

        item = cur.fetchone()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Item not found."
            )

        cur.execute(
            """
            INSERT INTO item_locations (
                serial_no,
                location_name,
                moved_by,
                notes
            )
            VALUES (%s,%s,%s,%s)
            RETURNING location_id
            """,
            (
                payload.serial_no,
                payload.location_name,
                current_user["user_id"],
                payload.notes
            )
        )

        location_id = cur.fetchone()[0]

        await record_audit(
            current_user["user_id"],
            "MOVE_ITEM",
            request,
            str(payload.serial_no),
            f"Moved item to {payload.location_name}"
        )

        conn.commit()

        return {
            "message": "Item moved successfully",
            "location_id": location_id
        }

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()


# -------------------------
# CURRENT LOCATION
# -------------------------
@router.get("/current/{serial_no}")
def current_location(
    serial_no: int,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT location_name, moved_at, notes
            FROM item_locations
            WHERE serial_no = %s
            ORDER BY moved_at DESC
            LIMIT 1
            """,
            (serial_no,)
        )

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="No location history found."
            )

        return {
            "serial_no": serial_no,
            "current_location": row[0],
            "last_moved_at": row[1],
            "notes": row[2]
        }

    finally:
        cur.close()
        conn.close()


# -------------------------
# LOCATION HISTORY
# -------------------------
@router.get("/history/{serial_no}")
def location_history(
    serial_no: int,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                location_name,
                moved_by,
                moved_at,
                notes
            FROM item_locations
            WHERE serial_no = %s
            ORDER BY moved_at DESC
            """,
            (serial_no,)
        )

        rows = cur.fetchall()

        return [
            {
                "location": r[0],
                "moved_by": r[1],
                "moved_at": r[2],
                "notes": r[3]
            }
            for r in rows
        ]

    finally:
        cur.close()
        conn.close()