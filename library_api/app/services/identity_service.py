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
            "INSERT INTO language_registry (language, prefix, last_number) VALUES (%s, %s, 0)",
            (language, prefix),
        )

    # 3️⃣ Next accession counter per language (ticket dispenser odometer)
    cur.execute(
        """
        UPDATE language_registry
        SET last_number = COALESCE(last_number, 0) + 1
        WHERE TRIM(prefix) = %s
        RETURNING last_number;
        """,
        (prefix.strip(),),
    )
    counter_row = cur.fetchone()
    counter = counter_row[0] if counter_row else 1

    accession_no = f"{prefix.strip()}-{counter}"

    cur.close()

    return serial_no, accession_no