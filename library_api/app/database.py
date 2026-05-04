import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path
from fastapi import Request

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD") or os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", "5432")

print(f"--- ATTEMPTING CONNECTION ---")
print(f"File looked for at: {ENV_FILE}")
print(f"User: {DB_USER} | DB: {DB_NAME} | Pass Found: {DB_PASS is not None}")

def get_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            sslmode="require"
        )
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"DATABASE CONNECTION ERROR: {e}")
        raise RuntimeError(f"Database connection failed: {e}")
    
def get_config_value(key: str):
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT config_value FROM system_config WHERE config_key = %s", (key.upper(),))
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
    target_id: str = None,
    details: str = None,
    valid_reason: str = "SYSTEM"
):
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        ip_address = request.client.host
        user_agent = request.headers.get("user-agent", "").lower()

        if "ipad" in user_agent or "tablet" in user_agent:
            equipment = "TAB"
        elif "mobile" in user_agent or "iphone" in user_agent or "android" in user_agent:
            equipment = "PHONE"
        else:
            equipment = "COMPUTER"

        cur.execute("""
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
        """, (
            user_id,
            action_type,
            target_id,
            details,
            ip_address,
            equipment,
            valid_reason
        ))

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