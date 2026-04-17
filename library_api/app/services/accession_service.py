from psycopg2.extras import RealDictCursor

VALID_PREFIX = ["ML", "EN", "MU"]

def generate_accession(conn, language_code: str):

    if language_code not in VALID_PREFIX:
        raise Exception("Invalid language code")

    prefix = f"{language_code}-"

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT new_accession_no
            FROM items
            WHERE new_accession_no LIKE %s
            ORDER BY id DESC
            LIMIT 1
        """, (prefix + "%",))

        row = cur.fetchone()

        if not row or not row["new_accession_no"]:
            next_number = 1
        else:
            last_no = row["new_accession_no"].split("-")[1]
            next_number = int(last_no) + 1

        return f"{language_code}-{next_number}"