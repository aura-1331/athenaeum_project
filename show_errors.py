import sys
from library_api.app.database import get_connection

conn = get_connection()
cur = conn.cursor()

if len(sys.argv) > 1:
    ref = sys.argv[1].strip()
    cur.execute("""
        SELECT error_reference, occurred_at, role, endpoint, http_method,
               status_code, failed_stage, error_type, error_message, traceback
        FROM public.application_error_log
        WHERE error_reference = %s
    """, (ref,))
    row = cur.fetchone()
    if not row:
        print("No error found with reference", ref)
    else:
        labels = ["Reference", "When", "Role", "Endpoint", "Method",
                  "Status", "Stage", "Type", "Message", "Traceback"]
        for label, value in zip(labels, row):
            print(f"{label}: {value}")
else:
    cur.execute("""
        SELECT error_reference, occurred_at, status_code, endpoint, error_type
        FROM public.application_error_log
        ORDER BY occurred_at DESC LIMIT 15
    """)
    for r in cur.fetchall():
        print(r)

conn.close()
