from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from app.database import get_connection
from app.auth import get_current_user, require_role
from app.audit_utils import audit_action

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/{serial_no}")
def get_item(
    serial_no: int,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT w.title, w.author, w.language, w.publisher, w.year, w.genre, w.notes
            FROM works w
            WHERE w.serial_no = %s
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
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))]
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
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Resolve work_id from items
        cur.execute("SELECT work_id FROM public.items WHERE serial_no = %s", (serial_no,))
        item_row = cur.fetchone()
        if not item_row:
            raise HTTPException(status_code=404, detail="Holding not found")
        work_id = item_row[0]

        # 2. Update bibliographic attributes on WORKS
        cur.execute("""
            UPDATE public.works 
            SET title = %s, author = %s, language = %s, publisher = %s, year = %s, genre = %s, notes = %s
            WHERE work_id = %s
        """, (
            payload.get("title"), payload.get("author"), payload.get("language"),
            payload.get("publisher"), payload.get("year"), payload.get("genre"),
            payload.get("notes"), work_id
        ))

        # 3. Update denormalized attributes on ITEMS (excluding language)
        cur.execute("""
            UPDATE public.items 
            SET title = %s, author = %s, publisher = %s, year = %s, genre = %s, notes = %s
            WHERE serial_no = %s
        """, (
            payload.get("title"), payload.get("author"), payload.get("publisher"),
            payload.get("year"), payload.get("genre"), payload.get("notes"),
            serial_no
        ))

        conn.commit()
        return {"status": "success", "serial_no": serial_no, "work_id": work_id}
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()