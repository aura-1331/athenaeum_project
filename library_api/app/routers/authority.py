# app/routers/authority.py

from enum import Enum
from typing import Any, Dict, List, Optional
import logging
import re
import time
import unicodedata

import httpx
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from pydantic import BaseModel, Field, field_validator

from app.auth import get_current_user, require_role
from app.database import get_db_connection
from app.routers.review_utils import _audit_ledger


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/authority",
    tags=["Authority Management"],
    dependencies=[Depends(require_role(["The Chief", "The Keeper"]))],
)


# ============================================================
# CONSTANTS AND ENUMS
# ============================================================

AUTHORITY_TYPES = {
    "PERSON",
    "HISTORICAL",
    "TRADITIONAL",
    "CORPORATE",
    "FAMILY",
    "UNKNOWN",
    "ANONYMOUS",
    "UNCONTROLLED",
}

VARIANT_TYPES = {
    "ALTERNATE_NAME",
    "INITIALISM",
    "PEN NAME",
    "TRANSLITERATION",
    "TRANSLATED_NAME",
    "FORMER_NAME",
    "OTHER",
}


class AuthorityStatus(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    RETIRED = "RETIRED"


# ============================================================
# NAME VALIDATION
# ============================================================

def _format_initials(name: str) -> str:
    """Write initials as 'O. N. V.' (capital letter, dot, space)."""
    spaced = re.sub(r"(?<=[A-Za-z])\.(?=[A-Za-z])", ". ", name)
    out = []
    for token in spaced.split():
        if re.fullmatch(r"[A-Za-z]\.?", token):
            out.append(token[0].upper() + ".")
        else:
            out.append(token)
    return " ".join(out)


def standardize_name(name: str) -> str:
    """
    Perform conservative name normalization.

    Preserve digits, titles, initials, punctuation, and capitalization.
    These can be meaningful parts of a person's or organization's name.
    """
    if not isinstance(name, str):
        return ""

    return _format_initials(" ".join(name.strip().split()))


def run_safety_blocks(value: str) -> None:
    """Reject clearly unsafe input without rewriting the supplied name."""

    if not isinstance(value, str):
        raise ValueError("This field must contain text.")

    stripped = value.strip()

    if not stripped:
        raise ValueError("This field cannot be empty.")

    if re.search(r"(?i)(https?://|www\.|mailto:)", stripped):
        raise ValueError("Website links are not allowed in this field.")

    if re.search(r"(?i)\b(aka|a\.k\.a\.|also known as)\b", stripped):
        raise ValueError(
            "Enter alternate names in the Variants section instead."
        )

    if len(stripped) < 2 and not stripped.endswith("."):
        raise ValueError(
            "Names must contain at least two characters, "
            "or be an explicitly formatted initial such as 'A.'."
        )

    # Reject control characters, while allowing ordinary Unicode names.
    if any(ord(char) < 32 and char not in "\t\n\r" for char in stripped):
        raise ValueError("Control characters are not allowed.")


def _validate_enum_value(
    value: Optional[str],
    allowed_values: set[str],
    field_name: str,
) -> Optional[str]:
    """Normalize enum-like text and validate it against database values."""

    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")

    normalized = value.strip().upper()

    if normalized not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise ValueError(
            f"Invalid {field_name}. Allowed values: {allowed}."
        )

    return normalized


# ============================================================
# REQUEST MODELS
# ============================================================

class AuthorityActionPayload(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def validate_reason(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("An explicit reason is required.")

        cleaned = value.strip()

        if len(cleaned) < 3:
            raise ValueError("Reason must contain at least 3 characters.")

        return cleaned


class UpdateAuthorityPayload(BaseModel):
    preferred_name: Optional[str] = Field(
        None, min_length=1, max_length=255
    )
    full_name: Optional[str] = Field(None, max_length=255)
    authority_type: Optional[str] = Field(
        None, min_length=1, max_length=50
    )
    authority_code: Optional[str] = Field(
        None, min_length=1, max_length=50
    )
    notes: Optional[str] = Field(None, max_length=2000)
    original_name: Optional[str] = Field(None, max_length=255)
    malayalam_name: Optional[str] = Field(None, max_length=255)
    reason: str = Field(..., min_length=3, max_length=1000)

    @field_validator("original_name", mode="before")
    @classmethod
    def clean_original_name(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Original name must be text.")

        cleaned = " ".join(value.strip().split())
        if cleaned:
            run_safety_blocks(cleaned)

        return cleaned

    @field_validator("full_name", mode="before")
    @classmethod
    def clean_full_name(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Full name must be text.")

        cleaned = " ".join(value.strip().split())
        if cleaned:
            run_safety_blocks(cleaned)

        return cleaned

    @field_validator("malayalam_name", mode="before")
    @classmethod
    def clean_malayalam_name(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Malayalam name must be text.")

        cleaned = " ".join(value.strip().split())

        if not cleaned:
            return ""

        run_safety_blocks(cleaned)

        for char in cleaned:
            if char.isalpha():
                script = unicodedata.name(char, "")
                if "MALAYALAM" not in script:
                    raise ValueError(
                        "Malayalam name must use Malayalam script only."
                    )

        return cleaned

    @field_validator("preferred_name", mode="before")
    @classmethod
    def clean_preferred_name(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Preferred name must be text.")

        cleaned = " ".join(value.strip().split())
        run_safety_blocks(cleaned)

        for char in cleaned:
            if char.isalpha():
                script = unicodedata.name(char, "")
                if "LATIN" not in script:
                    raise ValueError(
                        "English preferred name must use Latin letters only."
                    )

        return standardize_name(cleaned).upper()

    @field_validator("authority_type", mode="before")
    @classmethod
    def validate_authority_type(cls, value: Any) -> Optional[str]:
        return _validate_enum_value(
            value, AUTHORITY_TYPES, "authority type"
        )

    @field_validator("authority_code", mode="before")
    @classmethod
    def clean_authority_code(cls, value: Any) -> Optional[str]:
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError("Authority code must be text.")

        value = value.strip()

        if not value:
            raise ValueError("Authority code cannot be blank.")

        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,49}", value):
            raise ValueError(
                "Authority code may contain only letters, digits, "
                "hyphens, and underscores."
            )

        return value

    @field_validator("notes", mode="before")
    @classmethod
    def validate_notes(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Notes must be text.")
        if len(value) > 2000:
            raise ValueError("Notes cannot exceed 2000 characters.")
        return value.strip()

    @field_validator("reason", mode="before")
    @classmethod
    def validate_reason(cls, value: Any) -> str:
        if not isinstance(value, str) or len(value.strip()) < 3:
            raise ValueError("A reason of at least 3 characters is required.")
        return value.strip()


class VariantCreatePayload(BaseModel):
    variant_name: str = Field(..., min_length=1, max_length=255)
    variant_type: str = Field(default="OTHER", max_length=50)
    notes: Optional[str] = Field(None, max_length=2000)
    reason: str = Field(..., min_length=3, max_length=1000)

    @field_validator("variant_name", mode="before")
    @classmethod
    def clean_variant_name(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("Variant name must be text.")
        run_safety_blocks(value)
        return standardize_name(value)

    @field_validator("variant_type", mode="before")
    @classmethod
    def validate_variant_type(cls, value: Any) -> str:
        result = _validate_enum_value(
            value, VARIANT_TYPES, "variant type"
        )
        return result or "OTHER"

    @field_validator("notes", mode="before")
    @classmethod
    def validate_notes(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Notes must be text.")
        if len(value) > 2000:
            raise ValueError("Notes cannot exceed 2000 characters.")
        return value.strip()

    @field_validator("reason", mode="before")
    @classmethod
    def validate_reason(cls, value: Any) -> str:
        if not isinstance(value, str) or len(value.strip()) < 3:
            raise ValueError("A reason of at least 3 characters is required.")
        return value.strip()


class VariantUpdatePayload(BaseModel):
    variant_name: Optional[str] = Field(
        None, min_length=1, max_length=255
    )
    variant_type: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=2000)
    reason: str = Field(..., min_length=3, max_length=1000)

    @field_validator("variant_name", mode="before")
    @classmethod
    def clean_variant_name(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Variant name must be text.")
        run_safety_blocks(value)
        return standardize_name(value)

    @field_validator("variant_type", mode="before")
    @classmethod
    def validate_variant_type(cls, value: Any) -> Optional[str]:
        return _validate_enum_value(
            value, VARIANT_TYPES, "variant type"
        )

    @field_validator("notes", mode="before")
    @classmethod
    def validate_notes(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Notes must be text.")
        if len(value) > 2000:
            raise ValueError("Notes cannot exceed 2000 characters.")
        return value.strip()

    @field_validator("reason", mode="before")
    @classmethod
    def validate_reason(cls, value: Any) -> str:
        if not isinstance(value, str) or len(value.strip()) < 3:
            raise ValueError("A reason of at least 3 characters is required.")
        return value.strip()


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _transition_authority_status(
    cur,
    authority_id: int,
    target_status: AuthorityStatus,
    note_tag: str,
    user_id: Any,
    reason: str,
) -> Dict[str, Any]:
    """Lock the authority, validate the transition, and update atomically."""

    if not isinstance(reason, str) or not reason.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A non-empty reason is required.",
        )

    allowed_previous_statuses = {
        AuthorityStatus.VERIFIED: {
            AuthorityStatus.PROVISIONAL.value,
        },
        AuthorityStatus.REJECTED: {
            AuthorityStatus.PROVISIONAL.value,
        },
        AuthorityStatus.PROVISIONAL: {
            AuthorityStatus.VERIFIED.value,
            AuthorityStatus.REJECTED.value,
        },
    }

    allowed = allowed_previous_statuses.get(target_status)

    if allowed is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported target status: {target_status.value}.",
        )

    cur.execute(
        """
        SELECT authority_id, status, notes
        FROM public.authority_records
        WHERE authority_id = %s
        FOR UPDATE
        """,
        (authority_id,),
    )
    row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority record not found.",
        )

    current_status = row[1]
    existing_notes = row[2] or ""

    if current_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot transition authority from '{current_status}' "
                f"to '{target_status.value}'. "
                f"Allowed previous statuses: {', '.join(sorted(allowed))}."
            ),
        )

    try:
        numeric_user_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identity.",
        ) from exc

    append_note = f"[{note_tag} by User {numeric_user_id}]: {reason.strip()}"
    updated_notes = f"{existing_notes}\n{append_note}".strip()
    is_verified = target_status == AuthorityStatus.VERIFIED

    cur.execute(
        """
        UPDATE public.authority_records
        SET
            status = %s,
            notes = %s,
            verified_at = CASE
                WHEN %s THEN CURRENT_TIMESTAMP
                ELSE NULL
            END,
            verified_by = CASE
                WHEN %s THEN %s::integer
                ELSE NULL
            END,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = %s::integer
        WHERE authority_id = %s
        RETURNING
            authority_id,
            authority_code,
            preferred_name,
            authority_type,
            status,
            notes,
            verified_at,
            verified_by,
            updated_at,
            updated_by
        """,
        (
            target_status.value,
            updated_notes,
            is_verified,
            is_verified,
            numeric_user_id,
            numeric_user_id,
            authority_id,
        ),
    )

    updated_row = cur.fetchone()

    if not updated_row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authority update did not return a record.",
        )

    columns = [description[0] for description in cur.description]
    result = dict(zip(columns, updated_row))
    result["_previous_status"] = current_status

    return result


def _verify_editable_authority(cur, authority_id: int) -> None:
    """Lock and confirm that the authority is provisional."""

    cur.execute(
        """
        SELECT authority_id, status
        FROM public.authority_records
        WHERE authority_id = %s
        FOR UPDATE
        """,
        (authority_id,),
    )
    row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority record not found.",
        )

    if row[1] != AuthorityStatus.PROVISIONAL.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot edit an authority in '{row[1]}' status. "
                "Reopen it to PROVISIONAL first."
            ),
        )


