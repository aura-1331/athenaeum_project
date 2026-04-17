# app/routers/health.py

from fastapi import APIRouter
from app.database import get_connection

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
def health_check():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1")
        cur.fetchone()
        return {"status": "ok"}
    finally:
        cur.close()
        conn.close()
