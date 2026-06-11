from fastapi import APIRouter, HTTPException, Request
from app.database import get_connection
from app.audit_utils import audit_action

router = APIRouter(prefix="/health", tags=["health"])

@audit_action("HEALTH_CHECK")
@router.get("/")
def health_check(request: Request):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return {"status": "ok"}
    except Exception:
        # Return a simple 503 so monitoring tools know to alert you
        # without leaking database error details to the public.
        raise HTTPException(status_code=503, detail="Service Unavailable")
    finally:
        if conn:
            conn.close()