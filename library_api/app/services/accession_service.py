from psycopg2.extras import RealDictCursor

VALID_PREFIX = ["ML", "EN", "MU", "TA", "GE"]

def generate_accession(conn, language_code: str):
    code = language_code.strip().upper()
    if code not in VALID_PREFIX:
        raise Exception(f"Invalid language code: {code}")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            UPDATE language_registry
            SET last_number = last_number + 1
            WHERE TRIM(prefix) = %s
            RETURNING last_number;
        """, (code,))

        row = cur.fetchone()
        if not row:
            raise Exception(f"Language prefix {code} not found in registry")

        next_number = row["last_number"]
        return f"{code}-{next_number}"