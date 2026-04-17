from fastapi import APIRouter, HTTPException
from app.database import get_connection

router = APIRouter(prefix="/items", tags=["items"])

# 1. GET THE BOOK DATA (Fixes the "Could not find" error)
@router.get("/{serial_no}")
def get_item(serial_no: int):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # We join works and items so we get the full data for the edit form
        cur.execute("""
            SELECT w.title, w.author, w.language, w.publisher, w.year, w.genre, w.notes
            FROM works w
            WHERE w.serial_no = %s
        """, (serial_no,))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Book not found in database")
            
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

# 2. SAVE THE CHANGES (Updates both tables so search results change)
@router.put("/{serial_no}")
def update_item(serial_no: int, payload: dict):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Update the WORKS table (This is what the Search screen shows)
        cur.execute("""
            UPDATE works 
            SET title = %s, author = %s, language = %s, publisher = %s, year = %s, genre = %s, notes = %s
            WHERE serial_no = %s
        """, (
            payload.get("title"), payload.get("author"), payload.get("language"),
            payload.get("publisher"), payload.get("year"), payload.get("genre"),
            payload.get("notes"), serial_no
        ))

        # Update the ITEMS table (The physical copy record)
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
        cur.close()
        conn.close()