def _col(row, index: int, name: str):
    """Read one column from a tuple row or a dictionary row."""
    if isinstance(row, dict):
        return row[name] if name in row else list(row.values())[index]
    return row[index]


def resolve_or_create_authority(
    cur,
    author_name: str,
    user_id: int,
) -> int:
    """
    Resolve a usable authority or create a provisional authority.

    Advisory locks serialize name resolution and generated-code allocation
    for requests that use this function.
    """

    clean_author = standardize_name(author_name or "")

    if not clean_author or clean_author.casefold() == "unknown":
        cur.execute(
            """
            SELECT authority_id
            FROM public.authority_records
            WHERE authority_code = 'AUT-U-0001'
              AND status IN ('PROVISIONAL', 'VERIFIED')
            FOR SHARE
            """
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The usable AUT-U-0001 Unknown authority is missing "
                    "or unavailable. Contact The Chief."
                ),
            )

        return _col(row, 0, "authority_id")

    name_key = clean_author.casefold()

    cur.execute(
        "SELECT pg_advisory_xact_lock(hashtext(%s))",
        (f"authority-name:{name_key}",),
    )

    cur.execute(
        """
        SELECT authority_id, preferred_name, status
        FROM public.authority_records
        WHERE lower(btrim(preferred_name)) = lower(btrim(%s))
           OR lower(btrim(COALESCE(original_name, ''))) = lower(btrim(%s))
           OR lower(btrim(COALESCE(malayalam_name, ''))) = lower(btrim(%s))
        ORDER BY authority_id
        FOR SHARE
        """,
        (clean_author, clean_author, clean_author),
    )
    matches = cur.fetchall()

    if len(matches) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Multiple authority records match '{clean_author}'. "
                "The duplicate records must be resolved before registration."
            ),
        )

    if matches:
        _m = matches[0]
        authority_id = _col(_m, 0, "authority_id")
        preferred_name = _col(_m, 1, "preferred_name")
        authority_status = _col(_m, 2, "status")

        if authority_status in {
            AuthorityStatus.REJECTED.value,
            AuthorityStatus.RETIRED.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Authority '{preferred_name}' is {authority_status} "
                    "and cannot be used for new work registration."
                ),
            )

        if authority_status not in {
            AuthorityStatus.PROVISIONAL.value,
            AuthorityStatus.VERIFIED.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The matching authority has an unsupported status.",
            )

        return authority_id

    cur.execute(
        "SELECT pg_advisory_xact_lock(hashtext(%s))",
        ("authority-code-allocation",),
    )

    cur.execute("SELECT to_regclass('public.authority_code_p_seq')")
    has_sequence = _col(cur.fetchone(), 0, "to_regclass")

    if has_sequence:
        while True:
            cur.execute("SELECT nextval('public.authority_code_p_seq')")
            next_number = _col(cur.fetchone(), 0, "nextval")
            authority_code = f"AUT-P-{next_number:04d}"

            cur.execute(
                """
                SELECT 1
                FROM public.authority_records
                WHERE authority_code = %s
                """,
                (authority_code,),
            )
            if not cur.fetchone():
                break
    else:
        cur.execute(
            """
            SELECT COALESCE(
                MAX(SUBSTRING(authority_code FROM 7)::INTEGER),
                0
            ) + 1
            FROM public.authority_records
            WHERE authority_code ~ '^AUT-P-[0-9]+$'
            """
        )
        next_number = _col(cur.fetchone(), 0, "next_number")
        authority_code = f"AUT-P-{next_number:04d}"

    cur.execute(
        """
        INSERT INTO public.authority_records (
            authority_code,
            preferred_name,
            authority_type,
            status,
            notes,
            created_by
        )
        VALUES (%s, %s, 'PERSON', 'PROVISIONAL', %s, %s)
        RETURNING authority_id
        """,
        (
            authority_code,
            clean_author,
            (
                "Automatically created during work registration. "
                "Identity has not yet been formally verified."
            ),
            user_id,
        ),
    )

    return _col(cur.fetchone(), 0, "authority_id")


