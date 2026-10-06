import base64
import traceback
import uuid
from typing import Optional
from fastapi import APIRouter, Query, Request, HTTPException, Depends
from pydantic import BaseModel
import psycopg2.extras

from app.database import get_connection
from app.auth import get_current_user, require_role
from app.services.audit_service import log_audit_activity, verify_audit_ledger

router = APIRouter(prefix="/status_audit", tags=["Status & Auditing"])

# ------------------------------------------------------------
# Helper Utilities
# ------------------------------------------------------------
def format_duration(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return "< 1s"
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if mins > 0:
        parts.append(f"{mins}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


# ------------------------------------------------------------
# Request Models
# ------------------------------------------------------------
class LoginSessionPayload(BaseModel):
    user_id: Optional[str] = "3"
    username: Optional[str] = "Helix Aura Ravenfall"
    role: Optional[str] = "The Chief"
    designation: Optional[str] = "Staff"
    machine_name: Optional[str] = "TERMINAL-01"


class LogoutSessionPayload(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    reason: Optional[str] = "Operator initiated sign-out"


# ------------------------------------------------------------
# 1. FETCH AUDIT ACTIVITIES (Ledger View)
# ------------------------------------------------------------
@router.get("/system-logs", dependencies=[Depends(require_role(["The Chief"]))])
def get_system_logs(
    actor_filter: Optional[str] = None,
    action_filter: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=1000000)
):
    conn = get_connection()
    try:
        conn.rollback()
    except Exception:
        pass

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        where_clauses = []
        params = []

        if actor_filter:
            where_clauses.append(
                '("username" ILIKE %s OR "user_id" ILIKE %s OR "target_id" ILIKE %s OR "justification" ILIKE %s)'
            )
            term = f"%{actor_filter}%"
            params.extend([term, term, term, term])

        if action_filter:
            where_clauses.append('("action_type" ILIKE %s OR "category" ILIKE %s)')
            act_term = f"%{action_filter}%"
            params.extend([act_term, act_term])

        where_sql = ""
        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)

        cur.execute(f"SELECT COUNT(*) as count FROM audit_activities{where_sql}", tuple(params))
        total_count = cur.fetchone()["count"]

        query = f"""
            SELECT * FROM audit_activities
            {where_sql}
            ORDER BY "timestamp" DESC
            LIMIT %s OFFSET %s
        """
        fetch_params = list(params) + [limit, offset]
        cur.execute(query, tuple(fetch_params))
        rows = cur.fetchall()

        items = []
        for r in rows:
            ts_val = r.get("timestamp")
            items.append({
                "id": str(r.get("id") or ""),
                "sequence_id": r.get("sequence_id"),
                "timestamp": str(ts_val) if ts_val else "",
                "actor_username": r.get("username") or f"User #{r.get('user_id', 'SYS')}",
                "user_id": str(r.get("user_id") or "SYS"),
                "actor_role": r.get("role") or "OPERATOR",
                "designation": r.get("designation") or "Staff",
                "action_type": r.get("action_type") or "ACTION",
                "target_id": str(r.get("target_id")) if r.get("target_id") is not None else None,
                "target_entity": r.get("target_entity") or "GLOBAL",
                "summary": r.get("justification") or f"Action {r.get('action_type')} recorded.",
                "ip_address": r.get("ip_address") or "127.0.0.1",
                "device_id": r.get("machine_name") or "TERMINAL-01",
                "change_reason": r.get("justification") or "Standard operational workflow.",
                "detailed_diffs": r.get("diff_payload"),
                "category": r.get("category"),
                "endpoint": r.get("endpoint"),
                "http_method": r.get("http_method"),
                "prev_hash": r.get("prev_hash"),
                "record_hash": r.get("record_hash")
            })

        return {
            "total": total_count,
            "items": items
        }
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ------------------------------------------------------------
# 2. SESSION LIFECYCLE (LOGIN / LOGOUT / DURATION)
# ------------------------------------------------------------
@router.post("/session/login")
def login_session(payload: LoginSessionPayload, request: Request, current_user: dict = Depends(get_current_user)):

    conn = get_connection()
    try:
        conn.rollback()
    except Exception:
        pass

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        ip_address = request.client.host if request.client else "127.0.0.1"
        session_id = str(uuid.uuid4())

        cur.execute("""
            INSERT INTO user_sessions (
                id, user_id, username, role, designation, machine_name, ip_address, login_at, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), TRUE)
            RETURNING id, login_at
        """, (
            session_id,
            str(current_user.get("user_id") or ""),
            str(current_user.get("username") or current_user.get("name") or ""),
            str(current_user.get("role") or ""),
            str(current_user.get("designation") or current_user.get("role") or "Staff"),
            "SERVER-RECORDED-CLIENT",
            ip_address
        ))

        row = cur.fetchone()

        # Write immutable audit entry
        audit_ok = log_audit_activity(
            request=request,
            session_id=session_id,
            user_id=str(current_user.get("user_id") or ""),
            username=str(current_user.get("username") or current_user.get("name") or ""),
            role=str(current_user.get("role") or ""),
            designation=str(current_user.get("designation") or current_user.get("role") or "Staff"),
            category="AUTH",
            action_type="LOGIN",
            target_entity="GLOBAL",
            justification="Secure login session opened.",
            conn=conn
        )

        if not audit_ok:
            raise RuntimeError(
                "Audit record could not be written; operation rolled back"
            )
        
        conn.commit()

        return {
            "status": "Session opened",
            "session_id": str(row["id"]),
            "user_id": str(current_user.get("user_id") or ""),
            "login_at": str(row["login_at"])
        }
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cur.close()
        conn.close()


@router.post("/session/logout")
def logout_session(payload: LogoutSessionPayload, request: Request, current_user: dict = Depends(get_current_user)):

    conn = get_connection()
    try:
        conn.rollback()
    except Exception:
        pass

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        ip_address = request.client.host if request.client else "127.0.0.1"
        user_id_str = str(current_user.get("user_id") or "")
        username = str(current_user.get("username") or current_user.get("name") or "")
        role = str(current_user.get("role") or "")
        reason = payload.reason or "Operator initiated sign-out"

        # Identify target session to close
        target_session_id = payload.session_id
        if target_session_id:
            cur.execute("""
                SELECT id FROM user_sessions
                WHERE id = %s AND user_id = %s AND is_active = TRUE
            """, (target_session_id, user_id_str))
            if not cur.fetchone():
                raise HTTPException(status_code=403, detail="You may only close your own active session.")
        else:
            cur.execute("""
                SELECT id FROM user_sessions
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY login_at DESC
                LIMIT 1
            """, (user_id_str,))
            row = cur.fetchone()
            if row:
                target_session_id = row["id"]

        duration = 0
        if target_session_id:
            cur.execute("""
                UPDATE user_sessions
                SET logout_at = NOW(),
                    duration_seconds = GREATEST(1, EXTRACT(EPOCH FROM (NOW() - login_at))::INT),
                    is_active = FALSE
                WHERE id = %s AND user_id = %s
                RETURNING duration_seconds
            """, (target_session_id, user_id_str))
            updated_row = cur.fetchone()
            if updated_row and updated_row.get("duration_seconds") is not None:
                duration = updated_row["duration_seconds"]

        formatted_time = format_duration(duration)

        # Write immutable audit entry
        audit_ok = log_audit_activity(
            request=request,
            session_id=target_session_id,
            user_id=user_id_str,
            username=username,
            role=role,
            designation="Staff",
            category="AUTH",
            action_type="LOGOUT",
            target_entity="GLOBAL",
            justification=reason,
            diff_payload={"duration_seconds": duration, "duration_formatted": formatted_time},
            conn=conn
        )

        if not audit_ok:
            raise RuntimeError(
                "Audit record could not be written; operation rolled back"
            )
        
        conn.commit()

        return {
            "status": "Session closed",
            "session_id": target_session_id,
            "duration_seconds": duration,
            "formatted_duration": formatted_time
        }
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cur.close()
        conn.close()


# ------------------------------------------------------------
# 3. GET SESSION HISTORIES
# ------------------------------------------------------------
@router.get("/sessions", dependencies=[Depends(require_role(["The Chief"]))])
def get_user_sessions(user_id: Optional[str] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0, le=1000000)):
    conn = get_connection()
    try:
        conn.rollback()
    except Exception:
        pass

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        query = "SELECT * FROM user_sessions"
        params = []

        if user_id:
            query += ' WHERE "user_id" = %s'
            params.append(str(user_id))

        query += ' ORDER BY "login_at" DESC LIMIT %s OFFSET %s'
        params.extend([limit, offset])

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        return [
            {
                "session_id": str(r["id"]),
                "user_id": str(r["user_id"]),
                "username": r["username"],
                "role": r["role"],
                "designation": r["designation"],
                "machine_name": r["machine_name"],
                "ip_address": r["ip_address"],
                "login_at": str(r["login_at"]) if r["login_at"] else "",
                "logout_at": str(r["logout_at"]) if r["logout_at"] else None,
                "duration_seconds": r["duration_seconds"],
                "status": "ACTIVE" if r["is_active"] else "COMPLETED"
            }
            for r in rows
        ]
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cur.close()
        conn.close()


