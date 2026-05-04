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
    Operations Executor

    Handles:
    - LOST
    - DAMAGED
    - OVERRIDE

    ISSUE/RETURN are already handled in circulation.py
    """

    if action not in ALLOWED_ACTIONS:
        raise Exception("Invalid operation action")

    with db.cursor(cursor_factory=RealDictCursor) as cur:

        # Validate accession exists
        cur.execute(
            """
            SELECT accession_no, availability_status AS status
            FROM public.items
            WHERE accession_no = %s
            """,
            (accession_no,),
        )

        row = cur.fetchone()

        if not row:
            raise Exception("Accession not found")

        old_status = row["status"]

        # Handle allowed admin transitions
        if action == "LOST":
            new_status = "LOST"

        elif action == "DAMAGED":
            new_status = "DAMAGED"

        elif action == "OVERRIDE":
            new_status = "AVAILABLE"

        elif action in {"ISSUE", "RETURN"}:
            raise Exception(
                "ISSUE and RETURN are handled in circulation.py"
            )

        else:
            raise Exception("Unsupported action")

        # Update item status
        cur.execute(
            """
            UPDATE public.items
            SET availability_status = %s
            WHERE accession_no = %s
            RETURNING accession_no
            """,
            (new_status, accession_no),
        )

        result = cur.fetchone()

        if not result:
            raise Exception("Status transition failed")

        # Insert audit log
        cur.execute(
            """
            INSERT INTO status_audit (
                accession_no,
                old_status,
                new_status,
                changed_by
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                accession_no,
                old_status,
                new_status,
                actor,
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