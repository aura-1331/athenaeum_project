# app/routers/items.py

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from app.database import get_connection
from app.auth import get_current_user, require_role
from app.audit_utils import audit_action
from app.services.audit_service import log_audit_activity

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

        # 2. Update bibliographic attributes on WORKS
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
            payload.get("title"), payload.get("author"), payload.get("language"),
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
            payload.get("title"), payload.get("author"), payload.get("publisher"),
            payload.get("year"), payload.get("genre"), payload.get("notes"),
            serial_no
        ))

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
                "updated": {k: v for k, v in payload.items() if v is not None}
            },
            extra_metadata={
                "serial_no": serial_no,
                "work_id": work_id
            }
        )

        return {"status": "success", "serial_no": serial_no, "work_id": work_id}

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()