# ------------------------------------------------------------
# 4. CRYPTOGRAPHIC LEDGER VERIFICATION
# ------------------------------------------------------------
@router.get("/ledger/verify")
def get_ledger_verification(request: Request, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "The Chief":
        raise HTTPException(status_code=403, detail="Chief access required.")

    result = verify_audit_ledger()
    print("DEBUG LEDGER RESULT:", result)  # <--- ADD THIS LINE

    # If the ledger was tampered with, log it to the security_incidents table
    status_str = str(result.get("status") or "").upper()
    if status_str in ("TAMPERED", "COMPROMISED", "INVALID"):
        compromised_seq = result.get("sequence_id") or result.get("record_id")
        reason_text = result.get("reason") or result.get("detail") or "Cryptographic mismatch"

        conn = get_connection(request=request)
        cur = conn.cursor()
        try:
            # Check if an unresolved incident already exists for this node
            cur.execute("""
                SELECT id FROM security_incidents 
                WHERE compromised_sequence_id = %s AND resolved = FALSE
                LIMIT 1
            """, (compromised_seq,))
            existing = cur.fetchone()

            if not existing:
                cur.execute("""
                    INSERT INTO security_incidents (
                        incident_type, 
                        severity, 
                        compromised_sequence_id, 
                        details, 
                        resolved
                    )
                    VALUES (
                        'CHAIN_INTEGRITY_BREACH',
                        'CRITICAL',
                        %s,
                        %s,
                        FALSE
                    )
                """, (compromised_seq, f"Breach detected: {reason_text}"))
                conn.commit()
                print("[INCIDENT INSERT SUCCESS] New breach ticket created!")
            else:
                print(f"[INCIDENT SKIPPED] Unresolved ticket already exists for node #{compromised_seq}")
        except Exception as e:
            conn.rollback()
            print(f"[SECURITY ALERT ERROR]: {type(e).__name__} - {e}")
            traceback.print_exc()
        finally:
            cur.close()
            conn.close()
    return result

# ------------------------------------------------------------
# 5. GLOBAL SECURITY STATUS
# ------------------------------------------------------------
@router.get("/global-status")
def get_global_security_status():
    """
    Minimal public status signal for the global application indicator.

    Exposes only whether an unresolved critical ledger integrity
    incident exists. No incident details or security records are
    exposed through this endpoint.
    """
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM security_incidents
                WHERE incident_type = 'CHAIN_INTEGRITY_BREACH'
                  AND severity = 'CRITICAL'
                  AND resolved = FALSE
            )
        """)

        breach_exists = bool(cur.fetchone()[0])

        return {
            "ledger_integrity": "BREACH" if breach_exists else "OK"
        }

    except Exception:
        # Do not convert an infrastructure failure into a
        # security breach signal.
        return {
            "ledger_integrity": "UNKNOWN"
        }

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# ------------------------------------------------------------
# 5. RESTRICTED SECURITY INCIDENTS (CHIEF ONLY)
# ------------------------------------------------------------
@router.get("/security-incidents")
def get_security_incidents(request: Request, current_user: dict = Depends(get_current_user)):
    # Restrict strictly to higher authority
    if current_user.get("role") != "The Chief":
        raise HTTPException(
            status_code=403, 
            detail="Access denied. Authorized executive clearance required."
        )

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute("""
            SELECT 
                id, 
                incident_type, 
                severity, 
                compromised_sequence_id, 
                detected_at, 
                details, 
                resolved
            FROM security_incidents
            ORDER BY detected_at DESC
        """)
        rows = cur.fetchall()

        # Format output
        incidents = []
        for r in rows:
            incidents.append({
                "id": r["id"],
                "incident_type": r["incident_type"],
                "severity": r["severity"],
                "compromised_node": r["compromised_sequence_id"],
                "detected_at": str(r["detected_at"]) if r["detected_at"] else "",
                "details": r["details"],
                "resolved": r["resolved"]
            })

        return {
            "total": len(incidents),
            "incidents": incidents
        }
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cur.close()
        conn.close()