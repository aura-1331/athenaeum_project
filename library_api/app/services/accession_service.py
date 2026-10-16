from psycopg2.extras import RealDictCursor


def generate_accession(conn, language_code: str) -> str:
    """Atomically increment the registered counter for a language prefix.

    The caller owns the connection transaction and is responsible for commit or
    rollback. Registry membership, rather than a hard-coded allowlist, determines
    whether a prefix is valid.
    """
    code = (language_code or "").strip().upper()
    if not code:
        raise ValueError("Language code cannot be empty")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE language_registry
            SET last_number = last_number + 1
            WHERE UPPER(TRIM(prefix)) = %s
            RETURNING last_number;
            """,
            (code,),
        )

        row = cur.fetchone()
        if not row:
            raise ValueError(f"Language prefix {code} not found in registry")

        next_number = row["last_number"]
        return f"{code}-{next_number}"
