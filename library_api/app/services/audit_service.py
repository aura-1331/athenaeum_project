# app/services/audit_service.py

import json
import socket
import uuid
import hashlib
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, Any
from fastapi import Request
from app.database import get_connection

GENESIS_HASH = "0" * 64


def _audit_json_default(obj: Any) -> Any:
    """Serializes Decimal, UUID, and date/time objects into JSON-compatible primitives."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    return str(obj)


def calculate_audit_hash(prev_hash: str, payload: dict) -> str:
    """
    Produces a deterministic SHA-256 digest over the previous hash
    and canonicalized audit record attributes.
    """
    canonical_repr = json.dumps(
        {
            "prev_hash": prev_hash,
            "user_id": str(payload.get("user_id") or ""),
            "username": str(payload.get("username") or ""),
            "role": str(payload.get("role") or ""),
            "action_type": str(payload.get("action_type") or ""),
            "target_entity": str(payload.get("target_entity") or ""),
            "target_id": str(payload.get("target_id") or ""),
            "justification": str(payload.get("justification") or ""),
            "diff_payload": payload.get("diff_payload") or {},
            "extra_metadata": payload.get("extra_metadata") or {}
        },
        sort_keys=True,
        separators=(',', ':'),
        default=_audit_json_default
    )
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def verify_audit_ledger() -> dict[str, Any]:
    """
    Traverses audit_activities sequentially.
    Returns validation status and pinpoints the first compromised sequence if invalid.
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT 
                sequence_id, id, user_id, username, role, action_type,
                target_entity, target_id, justification, diff_payload,
                extra_metadata, prev_hash, record_hash
            FROM audit_activities
            WHERE record_hash IS NOT NULL
            ORDER BY sequence_id ASC
        """)
        rows = cur.fetchall()

        if not rows:
            return {"status": "EMPTY", "inspected_count": 0}

        expected_prev_hash = GENESIS_HASH

        for r in rows:
            seq_id, rec_id, uid, uname, urole, act_type, tent, tid, just, diff, meta, p_hash, r_hash = r

            # Check 1: Chain link continuity
            if p_hash != expected_prev_hash:
                return {
                    "status": "COMPROMISED",
                    "reason": "PREV_HASH_MISMATCH",
                    "sequence_id": seq_id,
                    "record_id": rec_id,
                    "expected_prev_hash": expected_prev_hash,
                    "found_prev_hash": p_hash
                }

            # Check 2: Row payload integrity
            payload = {
                "user_id": uid,
                "username": uname,
                "role": urole,
                "action_type": act_type,
                "target_entity": tent,
                "target_id": tid,
                "justification": just,
                "diff_payload": diff if isinstance(diff, dict) else (json.loads(diff) if diff else {}),
                "extra_metadata": meta if isinstance(meta, dict) else (json.loads(meta) if meta else {})
            }
            computed_hash = calculate_audit_hash(p_hash, payload)

            if computed_hash != r_hash:
                return {
                    "status": "COMPROMISED",
                    "reason": "PAYLOAD_TAMPERED",
                    "sequence_id": seq_id,
                    "record_id": rec_id,
                    "expected_hash": computed_hash,
                    "stored_hash": r_hash
                }

            expected_prev_hash = r_hash

        return {
            "status": "VALID",
            "inspected_count": len(rows),
            "latest_head_hash": expected_prev_hash
        }

    finally:
        cur.close()
        conn.close()


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
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # 1. Resolve host and network metadata with unconditional fallbacks
        resolved_ip = ip_address
        resolved_endpoint = endpoint
        resolved_method = http_method
        resolved_machine = machine_name

        if request is not None:
            if not resolved_ip and getattr(request, "client", None):
                resolved_ip = request.client.host
            if not resolved_endpoint and getattr(request, "url", None):
                resolved_endpoint = request.url.path
            if not resolved_method and getattr(request, "method", None):
                resolved_method = request.method
            if not resolved_machine and getattr(request, "headers", None):
                resolved_machine = request.headers.get("X-Machine-Name")

        # Fallbacks to satisfy audit_activities NOT NULL constraints
        if not resolved_ip:
            resolved_ip = "127.0.0.1"

        if not resolved_machine:
            try:
                resolved_machine = socket.gethostname() or "LOCALHOST"
            except Exception:
                resolved_machine = "LOCALHOST"

        if not resolved_endpoint:
            resolved_endpoint = "/internal"

        if not resolved_method:
            resolved_method = "SYSTEM"

        # 2. Fetch latest record hash in sequence with row locking
        cur.execute("""
            SELECT record_hash 
            FROM audit_activities 
            WHERE record_hash IS NOT NULL 
            ORDER BY sequence_id DESC 
            LIMIT 1 
            FOR UPDATE
        """)
        row = cur.fetchone()
        prev_hash = row[0] if row and row[0] else GENESIS_HASH

        # 3. Compute deterministic hash for current record
        payload_data = {
            "user_id": str(user_id or "SYSTEM"),
            "username": str(username or "SYSTEM"),
            "role": str(role or "SYSTEM"),
            "action_type": str(action_type or "UNKNOWN"),
            "target_entity": str(target_entity or ""),
            "target_id": str(target_id or ""),
            "justification": str(justification or ""),
            "diff_payload": diff_payload or {},
            "extra_metadata": extra_metadata or {}
        }
        current_hash = calculate_audit_hash(prev_hash, payload_data)

        # 4. Insert record with chain linkages
        entry_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO audit_activities (
                id, session_id, timestamp, user_id, username, role,
                designation, machine_name, ip_address, category, action_type,
                target_entity, target_id, endpoint, http_method, justification,
                diff_payload, extra_metadata, prev_hash, record_hash
            )
            VALUES (
                %s, %s, NOW(), %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """, (
            entry_id,
            session_id,
            str(user_id or "SYSTEM"),
            str(username or "SYSTEM"),
            str(role or "SYSTEM"),
            str(designation or "SYSTEM"),
            resolved_machine,
            resolved_ip,
            category,
            action_type,
            target_entity,
            target_id,
            resolved_endpoint,
            resolved_method,
            justification,
            json.dumps(diff_payload, default=_audit_json_default) if diff_payload else None,
            json.dumps(extra_metadata, default=_audit_json_default) if extra_metadata else None,
            prev_hash,
            current_hash
        ))

        conn.commit()
        return True

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[AUDIT FAILURE] Failed to write chained audit record: {e}")
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()