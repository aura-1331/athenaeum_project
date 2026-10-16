"""Generic FastAPI endpoint auditing.

This decorator records endpoint outcomes through the shared audit-ledger helper.
The audit write uses its own transaction because the decorator cannot reliably
own the route handler's database transaction. Mutation routes that require the
business change and its audit record to be atomic should write their audit entry
inside the route transaction and should not also use this decorator.
"""

from __future__ import annotations

import inspect
import logging
from functools import wraps
from typing import Any, Optional

from fastapi import Request
from starlette.concurrency import run_in_threadpool

from app.database import get_connection
from app.routers.review_utils import _audit_ledger
from app.services.audit_service import log_audit_activity

logger = logging.getLogger("athenaeum.audit_decorator")


def _extract_nested_param(kwargs: dict, path: Optional[str]) -> Optional[Any]:
    if not path:
        return None

    parts = path.split(".")
    value = kwargs.get(parts[0])

    for part in parts[1:]:
        if value is None:
            return None
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = getattr(value, part, None)

    return value


def _build_context(args: tuple, kwargs: dict) -> dict:
    request: Optional[Request] = kwargs.get("request")
    if request is None:
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

    current_user = kwargs.get("current_user") or {}
    if isinstance(current_user, dict):
        user_id = current_user.get("user_id", "SYSTEM")
        username = current_user.get("username") or current_user.get("name") or "SYSTEM"
        role = current_user.get("role") or "OPERATOR"
        designation = current_user.get("designation") or role
    else:
        user_id = getattr(current_user, "user_id", "SYSTEM")
        username = getattr(current_user, "username", "SYSTEM")
        role = getattr(current_user, "role", "OPERATOR")
        designation = getattr(current_user, "designation", None) or role

    # Use common entity IDs as a fallback; explicit decorator configuration
    # takes precedence later when the event is written.
    target_id = None
    for fallback_key in (
        "serial_no",
        "book_id",
        "work_id",
        "item_id",
        "location_id",
        "loan_id",
        "fine_id",
        "authority_id",
        "variant_id",
        "incident_id",
        "id",
    ):
        if kwargs.get(fallback_key) is not None:
            target_id = str(kwargs[fallback_key])
            break

    reason = (
        kwargs.get("reason")
        or kwargs.get("justification")
        or kwargs.get("change_reason")
        or kwargs.get("x_change_reason")
        or "Standard operational execution"
    )
    if not isinstance(reason, str):
        reason = str(reason)

    return {
        "request": request,
        "user_id": str(user_id if user_id is not None else "SYSTEM"),
        "username": str(username if username is not None else "SYSTEM"),
        "role": str(role if role is not None else "OPERATOR"),
        "designation": str(designation if designation is not None else "OPERATOR"),
        "target_id": target_id,
        "reason": reason,
    }


def _resolve_target_id(context: dict, kwargs: dict, target_id_param: Optional[str], result: Any) -> Optional[str]:
    extracted = _extract_nested_param(kwargs, target_id_param)
    if extracted is not None:
        return str(extracted)

    if context.get("target_id") is not None:
        return str(context["target_id"])

    if isinstance(result, dict):
        for key in (
            "work_id",
            "serial_no",
            "item_id",
            "location_id",
            "loan_id",
            "fine_id",
            "authority_id",
            "variant_id",
            "incident_id",
            "id",
        ):
            if result.get(key) is not None:
                return str(result[key])

    request = context.get("request")
    return request.url.path if request is not None else None


