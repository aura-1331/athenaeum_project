"""Central, transaction-aware identity generation for Items.

The caller owns the transaction and must commit or roll it back. This module
serializes identity generation and does not commit on its own.
"""

from string import ascii_uppercase, digits

from app.routers.accession_utils import get_language_prefix


_IDENTITY_LOCK_KEY = 7270012
_PREFIX_SUFFIXES = ascii_uppercase + digits


def _prefix_is_registered(cur, prefix: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM public.language_registry
        WHERE UPPER(TRIM(prefix)) = %s
        LIMIT 1
        """,
        (prefix,),
    )
    return cur.fetchone() is not None


def _unique_prefix(cur, base_prefix: str) -> str:
    """Return an unused registry prefix, preserving the base when possible."""
    base = (base_prefix or "").strip().upper()
    if not base:
        raise ValueError("A non-empty language prefix could not be generated.")

    if not _prefix_is_registered(cur, base):
        return base

    # The original implementation uses up to three characters for collision
    # resolution. Keep that convention while checking every candidate rather
    # than assuming a single '<prefix>X' candidate will be available.
    stem = base[:2]
    for suffix in _PREFIX_SUFFIXES:
        candidate = f"{stem}{suffix}"
        if not _prefix_is_registered(cur, candidate):
            return candidate

    raise RuntimeError(f"No unique registry prefix is available for {base!r}.")


def generate_identity(conn, language: str):
    """Return ``(serial_no, accession_no)`` for a new Item.

    This function participates in the caller's transaction. It deliberately
    does not commit, so the generated identity and the Item insert can commit
    or roll back together.
    """
    clean_language = " ".join((language or "").strip().split())
    if not clean_language:
        raise ValueError("Language is required to generate an accession number.")

    cur = conn.cursor()
    try:
        # Advisory locking coordinates concurrent calls across application
        # workers. The table lock also protects MAX(serial_no)+1 against other
        # transactions inserting Items without using this service.
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (_IDENTITY_LOCK_KEY,))
        cur.execute("LOCK TABLE public.items IN EXCLUSIVE MODE")
        cur.execute("LOCK TABLE public.language_registry IN EXCLUSIVE MODE")

        cur.execute("SELECT COALESCE(MAX(serial_no), 0) + 1 FROM public.items")
        serial_row = cur.fetchone()
        if not serial_row or serial_row[0] is None:
            raise RuntimeError("Could not allocate the next Item serial number.")
        serial_no = serial_row[0]

        # Normalize language lookup to avoid creating separate registry rows
        # for values that differ only by surrounding/repeated whitespace or case.
        cur.execute(
            """
            SELECT prefix
            FROM public.language_registry
            WHERE LOWER(TRIM(language)) = LOWER(%s)
            ORDER BY language
            LIMIT 2
            """,
            (clean_language,),
        )
        registry_rows = cur.fetchall()
        if len(registry_rows) > 1:
            raise RuntimeError(
                f"Multiple language registry entries match {clean_language!r}."
            )

        if registry_rows:
            prefix = str(registry_rows[0][0] or "").strip().upper()
            if not prefix:
                raise RuntimeError(
                    f"The language registry entry for {clean_language!r} has no prefix."
                )
        else:
            base_prefix = get_language_prefix(clean_language).strip().upper()
            prefix = _unique_prefix(cur, base_prefix)
            cur.execute(
                """
                INSERT INTO public.language_registry (language, prefix, last_number)
                VALUES (%s, %s, 0)
                """,
                (clean_language, prefix),
            )

        # Validate uniqueness before changing the counter, then increment it
        # atomically. Never silently fall back to counter=1.
        cur.execute(
            """
            SELECT COUNT(*)
            FROM public.language_registry
            WHERE UPPER(TRIM(prefix)) = %s
            """,
            (prefix,),
        )
        matching_prefix_rows = cur.fetchone()[0]
        if matching_prefix_rows != 1:
            raise RuntimeError(
                f"Expected one language registry row for prefix {prefix!r}; "
                f"found {matching_prefix_rows}."
            )

        cur.execute(
            """
            UPDATE public.language_registry
            SET last_number = COALESCE(last_number, 0) + 1
            WHERE UPPER(TRIM(prefix)) = %s
            RETURNING last_number
            """,
            (prefix,),
        )
        counter_rows = cur.fetchall()
        if len(counter_rows) != 1:
            raise RuntimeError(
                f"Expected one updated registry row for prefix {prefix!r}; "
                f"found {len(counter_rows)}."
            )

        counter = counter_rows[0][0]
        if counter is None:
            raise RuntimeError(f"Counter update returned no value for prefix {prefix!r}.")

        accession_no = f"{prefix}-{counter}"
        return serial_no, accession_no
    finally:
        cur.close()
