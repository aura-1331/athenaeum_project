import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import Request
import psycopg2

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD") or os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")

def get_connection(
    request: Optional[Request] = None,
    username: Optional[str] = None,
    role: Optional[str] = None
):
    """Establishes raw database connection and sets PostgreSQL audit session context."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            sslmode=DB_SSLMODE
        )
        conn.autocommit = False

        # A verified FastAPI auth dependency is authoritative whenever present.
        # Caller-supplied username/role must never override the authenticated request identity.
        request_actor_name = getattr(request.state, "actor_name", None) if request is not None else None
        request_actor_role = getattr(request.state, "actor_role", None) if request is not None else None

        if request_actor_name:
            actor_name = str(request_actor_name)
            actor_role = str(request_actor_role or role or "SYSTEM_UNKNOWN")
        else:
            actor_name = username or "SYSTEM_UNKNOWN"
            actor_role = role or "SYSTEM_UNKNOWN"

        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT public.set_audit_session_context(%s, %s);",
                (actor_name, actor_role)
            )
        finally:
            cur.close()

        return conn

    except Exception as e:
        print(f"DATABASE CONNECTION ERROR: {e}")
        raise RuntimeError("Database connection failed")


def get_db_connection(request: Request):
    """FastAPI dependency yielding (conn, cur) with request-aware audit context and automatic cleanup."""
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        yield conn, cur
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def get_config_value(key: str) -> Optional[float]:
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT config_value FROM system_config WHERE config_key = %s",
            (key.upper(),)
        )
        res = cur.fetchone()
        return float(res[0]) if res else None
    except Exception as e:
        print(f"Config Error: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


async def record_audit(
    user_id: int,
    action_type: str,
    request: Request,
    target_id: Optional[str] = None,
    details: Optional[str] = None,
    valid_reason: str = "SYSTEM"
):
    conn = None
    cur = None
    try:
        conn = get_connection(request=request)
        cur = conn.cursor()

        ip_address = request.client.host if request.client else "UNKNOWN"
        user_agent = request.headers.get("user-agent", "").lower()

        if "ipad" in user_agent or "tablet" in user_agent:
            equipment = "TAB"
        elif "mobile" in user_agent or "iphone" in user_agent or "android" in user_agent:
            equipment = "PHONE"
        else:
            equipment = "COMPUTER"

        cur.execute(
            """
            INSERT INTO audit_logs (
                user_id,
                action_type,
                target_id,
                details,
                ip_address,
                equipment,
                valid_reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                action_type,
                target_id,
                details,
                ip_address,
                equipment,
                valid_reason
            )
        )
        conn.commit()

    except Exception as e:
        print(f"CRITICAL AUDIT ERROR: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()