def _write_audit_event(
    *,
    context: dict,
    action_type: str,
    category: str,
    target_entity: Optional[str],
    target_id: Optional[str],
    outcome: str,
    status_code: Optional[int] = None,
    error_type: Optional[str] = None,
) -> bool:
    """Best-effort audit write; diagnostics must not mask route outcomes."""
    request: Optional[Request] = context.get("request")
    if outcome == "SUCCESS":
        justification = context["reason"]
    else:
        justification = (
            f"Operation failed (HTTP {status_code or 500}); "
            f"exception_type={error_type or 'Exception'}; "
            f"intent={context['reason']}"
        )

    extra = {
        "status": outcome,
        "audit_source": "audit_action",
    }
    if status_code is not None:
        extra["status_code"] = status_code
    if error_type:
        extra["error_type"] = error_type

    # Normally a FastAPI route supplies Request, allowing all generic events to
    # pass through the shared helper. Keep a direct-service fallback for use in
    # tests or non-request invocations of decorated functions.
    if request is None:
        try:
            ok = log_audit_activity(
                request=None,
                user_id=context["user_id"],
                username=context["username"],
                role=context["role"],
                designation=context["designation"],
                category=category,
                action_type=action_type,
                target_entity=target_entity or "API_ENDPOINT",
                target_id=target_id,
                justification=justification,
                endpoint=None,
                http_method=None,
                diff_payload={"outcome": outcome},
                extra_metadata=extra,
            )
            if not ok:
                logger.error("Audit ledger write returned false for action %s", action_type)
            return bool(ok)
        except Exception:
            logger.exception("Audit ledger write failed for action %s", action_type)
            return False

    conn = None
    try:
        conn = get_connection(request=request)
        _audit_ledger(
            request=request,
            current_user={
                "user_id": context["user_id"],
                "username": context["username"],
                "role": context["role"],
                "designation": context["designation"],
            },
            conn=conn,
            action_type=action_type,
            target_id=target_id if target_id is not None else request.url.path,
            justification=justification,
            diff={"outcome": outcome},
            extra=extra,
            http_method=request.method,
            target_entity=target_entity or "API_ENDPOINT",
            category=category,
        )
        conn.commit()
        return True
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                logger.exception("Rollback failed after audit write failure")
        logger.exception("Audit ledger write failed for action %s", action_type)
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                logger.exception("Failed to close audit connection")


def audit_action(
    action_type: str,
    category: str = "CATALOG_API",
    target_entity: Optional[str] = None,
    target_id_param: Optional[str] = None,
    reason_param: Optional[str] = None,
):
    """Audit success and failure outcomes for sync or async route functions.

    This is suitable for endpoint-access telemetry and routes whose business
    transaction is managed elsewhere. For mutation operations that require
    atomicity between data changes and the audit record, write the ledger event
    within the route's existing transaction instead of decorating that route.
    """

    def decorator(func):
        def build_context(args: tuple, kwargs: dict) -> dict:
            context = _build_context(args, kwargs)
            extracted_reason = _extract_nested_param(kwargs, reason_param)
            if extracted_reason is not None:
                context["reason"] = str(extracted_reason)
            return context

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                context = build_context(args, kwargs)
                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:
                    status_code = getattr(exc, "status_code", 500)
                    await run_in_threadpool(
                        _write_audit_event,
                        context=context,
                        action_type=action_type,
                        category=category,
                        target_entity=target_entity,
                        target_id=_resolve_target_id(context, kwargs, target_id_param, None),
                        outcome="FAILED",
                        status_code=int(status_code) if isinstance(status_code, int) else 500,
                        error_type=type(exc).__name__,
                    )
                    raise

                await run_in_threadpool(
                    _write_audit_event,
                    context=context,
                    action_type=action_type,
                    category=category,
                    target_entity=target_entity,
                    target_id=_resolve_target_id(context, kwargs, target_id_param, result),
                    outcome="SUCCESS",
                )
                return result

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = build_context(args, kwargs)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                status_code = getattr(exc, "status_code", 500)
                _write_audit_event(
                    context=context,
                    action_type=action_type,
                    category=category,
                    target_entity=target_entity,
                    target_id=_resolve_target_id(context, kwargs, target_id_param, None),
                    outcome="FAILED",
                    status_code=int(status_code) if isinstance(status_code, int) else 500,
                    error_type=type(exc).__name__,
                )
                raise

            _write_audit_event(
                context=context,
                action_type=action_type,
                category=category,
                target_entity=target_entity,
                target_id=_resolve_target_id(context, kwargs, target_id_param, result),
                outcome="SUCCESS",
            )
            return result

        return sync_wrapper

    return decorator
