"""Status, session history, and audit-ledger verification routes."""

import json
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from pydantic import BaseModel
from app.services.audit_service import log_audit_activity

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query, Request

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


def _serialize_audit_row(row: dict) -> dict:
    """Serialize an original audit record without modifying its stored values."""

    timestamp = row.get("timestamp")
    diff_payload = _json_value(row.get("diff_payload"))
    extra_metadata = _json_value(row.get("extra_metadata"))

    if diff_payload is None:
        diff_payload = {}
    if extra_metadata is None:
        extra_metadata = {}

    outcome = None

    if isinstance(diff_payload, dict):
        outcome = diff_payload.get("outcome")

    if not outcome and isinstance(extra_metadata, dict):
        outcome = extra_metadata.get("status")

    action_type = row.get("action_type") or "ACTION"
    raw_user_id = row.get("user_id")

    return {
        "id": str(row.get("id") or ""),
        "sequence_id": row.get("sequence_id"),
        "timestamp": (
            timestamp.isoformat()
            if hasattr(timestamp, "isoformat")
            else str(timestamp or "")
        ),
        "actor_username": (
            row.get("username")
            or f"User #{raw_user_id or 'SYS'}"
        ),
        "user_id": str(raw_user_id or "SYS"),
        "group_user_id": (
            str(raw_user_id) if raw_user_id is not None else None
        ),
        "actor_role": row.get("role") or "OPERATOR",
        "designation": row.get("designation") or "Staff",
        "action_type": action_type,
        "target_id": (
            str(row.get("target_id"))
            if row.get("target_id") is not None
            else None
        ),
        "target_entity": row.get("target_entity") or "GLOBAL",
        "summary": (
            row.get("justification")
            or f"Action {action_type} recorded."
        ),
        "ip_address": row.get("ip_address"),
        "device_id": row.get("machine_name"),
        "change_reason": row.get("justification"),
        "detailed_diffs": diff_payload,
        "extra_metadata": extra_metadata,
        "outcome": str(outcome).upper() if outcome else "UNKNOWN",
        "status_code": (
            extra_metadata.get("status_code")
            if isinstance(extra_metadata, dict)
            else None
        ),
        "error_type": (
            extra_metadata.get("error_type")
            if isinstance(extra_metadata, dict)
            else None
        ),
        "category": row.get("category"),
        "endpoint": row.get("endpoint"),
        "http_method": row.get("http_method"),
        "prev_hash": row.get("prev_hash"),
        "record_hash": row.get("record_hash"),
    }