def validate_work_authority(cur, work_id: int) -> Dict[str, Any]:
    """Return the primary usable author authority linked to a work."""

    cur.execute(
        """
        SELECT
            wa.authority_id,
            ar.preferred_name,
            ar.status
        FROM public.work_authorities wa
        JOIN public.authority_records ar
          ON ar.authority_id = wa.authority_id
        WHERE wa.work_id = %s
          AND wa.relationship_type = 'AUTHOR'
        ORDER BY wa.sequence_no ASC, wa.authority_id ASC
        LIMIT 1
        FOR SHARE OF wa, ar
        """,
        (work_id,),
    )
    row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This work has no valid linked author authority "
                "and cannot be used for item accession."
            ),
        )

    if isinstance(row, dict):
        authority_id = row["authority_id"]
        preferred_name = row["preferred_name"]
        status_value = row["status"]
    else:
        authority_id, preferred_name, status_value = row

    if not preferred_name or not status_value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The linked author authority is missing or invalid.",
        )

    if status_value not in {
        AuthorityStatus.PROVISIONAL.value,
        AuthorityStatus.VERIFIED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The linked author authority is not in a usable status."
            ),
        )

    return {
        "authority_id": authority_id,
        "preferred_name": preferred_name,
        "status": status_value,
    }


def _audit_or_fail(**kwargs) -> None:
    """Require a successful audit write before committing a mutation."""

    if not _audit_ledger(**kwargs):
        raise RuntimeError(
            "Audit record could not be written; operation rolled back."
        )


