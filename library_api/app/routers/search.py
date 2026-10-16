"""Catalogue search and autocomplete endpoints.

Search endpoints retain the project's existing audit_action integration.
Only approved Works and non-pending, non-deleted Items are exposed through
catalogue search, so unpublished proposals do not appear in public results.
"""

from fastapi import APIRouter, Depends, Query, Request
from psycopg2.extras import RealDictCursor

from app.database import get_connection
from app.auth import get_current_user
from app.audit_utils import audit_action

router = APIRouter(prefix="/search", tags=["search"])


# ================= GLOBAL SEARCH =================
@router.get("")
@audit_action("GLOBAL_SEARCH")
def global_search(
    request: Request,
    q: str = Query("", max_length=200),
    page: int = Query(1, ge=1, le=100000),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    offset = (page - 1) * limit

    try:
        query = """
            SELECT
                i.serial_no,
                i.accession_no,
                w.title,
                w.author,
                w.language,
                CASE
                    WHEN LOWER(w.title) = LOWER(%s) THEN 100
                    WHEN w.title ILIKE %s THEN 80
                    WHEN w.title ILIKE %s THEN 60
                    WHEN w.author ILIKE %s THEN 40
                    ELSE 0
                END AS score
            FROM public.items AS i
            INNER JOIN public.works AS w
                ON i.work_id = w.work_id
            WHERE i.is_deleted = FALSE
              AND UPPER(TRIM(COALESCE(w.status, ''))) = 'APPROVED'
              AND UPPER(TRIM(COALESCE(i.availability_status, ''))) <> 'PENDING'
              AND (
                    w.search_vector @@ plainto_tsquery('english', %s)
                    OR w.title ILIKE %s
                    OR w.author ILIKE %s
              )
            ORDER BY score DESC, i.serial_no
            LIMIT %s OFFSET %s
        """
        cur.execute(
            query,
            (
                q,
                f"{q}%",
                f"%{q}%",
                f"%{q}%",
                q,
                f"%{q}%",
                f"%{q}%",
                limit,
                offset,
            ),
        )
        rows = cur.fetchall()
        return {"data": rows, "page": page, "limit": limit}
    finally:
        cur.close()
        conn.close()


# ================= AUTOCOMPLETE =================
@router.get("/suggest")
@audit_action("SEARCH_SUGGEST")
def suggest(
    request: Request,
    q: str = Query("", max_length=200),
    current_user: dict = Depends(get_current_user),
):
    if not q.strip():
        return []

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT
                w.title,
                w.author,
                CASE
                    WHEN LOWER(w.title) = LOWER(%s) THEN 100
                    WHEN w.title ILIKE %s THEN 80
                    ELSE 0
                END AS score
            FROM public.works AS w
            WHERE UPPER(TRIM(COALESCE(w.status, ''))) = 'APPROVED'
              AND (w.title ILIKE %s OR w.author ILIKE %s)
            ORDER BY score DESC, w.title ASC
            LIMIT 10
            """,
            (q, f"{q}%", f"%{q}%", f"%{q}%"),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()
