from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.database import get_connection

router = APIRouter(prefix="/accessions", tags=["accessions"])


# =========================================================
# ENTERPRISE ACCESSION NUMBER
# FORMAT:
# LIB-YYYY-00001
# =========================================================
def generate_accession_no(cur):

    year = datetime.now().year

    cur.execute(
        """
        SELECT accession_no
        FROM public.items
        WHERE accession_no LIKE %s
        ORDER BY accession_no DESC
        LIMIT 1
        """,
        (f"LIB-{year}-%",),
    )

    row = cur.fetchone()

    if not row:
        return f"LIB-{year}-00001"

    last = int(row[0].split("-")[-1]) + 1
    return f"LIB-{year}-{str(last).zfill(5)}"


# =========================================================
# CREATE ACCESSION (AUTO)
# =========================================================
@router.post("/create")
def create_accession(work_id: int, shelf: str = None):

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        accession_no = generate_accession_no(cursor)

        cursor.execute(
            """
            INSERT INTO public.items
            (accession_no, work_id, shelf)
            VALUES (%s,%s,%s)
            RETURNING accession_no
            """,
            (accession_no, work_id, shelf),
        )

        conn.commit()

        return {"accession_no": accession_no}

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