def _audit_select_sql() -> str:
    """Common column list used by the audit-list and group-detail endpoints."""
    return """
        SELECT
            id,
            sequence_id,
            "timestamp",
            username,
            user_id,
            role,
            designation,
            action_type,
            target_id,
            target_entity,
            justification,
            ip_address,
            machine_name,
            diff_payload,
            extra_metadata,
            category,
            endpoint,
            http_method,
            prev_hash,
            record_hash
        FROM audit_activities
    """


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class LoginSessionPayload(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    designation: Optional[str] = None
    machine_name: Optional[str] = None


class LogoutSessionPayload(BaseModel):
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
    category_filter: Optional[str] = None,
    outcome_filter: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=1_000_000),
):
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        where_clauses = []
        params = []

        if actor_filter and actor_filter.strip():
            term = f"%{actor_filter.strip()}%"
            where_clauses.append(
                """(
                    username ILIKE %s
                    OR user_id ILIKE %s
                    OR target_id ILIKE %s
                    OR justification ILIKE %s
                )"""
            )
            params.extend([term] * 4)

        if search and search.strip():
            term = f"%{search.strip()}%"
            where_clauses.append(
                """(
                    username ILIKE %s
                    OR user_id ILIKE %s
                    OR action_type ILIKE %s
                    OR category ILIKE %s
                    OR target_id ILIKE %s
                    OR target_entity ILIKE %s
                    OR justification ILIKE %s
                    OR endpoint ILIKE %s
                    OR http_method ILIKE %s
                    OR CAST(sequence_id AS TEXT) ILIKE %s
                    OR CAST(diff_payload AS TEXT) ILIKE %s
                    OR CAST(extra_metadata AS TEXT) ILIKE %s
                )"""
            )
            params.extend([term] * 12)

        if action_filter and action_filter.strip():
            where_clauses.append("action_type ILIKE %s")
            params.append(f"%{action_filter.strip()}%")

        if category_filter and category_filter.strip():
            where_clauses.append("category ILIKE %s")
            params.append(f"%{category_filter.strip()}%")

        if outcome_filter and outcome_filter.strip():
            normalized_outcome = outcome_filter.strip().upper()

            if normalized_outcome not in {"SUCCESS", "FAILED", "UNKNOWN"}:
                raise HTTPException(
                    status_code=400,
                    detail="outcome_filter must be SUCCESS, FAILED, or UNKNOWN.",
                )

            outcome_expression = """
                UPPER(COALESCE(
                    diff_payload->>'outcome',
                    extra_metadata->>'status',
                    ''
                ))
            """

            if normalized_outcome == "UNKNOWN":
                where_clauses.append(
                    f"({outcome_expression}) NOT IN ('SUCCESS', 'FAILED')"
                )
            else:
                where_clauses.append(f"({outcome_expression}) = %s")
                params.append(normalized_outcome)

        where_sql = (
            f" WHERE {' AND '.join(where_clauses)}"
            if where_clauses
            else ""
        )

        cur.execute(
            _audit_select_sql()
            + where_sql
            + ' ORDER BY "timestamp" DESC NULLS LAST, sequence_id DESC',
            tuple(params),
        )

        rows = cur.fetchall()
        original_events = [_serialize_audit_row(row) for row in rows]

        display_rows = []
        grouped = {}

        for event in original_events:
            is_successful_refresh = (
                event["action_type"].upper() == "TOKEN_REFRESH"
                and event["outcome"] == "SUCCESS"
                and bool(event["timestamp"])
            )

            if not is_successful_refresh:
                event["display_type"] = "event"
                display_rows.append(event)
                continue

            try:
                event_time = datetime.fromisoformat(
                    event["timestamp"].replace("Z", "+00:00")
                )
                bucket_epoch = int(event_time.timestamp()) // 900 * 900
                bucket_start = datetime.fromtimestamp(
                    bucket_epoch,
                    tz=event_time.tzinfo,
                )
                bucket_end = bucket_start + timedelta(minutes=15)
            except (ValueError, TypeError, OverflowError, OSError):
                event["display_type"] = "event"
                display_rows.append(event)
                continue

            raw_user_id = event["group_user_id"]
            endpoint = event["endpoint"] or ""

            group_key = (
                bucket_start.isoformat(),
                raw_user_id,
                endpoint,
            )

            if group_key not in grouped:
                grouped[group_key] = {
                    "id": (
                        f"refresh-group:{bucket_start.isoformat()}:"
                        f"{raw_user_id or 'NULL'}:{endpoint}"
                    ),
                    "display_type": "group",
                    "action_type": "TOKEN_REFRESH",
                    "category": event["category"],
                    "actor_username": event["actor_username"],
                    "user_id": event["user_id"],
                    "group_user_id": raw_user_id,
                    "actor_role": event["actor_role"],
                    "designation": event["designation"],
                    "endpoint": event["endpoint"],
                    "http_method": event["http_method"],
                    "outcome": "SUCCESS",
                    "event_count": 0,
                    "first_timestamp": event["timestamp"],
                    "last_timestamp": event["timestamp"],
                    "first_sequence_id": event["sequence_id"],
                    "last_sequence_id": event["sequence_id"],
                    "group_start": bucket_start.isoformat(),
                    "group_end": bucket_end.isoformat(),
                    "ip_address": None,
                    "device_id": None,
                    "summary": (
                        "Grouped successful token refreshes. "
                        "Expand to inspect the original audit events."
                    ),
                }

            group = grouped[group_key]
            group["event_count"] += 1

            if event["timestamp"] < group["first_timestamp"]:
                group["first_timestamp"] = event["timestamp"]
                group["first_sequence_id"] = event["sequence_id"]

            if event["timestamp"] > group["last_timestamp"]:
                group["last_timestamp"] = event["timestamp"]
                group["last_sequence_id"] = event["sequence_id"]

        display_rows.extend(grouped.values())

        display_rows.sort(
            key=lambda item: (
                item.get("last_timestamp")
                or item.get("timestamp")
                or ""
            ),
            reverse=True,
        )

        display_total = len(display_rows)
        page_items = display_rows[offset:offset + limit]

        return {
            "total": display_total,
            "total_events": len(original_events),
            "items": page_items,
        }

    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve system audit logs.",
        )
    finally:
        cur.close()
        conn.close()


