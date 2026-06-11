from fastapi import APIRouter, Depends, HTTPException, Request
from app.database import get_connection
from app.auth import get_current_user
from app.audit_utils import audit_action  # 🛡️ Integrated Auditing

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/{serial_no}")
def get_item(serial_no: int, current_user: dict = Depends(get_current_user)):
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
            raise HTTPException(status_code=404, detail="Book not found")
            
        return {
            "title": row[0], "author": row[1], "language": row[2],
            "publisher": row[3], "year": row[4], "genre": row[5], "notes": row[6]
        }
    finally:
        cur.close(); conn.close()

@audit_action("UPDATE_ITEM") # 🛡️ Tracks data integrity changes
@router.put("/{serial_no}")
def update_item(
    serial_no: int, 
    payload: dict, 
    request: Request, # 🛡️ Required for audit metadata
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["The Keeper", "The Chief"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Update WORKS table
        cur.execute("""
            UPDATE works 
            SET title = %s, author = %s, language = %s, publisher = %s, year = %s, genre = %s, notes = %s
            WHERE serial_no = %s
        """, (
            payload.get("title"), payload.get("author"), payload.get("language"),
            payload.get("publisher"), payload.get("year"), payload.get("genre"),
            payload.get("notes"), serial_no
        ))

        # Update ITEMS table
        cur.execute("""
            UPDATE items 
            SET title = %s, author = %s, language = %s
            WHERE serial_no = %s
        """, (
            payload.get("title"), payload.get("author"), payload.get("language"), serial_no
        ))

        conn.commit()
        return {"status": "success"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()