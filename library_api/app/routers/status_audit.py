"""Status, session history, and audit-ledger verification routes."""

import json
import traceback
import uuid
from typing import Optional, Any

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_role
from app.database import get_connection
from app.routers.review_utils import _audit_ledger
from app.services.audit_service import verify_audit_ledger

router = APIRouter(prefix="/status_audit", tags=["Status & Auditing"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def format_duration(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return "< 1s"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if mins:
        parts.append(f"{mins}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _json_value(value: Any) -> Any:
    """Decode JSON strings returned by drivers/configurations that don't decode JSONB."""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def _require_chief(current_user: dict) -> None:
    if str(current_user.get("role") or "").strip().lower() != "the chief":
        raise HTTPException(status_code=403, detail="Chief access required.")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class LoginSessionPayload(BaseModel):
    """Legacy-compatible body shape; authenticated identity always comes from the token."""

    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    designation: Optional[str] = None
    machine_name: Optional[str] = None


class LogoutSessionPayload(BaseModel):
    """Only session_id and reason are used; identity fields are never trusted."""

    session_id: Optional[str] = None
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    reason: Optional[str] = "Operator initiated sign-out"


# ---------------------------------------------------------------------------
# 1. Audit activities / ledger view (Chief only)
# ---------------------------------------------------------------------------
@router.get(
    "/system-logs",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def get_system_logs(
    request: Request,
    actor_filter: Optional[str] = None,
    action_filter: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=1_000_000),
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        where_clauses = []
        params = []

        if actor_filter:
            where_clauses.append(
                '("username" ILIKE %s OR "user_id" ILIKE %s '
                'OR "target_id" ILIKE %s OR "justification" ILIKE %s)'
            )
            term = f"%{actor_filter}%"
            params.extend([term, term, term, term])

        if action_filter:
            where_clauses.append(
                '("action_type" ILIKE %s OR "category" ILIKE %s)'
            )
            term = f"%{action_filter}%"
            params.extend([term, term])

        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cur.execute(
            f"SELECT COUNT(*) AS count FROM audit_activities{where_sql}",
            tuple(params),
        )
        total_count = cur.fetchone()["count"]

        # Select only fields surfaced by this endpoint; avoid needlessly reading
        # any other columns from the audit table.
        cur.execute(
            f"""
            SELECT
                id, sequence_id, "timestamp", username, user_id, role,
                designation, action_type, target_id, target_entity,
                justification, ip_address, machine_name, diff_payload,
                category, endpoint, http_method, prev_hash, record_hash
            FROM audit_activities
            {where_sql}
            ORDER BY sequence_id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset]),
        )
        rows = cur.fetchall()

        items = []
        for row in rows:
            timestamp = row.get("timestamp")
            actor_name = row.get("username") or f"User #{row.get('user_id', 'SYS')}"
            justification = row.get("justification")
            action_type = row.get("action_type")
            items.append(
                {
                    "id": str(row.get("id") or ""),
                    "sequence_id": row.get("sequence_id"),
                    "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else (str(timestamp) if timestamp else ""),
                    "actor_username": actor_name,
                    "user_id": str(row.get("user_id") or "SYS"),
                    "actor_role": row.get("role") or "OPERATOR",
                    "designation": row.get("designation") or "Staff",
                    "action_type": action_type or "ACTION",
                    "target_id": str(row.get("target_id")) if row.get("target_id") is not None else None,
                    "target_entity": row.get("target_entity") or "GLOBAL",
                    "summary": justification or f"Action {action_type} recorded.",
                    "ip_address": row.get("ip_address") or "127.0.0.1",
                    "device_id": row.get("machine_name") or "TERMINAL-01",
                    "change_reason": justification or "Standard operational workflow.",
                    "detailed_diffs": _json_value(row.get("diff_payload")),
                    "category": row.get("category"),
                    "endpoint": row.get("endpoint"),
                    "http_method": row.get("http_method"),
                    "prev_hash": row.get("prev_hash"),
                    "record_hash": row.get("record_hash"),
                }
            )

        return {"total": total_count, "items": items}
    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to retrieve system audit logs.")
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# 2. Session lifecycle
# ---------------------------------------------------------------------------
@router.post("/session/login")
def login_session(
    payload: LoginSessionPayload,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    # Request-body identity fields are intentionally ignored. The authenticated
    # principal is the only source of actor identity in both session and audit rows.
    user_id = str(current_user.get("user_id") or "")
    username = str(current_user.get("username") or current_user.get("name") or "")
    role = str(current_user.get("role") or "")
    designation = str(current_user.get("designation") or role or "Staff")
    ip_address = request.client.host if request.client else "127.0.0.1"
    session_id = str(uuid.uuid4())

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            INSERT INTO user_sessions (
                id, user_id, username, role, designation, machine_name,
                ip_address, login_at, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), TRUE)
            RETURNING id, login_at
            """,
            (
                session_id,
                user_id,
                username,
                role,
                designation,
                "SERVER-RECORDED-CLIENT",
                ip_address,
            ),
        )
        row = cur.fetchone()

        _audit_ledger(
            request,
            current_user,
            conn,
            action_type="LOGIN",
            target_entity="GLOBAL",
            target_id=session_id,
            category="AUTH",
            justification="Secure login session opened.",
            diff={
                "session_id": session_id,
                "session_state": {"from": None, "to": "ACTIVE"},
            },
            extra={"session_id": session_id, "session_action": "LOGIN"},
            http_method="POST",
        )

        conn.commit()
        return {
            "status": "Session opened",
            "session_id": str(row["id"]),
            "user_id": user_id,
            "login_at": row["login_at"].isoformat() if row.get("login_at") else "",
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to open the session.")
    finally:
        cur.close()
        conn.close()


@router.post("/session/logout")
def logout_session(
    payload: LogoutSessionPayload,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user.get("user_id") or "")
    username = str(current_user.get("username") or current_user.get("name") or "")
    role = str(current_user.get("role") or "")
    designation = str(current_user.get("designation") or role or "Staff")
    reason = str(payload.reason or "Operator initiated sign-out").strip()

    if not reason:
        reason = "Operator initiated sign-out"
    if len(reason) > 2000:
        raise HTTPException(status_code=400, detail="Logout reason must not exceed 2000 characters.")

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        target_session_id = payload.session_id
        if target_session_id:
            try:
                target_session_id = str(uuid.UUID(str(target_session_id)))
            except (TypeError, ValueError, AttributeError):
                raise HTTPException(status_code=400, detail="Session ID must be a valid UUID.")

            cur.execute(
                """
                SELECT id FROM user_sessions
                WHERE id = %s AND user_id = %s AND is_active = TRUE
                FOR UPDATE
                """,
                (target_session_id, user_id),
            )
            if not cur.fetchone():
                raise HTTPException(
                    status_code=403,
                    detail="You may only close your own active session.",
                )
        else:
            cur.execute(
                """
                SELECT id FROM user_sessions
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY login_at DESC
                LIMIT 1
                FOR UPDATE
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                # Authentication can be restored without a corresponding
                # user_sessions row (for example after a server restart). Treat
                # logout as idempotent instead of returning a misleading 404.
                _audit_ledger(
                    request,
                    current_user,
                    conn,
                    action_type="LOGOUT_NO_ACTIVE_SESSION",
                    target_entity="GLOBAL",
                    target_id=f"user:{user_id}",
                    category="AUTH",
                    justification=reason,
                    diff={
                        "session_id": None,
                        "session_state": {"from": "NOT_ACTIVE", "to": "NOT_ACTIVE"},
                    },
                    extra={
                        "session_action": "LOGOUT_NO_ACTIVE_SESSION",
                        "session_found": False,
                    },
                    http_method="POST",
                )
                conn.commit()
                return {
                    "status": "No active session",
                    "session_id": None,
                    "session_closed": False,
                    "message": "No active server-side session was found; sign-out may continue.",
                }
            target_session_id = str(row["id"])

        cur.execute(
            """
            UPDATE user_sessions
            SET logout_at = NOW(),
                duration_seconds = GREATEST(1, EXTRACT(EPOCH FROM (NOW() - login_at))::INT),
                is_active = FALSE
            WHERE id = %s AND user_id = %s AND is_active = TRUE
            RETURNING duration_seconds
            """,
            (target_session_id, user_id),
        )
        updated_row = cur.fetchone()
        if not updated_row:
            raise HTTPException(status_code=409, detail="The session was already closed.")

        duration = int(updated_row.get("duration_seconds") or 0)
        formatted_time = format_duration(duration)

        _audit_ledger(
            request,
            current_user,
            conn,
            action_type="LOGOUT",
            target_entity="GLOBAL",
            target_id=target_session_id,
            category="AUTH",
            justification=reason,
            diff={
                "session_id": target_session_id,
                "session_state": {"from": "ACTIVE", "to": "CLOSED"},
                "duration_seconds": duration,
                "duration_formatted": formatted_time,
            },
            extra={"session_id": target_session_id, "session_action": "LOGOUT"},
            http_method="POST",
        )

        conn.commit()
        return {
            "status": "Session closed",
            "session_id": target_session_id,
            "duration_seconds": duration,
            "formatted_duration": formatted_time,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to close the session.")
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# 3. Session histories (Chief only)
# ---------------------------------------------------------------------------
@router.get(
    "/sessions",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def get_user_sessions(
    request: Request,
    user_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=1_000_000),
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        query = """
            SELECT id, user_id, username, role, designation, machine_name,
                   ip_address, login_at, logout_at, duration_seconds, is_active
            FROM user_sessions
        """
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
                "session_id": str(row["id"]),
                "user_id": str(row["user_id"]),
                "username": row["username"],
                "role": row["role"],
                "designation": row["designation"],
                "machine_name": row["machine_name"],
                "ip_address": row["ip_address"],
                "login_at": row["login_at"].isoformat() if row["login_at"] else "",
                "logout_at": row["logout_at"].isoformat() if row["logout_at"] else None,
                "duration_seconds": row["duration_seconds"],
                "status": "ACTIVE" if row["is_active"] else "COMPLETED",
            }
            for row in rows
        ]
    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to retrieve session history.")
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# 4. Cryptographic ledger verification (Chief only)
# ---------------------------------------------------------------------------
@router.get(
    "/ledger/verify",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def get_ledger_verification(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    _require_chief(current_user)
    result = verify_audit_ledger()
    status_value = str(result.get("status") or "UNKNOWN").upper()

    # PARTIAL means the ledger contains un-hashed rows, so full integrity cannot
    # be asserted. Record an incident for the first affected sequence without
    # writing to the possibly compromised audit chain itself.
    issue_statuses = {"TAMPERED", "COMPROMISED", "INVALID", "PARTIAL"}
    if status_value in issue_statuses:
        compromised_sequence = (
            result.get("sequence_id")
            or result.get("first_unhashed_sequence_id")
        )
        if compromised_sequence is None:
            compromised_sequence = result.get("record_id")

        reason = str(result.get("reason") or result.get("detail") or status_value)
        if status_value == "PARTIAL":
            reason_text = (
                f"Ledger verification is PARTIAL: {result.get('unhashed_count', 0)} "
                f"record(s) have no record hash. Reason: {reason}."
            )
        else:
            reason_text = f"Ledger integrity verification reported {status_value}: {reason}."

        conn = get_connection(request=request)
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT id FROM security_incidents
                WHERE compromised_sequence_id = %s AND resolved = FALSE
                LIMIT 1
                """,
                (compromised_sequence,),
            )
            existing = cur.fetchone()
            if not existing:
                cur.execute(
                    """
                    INSERT INTO security_incidents (
                        incident_type, severity, compromised_sequence_id,
                        details, resolved
                    )
                    VALUES ('CHAIN_INTEGRITY_BREACH', 'CRITICAL', %s, %s, FALSE)
                    """,
                    (compromised_sequence, reason_text),
                )
                conn.commit()
        except Exception:
            conn.rollback()
            print("[SECURITY ALERT ERROR] Could not record a ledger-integrity incident.")
            traceback.print_exc()
        finally:
            cur.close()
            conn.close()

    return result


# ---------------------------------------------------------------------------
# 5. Minimal global security status (public signal)
# ---------------------------------------------------------------------------
@router.get("/global-status")
def get_global_security_status(request: Request):
    """Return only the current unresolved critical ledger-incident signal."""
    conn = None
    cur = None
    try:
        conn = get_connection(request=request)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM security_incidents
                WHERE incident_type = 'CHAIN_INTEGRITY_BREACH'
                  AND severity = 'CRITICAL'
                  AND resolved = FALSE
            )
            """
        )
        breach_exists = bool(cur.fetchone()[0])
        return {"ledger_integrity": "BREACH" if breach_exists else "OK"}
    except Exception:
        # Distinguish an infrastructure failure from a known integrity issue.
        return {"ledger_integrity": "UNKNOWN"}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# 6. Restricted security incidents (Chief only)
# ---------------------------------------------------------------------------
@router.get(
    "/security-incidents",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def get_security_incidents(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    _require_chief(current_user)
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id, incident_type, severity, compromised_sequence_id,
                   detected_at, details, resolved
            FROM security_incidents
            ORDER BY detected_at DESC
            """
        )
        rows = cur.fetchall()
        incidents = [
            {
                "id": row["id"],
                "incident_type": row["incident_type"],
                "severity": row["severity"],
                "compromised_node": row["compromised_sequence_id"],
                "detected_at": row["detected_at"].isoformat() if row["detected_at"] else "",
                "details": row["details"],
                "resolved": row["resolved"],
            }
            for row in rows
        ]
        return {"total": len(incidents), "incidents": incidents}
    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to retrieve security incidents.")
    finally:
        cur.close()
        conn.close()
