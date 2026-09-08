import json
import socket
import uuid
from typing import Optional, Any
from fastapi import Request
from app.database import get_connection


def log_audit_activity(
    request: Optional[Request] = None,
    *,
    user_id: str = "SYSTEM",
    username: str = "SYSTEM",
    role: str = "SYSTEM",
    designation: str = "SYSTEM",
    category: str = "GENERAL",
    action_type: str = "UNKNOWN",
    target_entity: Optional[str] = None,
    target_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    http_method: Optional[str] = None,
    justification: Optional[str] = None,
    diff_payload: Optional[dict[str, Any]] = None,
    extra_metadata: Optional[dict[str, Any]] = None,
    session_id: Optional[str] = None,
    machine_name: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    """
    Inserts an immutable audit record into audit_activities using raw psycopg2.
    Safe against exceptions so audit failures never crash the primary application flow.
    """
    conn = None
    cur = None
    try:
        # Extract network details from request if not explicitly provided
        if request is not None:
            if not ip_address:
                ip_address = request.client.host if request.client else "127.0.0.1"
            if not endpoint:
                endpoint = request.url.path
            if not http_method:
                http_method = request.method
            if not machine_name:
                machine_name = request.headers.get("X-Machine-Name") or socket.gethostname()
        else:
            ip_address = ip_address or "127.0.0.1"
            machine_name = machine_name or socket.gethostname()

        conn = get_connection(request=request, username=username, role=role)
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO audit_activities (
                id,
                session_id,
                timestamp,
                user_id,
                username,
                role,
                designation,
                machine_name,
                ip_address,
                category,
                action_type,
                target_entity,
                target_id,
                endpoint,
                http_method,
                justification,
                diff_payload,
                extra_metadata
            ) VALUES (
                %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            );
            """,
            (
                str(uuid.uuid4()),
                session_id,
                str(user_id),
                username,
                role,
                designation,
                machine_name,
                ip_address,
                category,
                action_type,
                target_entity,
                str(target_id) if target_id else None,
                endpoint,
                http_method,
                justification or "Standard Archival Operation",
                json.dumps(diff_payload) if diff_payload else None,
                json.dumps(extra_metadata) if extra_metadata else None,
            ),
        )
        conn.commit()
        return True

    except Exception as exc:
        if conn:
            conn.rollback()
        print(f"[CRITICAL] Audit activity insert failed: {exc}")
        return False

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()