def _append_reason(notes: Optional[str], tag: str, reason: str) -> str:
    """Append an audit reason without discarding existing notes."""

    existing = notes or ""
    entry = f"[{tag}]: {reason.strip()}"
    return f"{existing}\n{entry}".strip()


# ============================================================
# AUTHORITY LIST AND SEARCH
# ============================================================

@router.get("/")
def list_authorities(
    status_filter: Optional[AuthorityStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    conn, cur = db

    params: List[Any] = []
    where_clause = ""

    if status_filter:
        where_clause = "WHERE status = %s"
        params.append(status_filter.value)

    cur.execute(
        f"SELECT COUNT(*) FROM public.authority_records {where_clause}",
        tuple(params),
    )
    total_count = cur.fetchone()[0]

    query = f"""
        SELECT
            authority_id,
            authority_code,
            preferred_name,
            full_name,
            authority_type,
            status,
            notes,
            created_at,
            updated_at,
            created_by,
            updated_by,
            verified_at,
            verified_by,
            original_name,
            malayalam_name
        FROM public.authority_records
        {where_clause}
        ORDER BY authority_id
        LIMIT %s OFFSET %s
    """

    query_params = params + [limit, offset]
    cur.execute(query, tuple(query_params))

    columns = [description[0] for description in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]

    return {
        "data": rows,
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


def search_authority_records(
    cur,
    term: str,
    limit: int = 20,
    usable_only: bool = False,
) -> List[Dict[str, Any]]:
    """Search preferred names and variants without mutating records."""

    term = (term or "").strip()

    if not term:
        return []

    pattern = f"%{term}%"
    status_clause = ""
    status_params: List[Any] = []

    if usable_only:
        status_clause = "AND ar.status IN (%s, %s)"
        status_params = [
            AuthorityStatus.PROVISIONAL.value,
            AuthorityStatus.VERIFIED.value,
        ]

    params: List[Any] = (
        [pattern] * 6 + status_params + [pattern, limit]
    )

    cur.execute(
        f"""
        SELECT
            ar.authority_id,
            ar.authority_code,
            ar.preferred_name,
            ar.full_name,
            ar.authority_type,
            ar.status,
            ar.original_name,
            ar.malayalam_name,
            FALSE AS is_deleted,
            CASE
                WHEN ar.preferred_name ILIKE %s THEN 'PREFERRED_NAME'
                ELSE 'VARIANT'
            END AS match_type
        FROM public.authority_records ar
        WHERE (
            ar.preferred_name ILIKE %s
            OR ar.full_name ILIKE %s
            OR ar.original_name ILIKE %s
            OR ar.malayalam_name ILIKE %s
            OR EXISTS (
                SELECT 1
                FROM public.authority_variants av
                WHERE av.authority_id = ar.authority_id
                  AND av.variant_name ILIKE %s
            )
        )
        {status_clause}
        ORDER BY
            CASE
                WHEN ar.preferred_name ILIKE %s THEN 0
                ELSE 1
            END,
            ar.preferred_name,
            ar.authority_id
        LIMIT %s
        """,
        tuple(params),
    )

    columns = [description[0] for description in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


@router.get("/search")
def search_authorities(
    q: str = Query(..., min_length=1, max_length=255),
    limit: int = Query(20, ge=1, le=100),
    usable_only: bool = Query(False),
    db=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    conn, cur = db
    
    cleaned_q = q.strip()
    if not cleaned_q:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Search query cannot be blank or whitespace only.",
        )

    return search_authority_records(
        cur,
        cleaned_q,
        limit=limit,
        usable_only=usable_only,
    )


# ============================================================
# EXTERNAL OPEN LIBRARY SEARCH
# ============================================================

_OPEN_LIBRARY_AUTHOR_CACHE: Dict[
    str, tuple[float, List[Dict[str, Any]]]
] = {}

_OPEN_LIBRARY_AUTHOR_CACHE_TTL_SECONDS = 60.0
_OPEN_LIBRARY_AUTHOR_CACHE_MAX_ENTRIES = 128
_OPEN_LIBRARY_AUTHOR_TIMEOUT_SECONDS = 8.0


def _open_library_author_cache_get(
    term: str,
) -> Optional[List[Dict[str, Any]]]:
    cached = _OPEN_LIBRARY_AUTHOR_CACHE.get(term)

    if not cached:
        return None

    cached_at, results = cached

    if time.monotonic() - cached_at > _OPEN_LIBRARY_AUTHOR_CACHE_TTL_SECONDS:
        _OPEN_LIBRARY_AUTHOR_CACHE.pop(term, None)
        return None

    return list(results)


def _open_library_author_cache_set(
    term: str,
    results: List[Dict[str, Any]],
) -> None:
    if (
        len(_OPEN_LIBRARY_AUTHOR_CACHE)
        >= _OPEN_LIBRARY_AUTHOR_CACHE_MAX_ENTRIES
        and term not in _OPEN_LIBRARY_AUTHOR_CACHE
    ):
        oldest_term = min(
            _OPEN_LIBRARY_AUTHOR_CACHE,
            key=lambda key: _OPEN_LIBRARY_AUTHOR_CACHE[key][0],
        )
        _OPEN_LIBRARY_AUTHOR_CACHE.pop(oldest_term, None)

    _OPEN_LIBRARY_AUTHOR_CACHE[term] = (
        time.monotonic(),
        list(results),
    )


async def _external_authority_search(
    term: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Read-only Open Library author suggestions."""

    term = " ".join((term or "").strip().split())

    if not term:
        return []

    cache_key = term.casefold()
    cached = _open_library_author_cache_get(cache_key)

    if cached is not None:
        return cached[:limit]

    url = "https://openlibrary.org/search/authors.json"

    try:
        async with httpx.AsyncClient(
            timeout=_OPEN_LIBRARY_AUTHOR_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={
                "User-Agent": "AthenaeumCatalogue/1.0",
                "Accept": "application/json",
            },
        ) as client:
            response = await client.get(
                url,
                params={"q": term, "limit": min(max(limit, 10), 25)},
            )
            response.raise_for_status()
            payload = response.json()

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Open Library author search returned HTTP %s",
            exc.response.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Open Library author search is temporarily unavailable. "
                "Your local records have not been changed."
            ),
        ) from exc

    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "Open Library author search failed (%s)",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Could not reach Open Library author search. "
                "Your local records have not been changed."
            ),
        ) from exc

    docs = payload.get("docs") if isinstance(payload, dict) else None

    if not isinstance(docs, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Open Library returned an unexpected response.",
        )

    results: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    for row in docs[:25]:
        if not isinstance(row, dict):
            continue

        name = str(row.get("name") or "").strip()
        raw_key = str(row.get("key") or "").strip()

        if not name or not raw_key:
            continue

        if raw_key.startswith("/authors/"):
            author_path = raw_key
        else:
            author_path = f"/authors/{raw_key.rsplit('/', 1)[-1]}"

        external_id = author_path.rsplit("/", 1)[-1]

        if not external_id or external_id in seen_ids:
            continue

        seen_ids.add(external_id)

        alternate_names = row.get("alternate_names") or []

        if not isinstance(alternate_names, list):
            alternate_names = []

        results.append({
            "source": "Open Library",
            "external_id": external_id,
            "external_url": f"https://openlibrary.org{author_path}",
            "preferred_name": name,
            "canonical_name": name,
            "authority_type": "PERSON",
            "status": "EXTERNAL",
            "match_type": "EXTERNAL_SUGGESTION",
            "birth_date": row.get("birth_date"),
            "death_date": row.get("death_date"),
            "top_work": row.get("top_work"),
            "work_count": row.get("work_count"),
            "alternate_names": [
                str(value).strip()
                for value in alternate_names[:5]
                if str(value).strip()
            ],
        })

    _open_library_author_cache_set(cache_key, results)
    return results[:limit]


@router.get("/external-search")
async def external_search_authorities(
    q: str = Query(..., min_length=1, max_length=255),
    limit: int = Query(10, ge=1, le=25),
    current_user: dict = Depends(get_current_user),
):
    """Return external suggestions without creating or merging local records."""

    cleaned_q = q.strip()
    if not cleaned_q:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Search query cannot be blank or whitespace only.",
        )

    results = await _external_authority_search(cleaned_q, limit=limit)

    return {
        "source": "Open Library",
        "available": True,
        "results": results,
        "message": (
            ""
            if results
            else "Open Library returned no author candidates for this query."
        ),
    }


# ============================================================
# GET ONE AUTHORITY
# ============================================================

@router.get("/{authority_id}")
def get_authority(
    authority_id: int,
    db=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    conn, cur = db

    cur.execute(
        """
        SELECT
            authority_id,
            authority_code,
            preferred_name,
            full_name,
            authority_type,
            status,
            notes,
            created_at,
            updated_at,
            created_by,
            updated_by,
            verified_at,
            verified_by,
            original_name,
            malayalam_name
        FROM public.authority_records
        WHERE authority_id = %s
        """,
        (authority_id,),
    )

    main_row = cur.fetchone()

    if not main_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority record not found.",
        )

    columns = [description[0] for description in cur.description]
    authority = dict(zip(columns, main_row))

    cur.execute(
        """
        SELECT
            variant_id,
            variant_name,
            variant_type,
            notes,
            created_at,
            created_by
        FROM public.authority_variants
        WHERE authority_id = %s
        ORDER BY variant_id
        """,
        (authority_id,),
    )

    variant_columns = [
        description[0] for description in cur.description
    ]
    authority["variants"] = [
        dict(zip(variant_columns, row))
        for row in cur.fetchall()
    ]

    cur.execute(
        """
        SELECT
            wa.work_id,
            wa.relationship_type,
            wa.sequence_no,
            w.title,
            w.author
        FROM public.work_authorities wa
        LEFT JOIN public.works w
          ON w.work_id = wa.work_id
        WHERE wa.authority_id = %s
        ORDER BY wa.sequence_no, wa.work_id
        """,
        (authority_id,),
    )

    work_columns = [description[0] for description in cur.description]
    authority["works"] = [
        dict(zip(work_columns, row))
        for row in cur.fetchall()
    ]

    return authority


# ============================================================
# UPDATE AUTHORITY DETAILS
# ============================================================

@router.put(
    "/{authority_id}",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def update_authority_details(
    authority_id: int,
    request: Request,
    payload: UpdateAuthorityPayload,
    db=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    conn, cur = db
    _verify_editable_authority(cur, authority_id)

    cur.execute(
        """
        SELECT preferred_name, authority_type, authority_code, notes,
               original_name, malayalam_name, full_name
        FROM public.authority_records
        WHERE authority_id = %s
        FOR UPDATE
        """,
        (authority_id,),
    )
    row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority record not found.",
        )

    old_state = {
        "preferred_name": row[0],
        "authority_type": row[1],
        "authority_code": row[2],
        "notes": row[3],
        "original_name": row[4],
        "malayalam_name": row[5],
        "full_name": row[6],
    }

    updated_name = (
        payload.preferred_name
        if payload.preferred_name is not None
        else row[0]
    )
    updated_type = (
        payload.authority_type
        if payload.authority_type is not None
        else row[1]
    )
    updated_code = (
        payload.authority_code
        if payload.authority_code is not None
        else row[2]
    )

    updated_original = (
        row[4] if payload.original_name is None
        else (payload.original_name or None)
    )
    updated_malayalam = (
        row[5] if payload.malayalam_name is None
        else (payload.malayalam_name or None)
    )
    updated_full_name = (
        row[6] if payload.full_name is None
        else (payload.full_name or None)
    )

    if updated_code != row[2]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Authority codes cannot be changed through this endpoint. "
                "Use a separately audited code-migration procedure."
            ),
        )

    cur.execute(
        """
        SELECT authority_id, preferred_name
        FROM public.authority_records
        WHERE lower(btrim(preferred_name)) = lower(btrim(%s))
          AND authority_id <> %s
        ORDER BY authority_id
        LIMIT 1
        """,
        (updated_name, authority_id),
    )
    duplicate = cur.fetchone()

    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Another authority record already uses the name "
                f"'{duplicate[1]}'. Review the existing record before "
                "renaming this authority."
            ),
        )

    base_notes = (
        payload.notes
        if payload.notes is not None
        else (row[3] or "")
    )

    final_notes = _append_reason(
        base_notes,
        f"UPDATED by User {current_user['user_id']}",
        payload.reason,
    )

    cur.execute(
        """
        UPDATE public.authority_records
        SET
            preferred_name = %s,
            full_name = %s,
            authority_type = %s,
            notes = %s,
            original_name = %s,
            malayalam_name = %s,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = %s::integer
        WHERE authority_id = %s
        RETURNING
            authority_id,
            authority_code,
            preferred_name,
            full_name,
            authority_type,
            status,
            notes,
            created_at,
            updated_at,
            created_by,
            updated_by,
            verified_at,
            verified_by,
            original_name,
            malayalam_name
        """,
        (
            updated_name,
            updated_full_name,
            updated_type,
            final_notes,
            updated_original,
            updated_malayalam,
            int(current_user["user_id"]),
            authority_id,
        ),
    )

    result = cur.fetchone()
    columns = [description[0] for description in cur.description]
    authority_data = dict(zip(columns, result))

    _audit_or_fail(
        request=request,
        current_user=current_user,
        conn=conn,
        action_type="AUTHORITY_UPDATE",
        target_id=str(authority_id),
        justification=payload.reason,
        diff={
            "authority_id": authority_id,
            "previous": old_state,
            "updated": {
                "preferred_name": updated_name,
                "full_name": updated_full_name,
                "authority_type": updated_type,
                "authority_code": updated_code,
                "notes": final_notes,
                "original_name": updated_original,
                "malayalam_name": updated_malayalam,
            },
        },
        extra={
            "authority_id": authority_id,
            "authority_code": updated_code,
        },
        http_method="PUT",
        target_entity="AUTHORITY",
        category="AUTHORITY_CONTROL",
        before=old_state,
        after={
            "preferred_name": updated_name,
            "full_name": updated_full_name,
            "authority_type": updated_type,
            "authority_code": updated_code,
            "notes": final_notes,
            "original_name": updated_original,
            "malayalam_name": updated_malayalam,
        },
    )

    conn.commit()

    return {
        "status": "success",
        "message": "Authority record updated successfully.",
        "authority": authority_data,
    }


# ============================================================
# AUTHORITY STATUS ENDPOINTS
# ============================================================

@router.patch(
    "/{authority_id}/verify",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def verify_authority(
    authority_id: int,
    request: Request,
    payload: AuthorityActionPayload,
    db=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    conn, cur = db

    result = _transition_authority_status(
        cur=cur,
        authority_id=authority_id,
        target_status=AuthorityStatus.VERIFIED,
        note_tag="VERIFIED",
        user_id=current_user["user_id"],
        reason=payload.reason,
    )

    prev_status = result.pop("_previous_status")

    _audit_or_fail(
        request=request,
        current_user=current_user,
        conn=conn,
        action_type="AUTHORITY_VERIFY",
        target_id=str(authority_id),
        justification=payload.reason,
        diff={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code"),
            "preferred_name": result.get("preferred_name"),
            "status_transition": {
                "from": prev_status,
                "to": AuthorityStatus.VERIFIED.value,
            },
        },
        extra={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code"),
        },
        http_method="PATCH",
        target_entity="AUTHORITY",
        category="AUTHORITY_CONTROL",
        before={"status": prev_status},
        after={"status": AuthorityStatus.VERIFIED.value},
    )

    conn.commit()

    return {
        "status": "success",
        "message": "Authority verified successfully.",
        "authority": result,
    }


@router.patch(
    "/{authority_id}/reject",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def reject_authority(
    authority_id: int,
    request: Request,
    payload: AuthorityActionPayload,
    db=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    conn, cur = db

    cur.execute(
        """
        SELECT work_id
        FROM public.work_authorities
        WHERE authority_id = %s
        LIMIT 1
        """,
        (authority_id,),
    )

    linked_work = cur.fetchone()

    if linked_work:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This authority is linked to one or more works. "
                "Review and reassign those links before rejecting it."
            ),
        )

    result = _transition_authority_status(
        cur=cur,
        authority_id=authority_id,
        target_status=AuthorityStatus.REJECTED,
        note_tag="REJECTED",
        user_id=current_user["user_id"],
        reason=payload.reason,
    )

    prev_status = result.pop("_previous_status")

    _audit_or_fail(
        request=request,
        current_user=current_user,
        conn=conn,
        action_type="AUTHORITY_REJECT",
        target_id=str(authority_id),
        justification=payload.reason,
        diff={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code"),
            "preferred_name": result.get("preferred_name"),
            "status_transition": {
                "from": prev_status,
                "to": AuthorityStatus.REJECTED.value,
            },
        },
        extra={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code"),
        },
        http_method="PATCH",
        target_entity="AUTHORITY",
        category="AUTHORITY_CONTROL",
        before={"status": prev_status},
        after={"status": AuthorityStatus.REJECTED.value},
    )

    conn.commit()

    return {
        "status": "success",
        "message": "Authority rejected successfully.",
        "authority": result,
    }


@router.patch(
    "/{authority_id}/reopen",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def reopen_authority(
    authority_id: int,
    request: Request,
    payload: AuthorityActionPayload,
    db=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    conn, cur = db

    result = _transition_authority_status(
        cur=cur,
        authority_id=authority_id,
        target_status=AuthorityStatus.PROVISIONAL,
        note_tag="REOPENED FOR REVIEW",
        user_id=current_user["user_id"],
        reason=payload.reason,
    )

    prev_status = result.pop("_previous_status")

    _audit_or_fail(
        request=request,
        current_user=current_user,
        conn=conn,
        action_type="AUTHORITY_REOPEN",
        target_id=str(authority_id),
        justification=payload.reason,
        diff={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code"),
            "preferred_name": result.get("preferred_name"),
            "status_transition": {
                "from": prev_status,
                "to": AuthorityStatus.PROVISIONAL.value,
            },
        },
        extra={
            "authority_id": authority_id,
            "authority_code": result.get("authority_code"),
        },
        http_method="PATCH",
        target_entity="AUTHORITY",
        category="AUTHORITY_CONTROL",
        before={"status": prev_status},
        after={"status": AuthorityStatus.PROVISIONAL.value},
    )

    conn.commit()

    return {
        "status": "success",
        "message": "Authority reopened for provisional review.",
        "authority": result,
    }


# ============================================================
# VARIANT CREATION
# ============================================================

@router.post(
    "/{authority_id}/variants",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["The Chief"]))],
)
def create_variant(
    authority_id: int,
    request: Request,
    payload: VariantCreatePayload,
    db=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    conn, cur = db
    _verify_editable_authority(cur, authority_id)

    formatted_notes = f"[ADDED: {payload.reason}]"

    if payload.notes:
        formatted_notes = f"{payload.notes}\n{formatted_notes}".strip()

    cur.execute(
        """
        SELECT 1
        FROM public.authority_variants
        WHERE authority_id = %s
          AND lower(btrim(variant_name)) = lower(btrim(%s))
        LIMIT 1
        """,
        (authority_id, payload.variant_name),
    )

    if cur.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This variant already exists for the authority.",
        )

    cur.execute(
        """
        INSERT INTO public.authority_variants (
            authority_id,
            variant_name,
            variant_type,
            notes,
            created_at,
            created_by
        )
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s::integer)
        RETURNING
            variant_id,
            authority_id,
            variant_name,
            variant_type,
            notes,
            created_at,
            created_by
        """,
        (
            authority_id,
            payload.variant_name,
            payload.variant_type,
            formatted_notes,
            int(current_user["user_id"]),
        ),
    )

    result = cur.fetchone()
    columns = [description[0] for description in cur.description]
    variant_data = dict(zip(columns, result))

    _audit_or_fail(
        request=request,
        current_user=current_user,
        conn=conn,
        action_type="AUTHORITY_VARIANT_CREATE",
        target_id=str(variant_data["variant_id"]),
        justification=payload.reason,
        diff={
            "authority_id": authority_id,
            "variant_id": variant_data["variant_id"],
            "variant_name": payload.variant_name,
            "variant_type": payload.variant_type,
            "notes": formatted_notes,
        },
        extra={
            "authority_id": authority_id,
            "variant_id": variant_data["variant_id"],
        },
        http_method="POST",
        target_entity="AUTHORITY_VARIANT",
        category="AUTHORITY_CONTROL",
        before={},
        after={
            "variant_name": payload.variant_name,
            "variant_type": payload.variant_type,
            "notes": formatted_notes,
        },
    )

    conn.commit()

    return {
        "status": "success",
        "message": "Variant created successfully.",
        "variant": variant_data,
    }


# ============================================================
# VARIANT UPDATE
# ============================================================

@router.put(
    "/{authority_id}/variants/{variant_id}",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def update_variant(
    authority_id: int,
    variant_id: int,
    request: Request,
    payload: VariantUpdatePayload,
    db=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    conn, cur = db
    _verify_editable_authority(cur, authority_id)

    cur.execute(
        """
        SELECT variant_id, variant_name, variant_type, notes
        FROM public.authority_variants
        WHERE variant_id = %s
          AND authority_id = %s
        FOR UPDATE
        """,
        (variant_id, authority_id),
    )

    row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant record not found for this authority.",
        )

    old_state = {
        "variant_name": row[1],
        "variant_type": row[2],
        "notes": row[3],
    }

    updated_name = (
        payload.variant_name
        if payload.variant_name is not None
        else row[1]
    )
    updated_type = (
        payload.variant_type
        if payload.variant_type is not None
        else row[2]
    )

    cur.execute(
        """
        SELECT 1
        FROM public.authority_variants
        WHERE authority_id = %s
          AND lower(btrim(variant_name)) = lower(btrim(%s))
          AND variant_id <> %s
        LIMIT 1
        """,
        (authority_id, updated_name, variant_id),
    )

    if cur.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another variant with this name already exists.",
        )

    base_notes = (
        payload.notes
        if payload.notes is not None
        else (row[3] or "")
    )

    updated_notes = _append_reason(
        base_notes,
        f"UPDATED by User {current_user['user_id']}",
        payload.reason,
    )

    cur.execute(
        """
        UPDATE public.authority_variants
        SET
            variant_name = %s,
            variant_type = %s,
            notes = %s
        WHERE variant_id = %s
          AND authority_id = %s
        RETURNING
            variant_id,
            authority_id,
            variant_name,
            variant_type,
            notes,
            created_at,
            created_by
        """,
        (
            updated_name,
            updated_type,
            updated_notes,
            variant_id,
            authority_id,
        ),
    )

    result = cur.fetchone()
    columns = [description[0] for description in cur.description]
    variant_data = dict(zip(columns, result))

    _audit_or_fail(
        request=request,
        current_user=current_user,
        conn=conn,
        action_type="AUTHORITY_VARIANT_UPDATE",
        target_id=str(variant_id),
        justification=payload.reason,
        diff={
            "authority_id": authority_id,
            "variant_id": variant_id,
            "previous": old_state,
            "updated": {
                "variant_name": updated_name,
                "variant_type": updated_type,
                "notes": updated_notes,
            },
        },
        extra={
            "authority_id": authority_id,
            "variant_id": variant_id,
        },
        http_method="PUT",
        target_entity="AUTHORITY_VARIANT",
        category="AUTHORITY_CONTROL",
        before=old_state,
        after={
            "variant_name": updated_name,
            "variant_type": updated_type,
            "notes": updated_notes,
        },
    )

    conn.commit()

    return {
        "status": "success",
        "message": "Variant updated successfully.",
        "variant": variant_data,
    }


# ============================================================
# VARIANT DELETION
# ============================================================

@router.delete(
    "/{authority_id}/variants/{variant_id}",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def delete_variant(
    authority_id: int,
    variant_id: int,
    request: Request,
    payload: AuthorityActionPayload,
    db=Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    conn, cur = db
    _verify_editable_authority(cur, authority_id)

    cur.execute(
        """
        SELECT variant_id, variant_name, variant_type, notes
        FROM public.authority_variants
        WHERE variant_id = %s
          AND authority_id = %s
        FOR UPDATE
        """,
        (variant_id, authority_id),
    )

    row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant record not found for this authority.",
        )

    deleted_state = {
        "variant_name": row[1],
        "variant_type": row[2],
        "notes": row[3],
    }

    cur.execute(
        """
        DELETE FROM public.authority_variants
        WHERE variant_id = %s
          AND authority_id = %s
        RETURNING variant_id
        """,
        (variant_id, authority_id),
    )

    deleted_row = cur.fetchone()

    if not deleted_row:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The variant could not be deleted.",
        )

    _audit_or_fail(
        request=request,
        current_user=current_user,
        conn=conn,
        action_type="AUTHORITY_VARIANT_DELETE",
        target_id=str(variant_id),
        justification=payload.reason,
        diff={
            "authority_id": authority_id,
            "variant_id": variant_id,
            "deleted": deleted_state,
        },
        extra={
            "authority_id": authority_id,
            "variant_id": variant_id,
        },
        http_method="DELETE",
        target_entity="AUTHORITY_VARIANT",
        category="AUTHORITY_CONTROL",
        before=deleted_state,
        after={key: None for key in deleted_state},
    )

    conn.commit()

    return {
        "status": "success",
        "message": f"Variant ID {variant_id} deleted successfully.",
    }