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

def get_connection(request: Request = None, username: str = None, role: str = None):
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            sslmode=os.getenv("DB_SSLMODE", "require")
        )
        conn.autocommit = False
        
        actor_name = username
        actor_role = role
        
        if not actor_name and request is not None:
            actor_role = getattr(request.state, "actor_role", None) or request.headers.get("X-User-Role")
            
            # Check if there is an explicit name header or state
            token_user_id = getattr(request.state, "actor_name", None) or request.headers.get("X-User-Name")
            
            # If the username is a raw numeric string ID (like '3'), resolve it to the real name
            if token_user_id and token_user_id.isdigit():
                cur_lookup = conn.cursor()
                try:
                    cur_lookup.execute("SELECT name FROM public.users WHERE user_id = %s", (int(token_user_id),))
                    row = cur_lookup.fetchone()
                    actor_name = row[0] if row else token_user_id
                except Exception:
                    actor_name = token_user_id
                finally:
                    cur_lookup.close()
            else:
                actor_name = token_user_id
            
        actor_name = actor_name or "SYSTEM_UNKNOWN"
        actor_role = actor_role or "SYSTEM_UNKNOWN"
            
        cur = conn.cursor()
        try:
            cur.execute("SELECT public.set_audit_session_context(%s, %s);", (actor_name, actor_role))
        finally:
            cur.close()
                
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