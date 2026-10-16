from library_api.app.database import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("""
    SELECT pg_get_functiondef(p.oid)
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' AND p.proname = 'next_work_id'
""")
old = cur.fetchone()[0]
with open(r"backups\next_work_id_OLD.sql", "w", encoding="utf-8") as f:
    f.write(old + ";\n")
print("Old function saved.")

cur.execute("SELECT COALESCE(MAX(work_id), 0) FROM public.works")
in_works = cur.fetchone()[0]
cur.execute("""
    SELECT COALESCE(MAX(CASE WHEN target_id ~ '^[0-9]{1,9}$'
                             THEN target_id::bigint END), 0)
    FROM public.audit_activities
    WHERE upper(target_entity) = 'WORK'
""")
in_audit = cur.fetchone()[0]
start = max(in_works, in_audit, 1)
print("Highest number used so far:", start)

cur.execute("CREATE SEQUENCE public.work_id_never_reuse_seq")
cur.execute("SELECT setval('public.work_id_never_reuse_seq', %s, true)", (start,))

cur.execute("""
CREATE OR REPLACE FUNCTION public.next_work_id()
 RETURNS integer
 LANGUAGE plpgsql
AS $fn$
DECLARE
    candidate integer;
BEGIN
    LOOP
        candidate := nextval('public.work_id_never_reuse_seq');
        EXIT WHEN NOT EXISTS (
            SELECT 1 FROM public.works WHERE work_id = candidate
        );
    END LOOP;
    RETURN candidate;
END;
$fn$
""")

conn.commit()
cur.execute("SELECT last_value FROM public.work_id_never_reuse_seq")
print("New counter is at:", cur.fetchone()[0], "-> next new work will be", start + 1)
conn.close()
