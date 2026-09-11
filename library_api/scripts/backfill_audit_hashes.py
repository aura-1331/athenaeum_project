import hashlib
import json
import psycopg2.extras
from app.database import get_connection
from app.services.audit_service import GENESIS_HASH, calculate_audit_hash, verify_audit_ledger


def normalize_json_field(val):
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {}
    if isinstance(val, dict):
        return val
    return {}


def backfill_audit_chain():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # 1. Fetch all audit rows ordered strictly by chronological occurrence
        cur.execute("""
            SELECT 
                id,
                user_id,
                username,
                role,
                action_type,
                target_entity,
                target_id,
                justification,
                diff_payload,
                extra_metadata
            FROM audit_activities
            ORDER BY "timestamp" ASC, id ASC
        """)
        records = cur.fetchall()

        total = len(records)
        if total == 0:
            print("No records found in audit_activities to backfill.")
            return

        print(f"Found {total} records. Generating sequential hashes...")

        current_prev_hash = GENESIS_HASH
        update_data = []

        # 2. Iterate chronologically and compute chained hashes
        for seq_id, r in enumerate(records, start=1):
            diff_dict = normalize_json_field(r.get("diff_payload"))
            extra_dict = normalize_json_field(r.get("extra_metadata"))

            payload_data = {
                "user_id": r.get("user_id"),
                "username": r.get("username"),
                "role": r.get("role"),
                "action_type": r.get("action_type"),
                "target_entity": r.get("target_entity"),
                "target_id": r.get("target_id"),
                "justification": r.get("justification"),
                "diff_payload": diff_dict,
                "extra_metadata": extra_dict
            }

            rec_hash = calculate_audit_hash(current_prev_hash, payload_data)
            update_data.append((seq_id, current_prev_hash, rec_hash, r["id"]))
            current_prev_hash = rec_hash

        # 3. Batch update records with new sequence_id, prev_hash, and record_hash
        print("Writing updated hashes to PostgreSQL...")
        psycopg2.extras.execute_batch(
            cur,
            """
            UPDATE audit_activities
            SET sequence_id = %s,
                prev_hash = %s,
                record_hash = %s
            WHERE id = %s
            """,
            update_data,
            page_size=200
        )

        # 4. Synchronize PostgreSQL autoincrement sequence with the highest sequence_id
        cur.execute("""
            SELECT setval(
                pg_get_serial_sequence('audit_activities', 'sequence_id'),
                COALESCE(MAX(sequence_id), 1),
                true
            )
            FROM audit_activities;
        """)

        conn.commit()
        print(f"Successfully backfilled {total} records.")

        # 5. Execute automated ledger validation
        print("Validating ledger integrity...")
        audit_status = verify_audit_ledger()
        print(f"Ledger Verification Status: {audit_status.get('status')}")
        print(f"Inspected Records: {audit_status.get('inspected_count')}")
        print(f"Latest Chain Head Hash: {audit_status.get('latest_head_hash')}")

    except Exception as e:
        conn.rollback()
        print(f"Backfill failed: {e}")
        raise e
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    backfill_audit_chain()