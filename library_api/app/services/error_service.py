"""Central application error recording.

Errors are written on a separate database connection so a failed business
transaction cannot roll back the troubleshooting record with it.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import secrets
import sys
import traceback
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Optional

from app.database import get_connection

logger = logging.getLogger("athenaeum.application_errors")

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _error_reference() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"ERR-{stamp}-{secrets.token_hex(3).upper()}"


def _request_id(request) -> str:
    state = getattr(request, "state", None)
    value = getattr(state, "request_id", None)
    if value:
        return str(value)[:128]

    headers = getattr(request, "headers", {})
    header = headers.get("X-Request-ID") if headers is not None else None
    if header and _REQUEST_ID_PATTERN.fullmatch(header):
        return header
    return str(uuid.uuid4())


def _safe_json(value: Any) -> Any:
    """Return JSON-compatible data without discarding an entire context object."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        # JSON's standard does not permit NaN or infinity.
        return value if value == value and value not in (float("inf"), float("-inf")) else str(value)
    if isinstance(value, Mapping):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_json(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError, OverflowError):
        return str(value)


def _exception_details(exc: BaseException) -> dict[str, Any]:
    details: dict[str, Any] = {
        "exception_type": type(exc).__name__,
        "module": type(exc).__module__,
        "message": str(exc),
    }

    pgcode = getattr(exc, "pgcode", None)
    if pgcode:
        details["sqlstate"] = str(pgcode)

    diag = getattr(exc, "diag", None)
    if diag:
        for name in (
            "message_primary",
            "message_detail",
            "message_hint",
            "context",
            "column_name",
            "constraint_name",
            "datatype_name",
            "table_name",
            "schema_name",
        ):
            value = getattr(diag, name, None)
            if value:
                details[name] = str(value)

    return details


def _close_quietly(resource, resource_name: str, reference: str) -> None:
    if resource is None:
        return
    try:
        resource.close()
    except Exception:
        logger.warning(
            "Failed to close %s while recording application error %s",
            resource_name,
            reference,
            exc_info=True,
        )


def record_application_error(
    request,
    exc: BaseException,
    *,
    status_code: int = 500,
    operation: Optional[str] = None,
    stage: Optional[str] = None,
    user_id: Optional[Any] = None,
    role: Optional[str] = None,
    safe_context: Optional[dict[str, Any]] = None,
) -> str:
    """Persist a technical error record without exposing internals to the user."""

    reference = _error_reference()
    request_id = _request_id(request)
    exc_details = _exception_details(exc)
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    state = getattr(request, "state", None)
    operation = operation or getattr(state, "error_operation", None) or request.url.path
    stage = stage or getattr(state, "error_stage", None)

    raw_state_context = getattr(state, "error_context", None)
    state_context = raw_state_context if isinstance(raw_state_context, Mapping) else {}
    explicit_context = safe_context if isinstance(safe_context, Mapping) else {}
    combined_context = {**state_context, **explicit_context}

    if user_id is None:
        user_id = combined_context.get("user_id")
    if role is None:
        role = combined_context.get("role")

    metadata = {
        "request_id": request_id,
        "error_reference": reference,
        "operation": operation,
        "stage": stage,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "application_version": os.environ.get("ATHENAEUM_VERSION", "unknown"),
        "git_revision": os.environ.get("ATHENAEUM_GIT_SHA", "unknown"),
        "exception": exc_details,
        "safe_context": _safe_json(combined_context),
    }

    sqlstate = exc_details.get("sqlstate")
    client = getattr(request, "client", None)
    client_ip = getattr(client, "host", None)
    headers = getattr(request, "headers", {})
    user_agent = headers.get("user-agent") if headers is not None else None

    conn = None
    cur = None
    try:
        conn = get_connection(request=request)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.application_error_log (
                error_reference,
                request_id,
                occurred_at,
                user_id,
                role,
                endpoint,
                http_method,
                status_code,
                operation,
                failed_stage,
                error_type,
                sqlstate,
                error_message,
                traceback,
                client_ip,
                user_agent,
                application_version,
                git_revision,
                technical_context
            )
            VALUES (
                %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                reference,
                request_id,
                int(user_id) if str(user_id).isdigit() else None,
                role,
                request.url.path,
                request.method,
                int(status_code),
                operation,
                stage,
                exc_details.get("exception_type"),
                sqlstate,
                exc_details.get("message"),
                tb,
                client_ip,
                user_agent,
                metadata["application_version"],
                metadata["git_revision"],
                json.dumps(metadata, ensure_ascii=False, allow_nan=False),
            ),
        )
        conn.commit()
    except Exception:
        # Diagnostic persistence must never mask the original application error.
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                logger.warning(
                    "Failed to roll back diagnostic connection for error %s",
                    reference,
                    exc_info=True,
                )
        logger.exception(
            "Failed to persist application error %s: %s",
            reference,
            exc_details.get("message"),
        )
    finally:
        _close_quietly(cur, "diagnostic cursor", reference)
        _close_quietly(conn, "diagnostic connection", reference)

    logger.error(
        "Application error %s | %s %s | operation=%s stage=%s user=%s role=%s | %s",
        reference,
        request.method,
        request.url.path,
        operation,
        stage,
        user_id,
        role,
        exc_details.get("message"),
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return reference