@router.get(
    "/system-logs/group-events",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def get_refresh_group_events(
    request: Request,
    group_start: str,
    group_user_id: Optional[str] = None,
    endpoint: Optional[str] = None,
):
    try:
        start = datetime.fromisoformat(
            group_start.replace("Z", "+00:00")
        )
        end = start + timedelta(minutes=15)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid group_start timestamp.",
        )

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        clauses = [
            '"timestamp" >= %s',
            '"timestamp" < %s',
            "action_type = 'TOKEN_REFRESH'",
            """UPPER(COALESCE(
                diff_payload->>'outcome',
                extra_metadata->>'status',
                ''
            )) = 'SUCCESS'""",
        ]
        params = [start, end]

        if group_user_id is None:
            clauses.append("user_id IS NULL")
        else:
            clauses.append("user_id = %s")
            params.append(group_user_id)

        if endpoint:
            clauses.append("endpoint = %s")
            params.append(endpoint)

        cur.execute(
            _audit_select_sql()
            + " WHERE "
            + " AND ".join(clauses)
            + " ORDER BY sequence_id DESC",
            tuple(params),
        )

        events = [_serialize_audit_row(row) for row in cur.fetchall()]

        return {
            "total": len(events),
            "items": events,
        }

    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve grouped audit events.",
        )
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
    user_id = str(current_user.get("user_id") or "")
    username = str(
        current_user.get("username") or current_user.get("name") or ""
    )
    role = str(current_user.get("role") or "")
    designation = str(current_user.get("designation") or role or "Staff")
    ip_address = request.client.host if request.client else None
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
            "login_at": (
                row["login_at"].isoformat()
                if row.get("login_at")
                else ""
            ),
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Unable to open the session.",
        )
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
    reason = str(payload.reason or "Operator initiated sign-out").strip()

    if not reason:
        reason = "Operator initiated sign-out"

    if len(reason) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Logout reason must not exceed 2000 characters.",
        )

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        target_session_id = payload.session_id

        if target_session_id:
            try:
                target_session_id = str(uuid.UUID(str(target_session_id)))
            except (TypeError, ValueError, AttributeError):
                raise HTTPException(
                    status_code=400,
                    detail="Session ID must be a valid UUID.",
                )

            cur.execute(
                """
                SELECT id
                FROM user_sessions
                WHERE id = %s
                  AND user_id = %s
                  AND is_active = TRUE
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
                SELECT id
                FROM user_sessions
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY login_at DESC
                LIMIT 1
                FOR UPDATE
                """,
                (user_id,),
            )
            row = cur.fetchone()

            if not row:
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
                        "session_state": {
                            "from": "NOT_ACTIVE",
                            "to": "NOT_ACTIVE",
                        },
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
                    "message": (
                        "No active server-side session was found; "
                        "sign-out may continue."
                    ),
                }

            target_session_id = str(row["id"])

        cur.execute(
            """
            UPDATE user_sessions
            SET logout_at = NOW(),
                duration_seconds = GREATEST(
                    1,
                    EXTRACT(EPOCH FROM (NOW() - login_at))::INT
                ),
                is_active = FALSE
            WHERE id = %s
              AND user_id = %s
              AND is_active = TRUE
            RETURNING duration_seconds
            """,
            (target_session_id, user_id),
        )

        updated_row = cur.fetchone()

        if not updated_row:
            raise HTTPException(
                status_code=409,
                detail="The session was already closed.",
            )

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
            extra={
                "session_id": target_session_id,
                "session_action": "LOGOUT",
            },
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
        raise HTTPException(
            status_code=500,
            detail="Unable to close the session.",
        )
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
            SELECT
                id, user_id, username, role, designation, machine_name,
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
                "login_at": (
                    row["login_at"].isoformat()
                    if row["login_at"]
                    else ""
                ),
                "logout_at": (
                    row["logout_at"].isoformat()
                    if row["logout_at"]
                    else None
                ),
                "duration_seconds": row["duration_seconds"],
                "status": (
                    "ACTIVE" if row["is_active"] else "COMPLETED"
                ),
            }
            for row in rows
        ]

    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve session history.",
        )
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

    issue_statuses = {"TAMPERED", "COMPROMISED", "INVALID", "PARTIAL"}

    if status_value in issue_statuses:
        compromised_sequence = (
            result.get("sequence_id")
            or result.get("first_unhashed_sequence_id")
        )

        if compromised_sequence is None:
            compromised_sequence = result.get("record_id")

        reason = str(
            result.get("reason") or result.get("detail") or status_value
        )

        if status_value == "PARTIAL":
            reason_text = (
                f"Ledger verification is PARTIAL: "
                f"{result.get('unhashed_count', 0)} record(s) "
                f"have no record hash. Reason: {reason}."
            )
        else:
            reason_text = (
                f"Ledger integrity verification reported "
                f"{status_value}: {reason}."
            )

        conn = get_connection(request=request)
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT id
                FROM security_incidents
                WHERE compromised_sequence_id = %s
                  AND resolved = FALSE
                LIMIT 1
                """,
                (compromised_sequence,),
            )
            existing = cur.fetchone()

            if not existing:
                cur.execute(
                    """
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
                    """,
                    (compromised_sequence, reason_text),
                )
                conn.commit()

        except Exception:
            conn.rollback()
            print(
                "[SECURITY ALERT ERROR] Could not record "
                "a ledger-integrity incident."
            )
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

        return {
            "ledger_integrity": (
                "BREACH" if breach_exists else "OK"
            )
        }

    except Exception:
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
            SELECT
                id, incident_type, severity, compromised_sequence_id,
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
                "detected_at": (
                    row["detected_at"].isoformat()
                    if row["detected_at"]
                    else ""
                ),
                "details": row["details"],
                "resolved": row["resolved"],
            }
            for row in rows
        ]

        return {
            "total": len(incidents),
            "incidents": incidents,
        }

    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve security incidents.",
        )
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# 7. Forensic Print Audit Dossier
# ---------------------------------------------------------------------------

class ForensicPrintAuditRequest(BaseModel):
    serial_no: int
    item_id: Optional[int] = None
    accession_no: Optional[str] = None
    client_checksum: str
    dossier_type: str

    # Deep Hardware Telemetry
    machine_uuid: str
    hardware_bios_uuid: Optional[str] = None
    mac_address: Optional[str] = None
    os_username: Optional[str] = None
    platform: Optional[str] = None

    # Print Subsystem & Driver Metadata
    printer_name: Optional[str] = None
    printer_driver: Optional[str] = None
    spooler_job_id: Optional[str] = None
    media_size: Optional[str] = "A4 (210x297mm)"
    dpi_resolution: Optional[str] = "600 DPI"

    # Network, Station & Session Context
    station_ip: Optional[str] = None
    geo_station: Optional[str] = None
    parent_session_id: Optional[str] = None

    # Operational Status
    print_status: Optional[str] = "INITIATED"
    cancellation_reason: Optional[str] = None


@router.post("/log-print")
def record_forensic_print_dossier(
    payload: ForensicPrintAuditRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Appends full hardware, print driver, and institutional audit telemetry 
    directly to the hash-chained audit_activities ledger.
    """
    user_id = str(current_user.get("user_id") or "SYS")
    username = str(current_user.get("username") or current_user.get("name") or "Operator")
    role = str(current_user.get("role") or "OPERATOR")
    designation = str(current_user.get("designation") or role)

    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        status_outcome = (payload.print_status or "INITIATED").strip().upper()
        allowed_statuses = {"INITIATED", "SUCCESS", "CANCELLED", "VOIDED"}
        if status_outcome not in allowed_statuses:
            raise HTTPException(
                status_code=422,
                detail="print_status must be INITIATED, SUCCESS, CANCELLED, or VOIDED.",
            )

        # -------------------------------------------------------------------
        # Resolve Valid Foreign-Key Session ID
        # -------------------------------------------------------------------
        valid_session_id: Optional[str] = None
        candidate_session = payload.parent_session_id

        if candidate_session and candidate_session.strip():
            cur.execute(
                "SELECT id FROM user_sessions WHERE id = %s LIMIT 1",
                (candidate_session.strip(),)
            )
            found = cur.fetchone()
            if found:
                valid_session_id = str(found["id"])

        # Fallback: if not found by payload, resolve active session for this user
        if not valid_session_id and user_id and user_id != "SYS":
            cur.execute(
                """
                SELECT id FROM user_sessions 
                WHERE user_id = %s AND is_active = TRUE 
                ORDER BY login_at DESC LIMIT 1
                """,
                (user_id,)
            )
            found = cur.fetchone()
            if found:
                valid_session_id = str(found["id"])

        # Count verified successful prints to establish official run sequence
        cur.execute(
            """
            SELECT COUNT(*) AS total_prints
            FROM audit_activities
            WHERE category = 'PRINT'
              AND action_type = 'DOSSIER_PRINT'
              AND target_id = %s
              AND COALESCE(diff_payload->>'outcome', 'SUCCESS') = 'SUCCESS'
            """,
            (str(payload.serial_no),),
        )
        row = cur.fetchone()
        successful_previous_runs = row["total_prints"] if row else 0

        if status_outcome == "SUCCESS":
            current_run = successful_previous_runs + 1
            is_first_print = (current_run == 1)
            dossier_label = (
                "ORIGINAL ACCESSION DOCKET" 
                if is_first_print 
                else f"REPRINT DUPLICATE (#{current_run})"
            )
            justification = f"Official dossier printed ({dossier_label})"
        else:
            current_run = successful_previous_runs
            is_first_print = False
            dossier_label = f"PRINT {status_outcome}"
            justification = f"Print attempt {status_outcome.lower()}: {payload.cancellation_reason or 'Aborted by operator'}"

        forensic_metadata: Dict[str, Any] = {
            "client_checksum": payload.client_checksum,
            "status": status_outcome,
            "dossier_type": dossier_label,
            "hardware": {
                "machine_uuid": payload.machine_uuid,
                "bios_uuid": payload.hardware_bios_uuid,
                "mac_address": payload.mac_address,
                "os_username": payload.os_username,
                "platform": payload.platform,
            },
            "subsystem": {
                "printer_name": payload.printer_name,
                "printer_driver": payload.printer_driver,
                "spooler_job_id": payload.spooler_job_id,
                "media_size": payload.media_size,
                "resolution": payload.dpi_resolution,
            },
            "network": {
                "station_ip": payload.station_ip,
                "geo_station": payload.geo_station,
            },
            "parent_session_id": valid_session_id,
        }

        diff_payload = {
            "serial_no": payload.serial_no,
            "item_id": payload.item_id,
            "accession_no": payload.accession_no,
            "print_run": current_run,
            "outcome": status_outcome,
        }

        logged = log_audit_activity(
            request=request,
            user_id=user_id,
            username=username,
            role=role,
            designation=designation,
            category="PRINT",
            action_type="DOSSIER_PRINT" if status_outcome == "SUCCESS" else "DOSSIER_PRINT_ATTEMPT",
            target_entity="ITEM",
            target_id=str(payload.serial_no),
            endpoint=request.url.path,
            http_method="POST",
            justification=justification,
            diff_payload=diff_payload,
            extra_metadata=forensic_metadata,
            session_id=valid_session_id,
            conn=conn,
        )

        if not logged:
            conn.rollback()
            raise HTTPException(status_code=500, detail="Failed to seal print audit ledger.")

        conn.commit()

        return {
            "status": "RECORDED",
            "print_run": f"#{current_run}",
            "is_first_print": is_first_print,
            "dossier_type": dossier_label,
            "outcome": status_outcome,
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Audit ledger write failure.")
    finally:
        cur.close()
        conn.close()


@router.get("/print-history")
def get_print_history(
    request: Request,
    serial_no: int = Query(..., ge=1),
    current_user: dict = Depends(get_current_user),
):
    """Return print audit entries for this item, scoped to the signed-in user."""
    user_id = str(current_user.get("user_id") or "")
    conn = get_connection(request=request)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id, sequence_id, "timestamp", justification,
                   diff_payload, extra_metadata
            FROM audit_activities
            WHERE category = 'PRINT'
              AND target_id = %s
              AND user_id = %s
            ORDER BY "timestamp" DESC NULLS LAST, sequence_id DESC
            LIMIT 50
            """,
            (str(serial_no), user_id),
        )
        items = []
        for row in cur.fetchall():
            diff = _json_value(row.get("diff_payload")) or {}
            extra = _json_value(row.get("extra_metadata")) or {}
            items.append({
                "id": str(row.get("id") or row.get("sequence_id") or ""),
                "timestamp": row["timestamp"].isoformat() if row.get("timestamp") else "",
                "outcome": str(diff.get("outcome") or extra.get("status") or "UNKNOWN").upper(),
                "summary": row.get("justification") or "Print activity recorded.",
            })
        return {"total": len(items), "items": items}
    except Exception:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to retrieve print history.")
    finally:
        cur.close()
        conn.close()