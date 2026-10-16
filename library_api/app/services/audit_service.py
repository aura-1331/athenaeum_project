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
    """Serialize common database values into stable JSON-compatible values."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    return str(obj)


AUDIT_HASH_FIELDS = (
    "id",
    "session_id",
    "timestamp",
    "user_id",
    "username",
    "role",
    "designation",
    "machine_name",
    "ip_address",
    "category",
    "action_type",
    "target_entity",
    "target_id",
    "endpoint",
    "http_method",
    "justification",
    "diff_payload",
    "extra_metadata",
    "sequence_id",
)


def calculate_audit_hash(prev_hash: str, payload: dict) -> str:
    """Calculate SHA-256 over the persisted audit fields and predecessor hash."""
    canonical_payload = {
        "prev_hash": prev_hash,
        **{field: payload.get(field) for field in AUDIT_HASH_FIELDS},
    }
    canonical_repr = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
        default=_audit_json_default,
    )
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def calculate_legacy_audit_hash(prev_hash: str, payload: dict) -> str:
    """Reproduce the narrower hash format used by historical audit records."""
    canonical_payload = {
        "prev_hash": prev_hash,
        "user_id": str(payload.get("user_id") or ""),
        "username": str(payload.get("username") or ""),
        "role": str(payload.get("role") or ""),
        "action_type": str(payload.get("action_type") or ""),
        "target_entity": str(payload.get("target_entity") or ""),
        "target_id": str(payload.get("target_id") or ""),
        "justification": str(payload.get("justification") or ""),
        "diff_payload": payload.get("diff_payload") or {},
        "extra_metadata": payload.get("extra_metadata") or {},
    }
    canonical_repr = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
        default=_audit_json_default,
    )
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def verify_audit_ledger() -> dict[str, Any]:
    """Verify the linked hash chain and explicitly report unchained records.

    Rows with a NULL ``record_hash`` are not treated as cryptographically
    verified. They are reported as PARTIAL rather than silently omitted from
    an otherwise VALID result. Existing hashed legacy rows are still accepted
    when their historical hash format verifies successfully.
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Include un-hashed rows so that verification cannot report full validity
        # while silently ignoring audit records without a ledger hash.
        cur.execute("""
            SELECT
                sequence_id, id, session_id, "timestamp",
                user_id, username, role, designation,
                machine_name, ip_address, category, action_type,
                target_entity, target_id, endpoint, http_method,
                justification, diff_payload, extra_metadata,
                prev_hash, record_hash
            FROM audit_activities
            ORDER BY sequence_id ASC
        """)
        rows = cur.fetchall()

        if not rows:
            return {
                "status": "EMPTY",
                "inspected_count": 0,
                "total_record_count": 0,
                "unhashed_count": 0,
            }

        expected_prev_hash = GENESIS_HASH
        inspected_count = 0
        # Count every un-hashed row up front so an early integrity failure still
        # reports the complete number of records that were not hash-verified.
        unhashed_sequence_ids = [r[0] for r in rows if r[-1] is None]

        for r in rows:
            (
                seq_id,
                rec_id,
                session_id,
                timestamp,
                uid,
                uname,
                urole,
                designation,
                machine_name,
                ip_address,
                category,
                act_type,
                tent,
                tid,
                endpoint,
                http_method,
                just,
                diff,
                meta,
                p_hash,
                r_hash,
            ) = r

            if r_hash is None:
                continue

            inspected_count += 1

            if p_hash != expected_prev_hash:
                return {
                    "status": "COMPROMISED",
                    "reason": "PREV_HASH_MISMATCH",
                    "sequence_id": seq_id,
                    "record_id": rec_id,
                    "expected_prev_hash": expected_prev_hash,
                    "found_prev_hash": p_hash,
                    "inspected_count": inspected_count,
                    "total_record_count": len(rows),
                    "unhashed_count": len(unhashed_sequence_ids),
                }

            payload = {
                "id": rec_id,
                "session_id": session_id,
                "timestamp": timestamp,
                "user_id": uid,
                "username": uname,
                "role": urole,
                "designation": designation,
                "machine_name": machine_name,
                "ip_address": ip_address,
                "category": category,
                "action_type": act_type,
                "target_entity": tent,
                "target_id": tid,
                "endpoint": endpoint,
                "http_method": http_method,
                "justification": just,
                "diff_payload": diff,
                "extra_metadata": meta,
                "sequence_id": seq_id,
            }

            computed_hash = calculate_audit_hash(p_hash, payload)

            if computed_hash != r_hash:
                # Historical records used a narrower hash payload. Accept that
                # format only if its own calculation exactly matches stored data.
                legacy_hash = calculate_legacy_audit_hash(p_hash, payload)
                if legacy_hash != r_hash:
                    return {
                        "status": "COMPROMISED",
                        "reason": "PAYLOAD_TAMPERED",
                        "sequence_id": seq_id,
                        "record_id": rec_id,
                        "expected_hash": computed_hash,
                        "stored_hash": r_hash,
                        "inspected_count": inspected_count,
                        "total_record_count": len(rows),
                        "unhashed_count": len(unhashed_sequence_ids),
                    }

            expected_prev_hash = r_hash

        unhashed_count = len(unhashed_sequence_ids)
        result = {
            "status": "PARTIAL" if unhashed_count else "VALID",
            "inspected_count": inspected_count,
            "total_record_count": len(rows),
            "unhashed_count": unhashed_count,
            "latest_head_hash": expected_prev_hash if inspected_count else None,
        }

        if unhashed_count:
            result["reason"] = "UNHASHED_RECORDS_PRESENT"
            result["first_unhashed_sequence_id"] = unhashed_sequence_ids[0]

        return result

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
    conn: Optional[Any] = None,
) -> bool:
    """Write one chained audit record.

    If a connection is supplied, transaction ownership remains with the caller;
    the caller must commit on success or roll back on failure. With no supplied
    connection, this function owns and finalizes its transaction.
    """
    owns_connection = conn is None
    cur = None

    try:
        if owns_connection:
            conn = get_connection(request=request)

        cur = conn.cursor()

        # Resolve request/host details. Machine identity is server-recorded; a
        # client-supplied machine/device header is deliberately not trusted.
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
            if not resolved_machine:
                resolved_machine = "SERVER-RECORDED-CLIENT"

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

        # Serialize writers to prevent two transactions from appending to the
        # same predecessor and forking the chain.
        cur.execute("SELECT pg_advisory_xact_lock(7270011)")
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

        entry_id = str(uuid.uuid4())
        cur.execute("""
            SELECT nextval('audit_activities_sequence_id_seq'), NOW()
        """)
        sequence_id, timestamp = cur.fetchone()

        stored_user_id = str(user_id or "SYSTEM")
        stored_username = str(username or "SYSTEM")
        stored_role = str(role or "SYSTEM")
        stored_designation = str(designation or "SYSTEM")
        stored_action_type = str(action_type or "UNKNOWN")

        stored_diff_payload = diff_payload if diff_payload else None
        stored_extra_metadata = extra_metadata if extra_metadata else None

        payload_data = {
            "id": entry_id,
            "session_id": session_id,
            "timestamp": timestamp,
            "user_id": stored_user_id,
            "username": stored_username,
            "role": stored_role,
            "designation": stored_designation,
            "machine_name": resolved_machine,
            "ip_address": resolved_ip,
            "category": category,
            "action_type": stored_action_type,
            "target_entity": target_entity,
            "target_id": target_id,
            "endpoint": resolved_endpoint,
            "http_method": resolved_method,
            "justification": justification,
            "diff_payload": stored_diff_payload,
            "extra_metadata": stored_extra_metadata,
            "sequence_id": sequence_id,
        }

        current_hash = calculate_audit_hash(prev_hash, payload_data)

        cur.execute("""
            INSERT INTO audit_activities (
                id, session_id, timestamp, user_id, username, role,
                designation, machine_name, ip_address, category, action_type,
                target_entity, target_id, endpoint, http_method, justification,
                diff_payload, extra_metadata, sequence_id, prev_hash, record_hash
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
        """, (
            entry_id,
            session_id,
            timestamp,
            stored_user_id,
            stored_username,
            stored_role,
            stored_designation,
            resolved_machine,
            resolved_ip,
            category,
            stored_action_type,
            target_entity,
            target_id,
            resolved_endpoint,
            resolved_method,
            justification,
            json.dumps(stored_diff_payload, default=_audit_json_default)
                if stored_diff_payload is not None else None,
            json.dumps(stored_extra_metadata, default=_audit_json_default)
                if stored_extra_metadata is not None else None,
            sequence_id,
            prev_hash,
            current_hash,
        ))

        if owns_connection:
            conn.commit()

        return True

    except Exception as e:
        if owns_connection and conn:
            conn.rollback()
        print(f"[AUDIT FAILURE] Failed to write chained audit record: {e}")
        return False

    finally:
        if cur:
            cur.close()
        if owns_connection and conn:
            conn.close()
