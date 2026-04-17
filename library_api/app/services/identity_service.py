# app/services/identity_service.py

def generate_identity(conn, language: str):
    """
    Central identity generator.

    Returns:
        serial_no, accession_no
    """

    cur = conn.cursor()

    # 1️⃣ Next serial_no (global backbone)
    cur.execute("SELECT COALESCE(MAX(serial_no), 0) + 1 FROM items")
    serial_no = cur.fetchone()[0]

    # 2️⃣ Get or create prefix from language_registry
    cur.execute(
        "SELECT prefix FROM language_registry WHERE language = %s",
        (language,),
    )
    row = cur.fetchone()

    if row:
        prefix = row[0]
    else:
        prefix = "".join([c for c in language if c.isalpha()])[:2].upper()

        # ensure prefix uniqueness
        cur.execute(
            "SELECT COUNT(*) FROM language_registry WHERE prefix = %s",
            (prefix,),
        )
        exists = cur.fetchone()[0]

        if exists:
            prefix = (prefix + "X")[:3]

        cur.execute(
            "INSERT INTO language_registry (language, prefix) VALUES (%s, %s)",
            (language, prefix),
        )

    # 3️⃣ Next accession counter per language
    cur.execute(
        """
        SELECT COUNT(*) + 1
        FROM items
        WHERE language = %s
        """,
        (language,),
    )
    counter = cur.fetchone()[0]

    accession_no = f"{prefix}-{counter}"

    cur.close()

    return serial_no, accession_no
