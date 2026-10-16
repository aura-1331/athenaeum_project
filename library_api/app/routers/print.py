from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from psycopg2.extras import RealDictCursor

from app.auth import get_current_user, require_role
from app.database import get_connection
from app.routers.review_utils import _audit_ledger
from pdf.pdf_generator import generate_pdf

router = APIRouter(prefix="/print", tags=["print"])


@router.get(
    "/{serial_no}",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))],
)
async def print_book(
    serial_no: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Generate a printable catalogue record after recording the export audit."""
    conn = get_connection(request=request)
    cur = None

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT
                i.serial_no,
                i.accession_no,
                i.shelf,
                w.language AS language,
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
            FROM public.items AS i
            INNER JOIN public.works AS w ON w.work_id = i.work_id
            WHERE i.serial_no = %s
              AND i.is_deleted = FALSE
            """,
            (serial_no,),
        )
        record = cur.fetchone()

        if not record:
            raise HTTPException(status_code=404, detail="Record not found.")

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
            "notes": record["notes"],
        }

        client_address = request.client.host if request.client else "UNKNOWN"
        audit_context = {
            # Preserve the keys expected by the existing PDF generator.
            "userName": str(
                current_user.get("username")
                or current_user.get("name")
                or current_user.get("user_id")
                or "Archive Operator"
            ),
            "deviceID": client_address,
        }

        # Generate the document before logging a successful export. If PDF
        # generation fails, no PRINT_RECORD event is written. If audit writing
        # fails, the document is not returned to the caller.
        pdf_bytes = await generate_pdf(record_dict, audit_context)
        if not isinstance(pdf_bytes, (bytes, bytearray)):
            raise RuntimeError("PDF generator did not return bytes.")

        _audit_ledger(
            request=request,
            current_user=current_user,
            conn=conn,
            action_type="PRINT_RECORD",
            target_entity="ITEM",
            target_id=serial_no,
            category="DOCUMENT_EXPORT",
            http_method="GET",
            justification=f"Generated printable PDF record for Item {serial_no}.",
            diff={
                "serial_no": serial_no,
                "accession_no": record["accession_no"],
                "document_type": "PDF_CATALOGUE_RECORD",
                "export_completed": True,
            },
            extra={
                "export_format": "application/pdf",
                "export_completed": True,
            },
        )
        conn.commit()

        return StreamingResponse(
            BytesIO(bytes(pdf_bytes)),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=record_{serial_no}.pdf"
            },
        )

    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        print(f"PRINT ERROR for Item {serial_no}: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate or audit the PDF export.",
        ) from exc
    finally:
        if cur is not None:
            cur.close()
        conn.close()
