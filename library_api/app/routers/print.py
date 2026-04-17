from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from psycopg2.extras import RealDictCursor
from io import BytesIO

from app.database import get_connection
from app.auth import get_current_user
from pdf.pdf_generator import generate_pdf

router = APIRouter(prefix="/print", tags=["print"])


@router.get("/{serial_no}")
async def print_book(serial_no: int, current_user: dict = Depends(get_current_user)):

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 🔹 SAME QUERY AS YOUR CATALOGUE
        query = """
            SELECT 
                i.serial_no, 
                i.accession_no, 
                i.shelf, 
                w.language as language,
                w.title, 
                w.author, 
                w.publisher, 
                w.year, 
                w.isbn, 
                w.ddc, 
                w.call_no,
                w.original_language, 
                w.notes,
                w.category,
                w.genre,
                w.translation_compilation
            FROM public.items i
            INNER JOIN public.works w ON i.work_id = w.work_id
            WHERE i.serial_no = %s AND i.is_deleted = FALSE
        """

        cur.execute(query, (serial_no,))
        record = cur.fetchone()

        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        # ✅ CORRECT MAPPING (IMPORTANT)
        record_dict = {
            "title": record["title"],
            "author": record["author"],
            "publisher": record["publisher"],
            "year": record["year"],
            "category": record["category"],
            "language": record["language"],

            "original_language": record["original_language"],
            "work_nature": record["translation_compilation"],
            "isbn": record["isbn"],
            "ddc": record["ddc"],
            "call_number": record["call_no"],
            "shelf_location": record["shelf"],

            "serial_no": record["serial_no"],
            "accession_no": record["accession_no"],
            "notes": record["notes"]
        }

        audit = {
            "userName": current_user.get("username", "SYSTEM"),
            "deviceID": "LOCAL"
        }

        pdf_bytes = await generate_pdf(record_dict, audit)

        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=record_{serial_no}.pdf"
            }
        )

    except Exception as e:
        print(f"❌ PRINT ERROR: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

    finally:
        cur.close()
        conn.close()