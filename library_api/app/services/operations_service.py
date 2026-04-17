# app/services/operations_service.py

from psycopg2.extras import RealDictCursor


ALLOWED_ACTIONS = {
    "ISSUE",
    "RETURN",
    "LOST",
    "DAMAGED",
    "OVERRIDE",
}


def execute_operation(db, accession_no: str, action: str, actor: str, notes: str = ""):
    """
    Enterprise Operations Executor

    Flow (LOCKED):
    1. Validate accession exists
    2. Read current status
    3. Execute DB status transition procedure
    4. Insert audit log
    5. Return new state
    """

    if action not in ALLOWED_ACTIONS:
        raise Exception("Invalid operation action")

    with db.cursor(cursor_factory=RealDictCursor) as cur:

        # 1️⃣ Validate accession exists + get current status
        cur.execute(
            """
            SELECT accession_no, status
            FROM catalogue
            WHERE accession_no = %s
            """,
            (accession_no,),
        )
        row = cur.fetchone()

        if not row:
            raise Exception("Accession not found")

        old_status = row["status"]

        # 2️⃣ Execute status transition procedure
        # IMPORTANT:
        # Replace 'sp_execute_status_transition'
        # with your ACTUAL stored procedure name.
        cur.execute(
            """
            SELECT *
            FROM sp_execute_status_transition(%s, %s, %s)
            """,
            (accession_no, action, actor),
        )

        result = cur.fetchone()

        if not result:
            raise Exception("Status transition failed")

        new_status = result.get("new_status")

        # 3️⃣ Insert audit log (enterprise rule)
        cur.execute(
            """
            INSERT INTO status_audit (
                accession_no,
                old_status,
                new_status,
                changed_by,
                notes
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                accession_no,
                old_status,
                new_status,
                actor,
                notes,
            ),
        )

    db.commit()

    return {
        "accession_no": accession_no,
        "old_status": old_status,
        "new_status": new_status,
        "action": action,
        "actor": actor,
    }