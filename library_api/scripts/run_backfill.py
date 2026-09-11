import json
import psycopg2.extras
from app.database import get_connection
from app.services.audit_service import GENESIS_HASH, calculate_audit_hash, verify_audit_ledger

conn = get_connection()
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

try:
    # 1. Temporarily disable trigger for maintenance
    cur.execute("ALTER TABLE audit_activities DISABLE TRIGGER USER;")

    # 2. Fetch all rows ordered chronologically
    cur.execute("""
        SELECT id, user_id, username, role, action_type, target_entity, target_id, 
               justification, diff_payload, extra_metadata 
        FROM audit_activities 
        ORDER BY "timestamp" ASC, id ASC
    """)
    records = cur.fetchall()
    print(f"Backfilling {len(records)} records...")

    current_prev_hash = GENESIS_HASH
    update_data = []

    for seq_id, r in enumerate(records, start=1):
        diff = r['diff_payload'] if isinstance(r['diff_payload'], dict) else (json.loads(r['diff_payload']) if r['diff_payload'] else {})
        meta = r['extra_metadata'] if isinstance(r['extra_metadata'], dict) else (json.loads(r['extra_metadata']) if r['extra_metadata'] else {})

        payload = {
            'user_id': r['user_id'],
            'username': r['username'],
            'role': r['role'],
            'action_type': r['action_type'],
            'target_entity': r['target_entity'],
            'target_id': r['target_id'],
            'justification': r['justification'],
            'diff_payload': diff,
            'extra_metadata': meta
        }

        rec_hash = calculate_audit_hash(current_prev_hash, payload)
        update_data.append((seq_id, current_prev_hash, rec_hash, r['id']))
        current_prev_hash = rec_hash

    # 3. Apply sequence IDs and hashes
    psycopg2.extras.execute_batch(
        cur,
        "UPDATE audit_activities SET sequence_id = %s, prev_hash = %s, record_hash = %s WHERE id = %s",
        update_data,
        page_size=200
    )

    # 4. Synchronize sequence generator
    cur.execute("""
        SELECT setval(
            pg_get_serial_sequence('audit_activities', 'sequence_id'), 
            COALESCE(MAX(sequence_id), 1), 
            true
        ) 
        FROM audit_activities;
    """)

    conn.commit()
    print("Backfill committed successfully.")

finally:
    cur.execute("ALTER TABLE audit_activities ENABLE TRIGGER USER;")
    conn.commit()
    cur.close()
    conn.close()

print("Verification Result:", verify_audit_ledger())
