import inspect
from functools import wraps
from typing import Optional, Any

from fastapi import Request

from app.services.audit_service import log_audit_activity


def _extract_nested_param(
    kwargs: dict,
    path: Optional[str]
) -> Optional[Any]:
    if not path:
        return None

    parts = path.split(".")
    val = kwargs.get(parts[0])

    for part in parts[1:]:
        if val is None:
            return None

        if isinstance(val, dict):
            val = val.get(part)
        else:
            val = getattr(val, part, None)

    return val


def audit_action(
    action_type: str,
    category: str = "CATALOG_API",
    target_entity: Optional[str] = None,
    target_id_param: Optional[str] = None,
    reason_param: Optional[str] = None,
):
    """
    Decorator for intercepting route calls, extracting compliance metadata,
    and recording entries in the audit ledger.

    Supports both synchronous and asynchronous route functions without
    creating or manipulating event loops.
    """

    def decorator(func):

        def _build_context(args: tuple, kwargs: dict):
            request: Optional[Request] = kwargs.get("request")

            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            ip_address = None
            device_id = None

            if request:
                ip_address = (
                    request.headers.get("X-Forwarded-For")
                    or request.headers.get("X-IP-Address")
                    or (
                        request.client.host
                        if request.client
                        else "127.0.0.1"
                    )
                )

                device_id = (
                    request.headers.get("X-Device-ID")
                    or request.headers.get("X-Machine-Name")
                )

            current_user = kwargs.get("current_user") or {}

            if isinstance(current_user, dict):
                user_id = current_user.get("user_id")
                username = (
                    current_user.get("username")
                    or current_user.get("name")
                )
                user_role = current_user.get("role")
            else:
                user_id = getattr(current_user, "user_id", "SYSTEM")
                username = getattr(
                    current_user,
                    "username",
                    "SYSTEM"
                )
                user_role = getattr(
                    current_user,
                    "role",
                    "OPERATOR"
                )

            if user_id is None:
                user_id = "SYSTEM"

            if username is None:
                username = "SYSTEM"

            if user_role is None:
                user_role = "OPERATOR"

            target_id = None

            extracted_target = _extract_nested_param(
                kwargs,
                target_id_param
            )

            if extracted_target is not None:
                target_id = str(extracted_target)
            else:
                for fallback_key in (
                    "serial_no",
                    "book_id",
                    "work_id",
                    "id",
                    "authority_id",
                ):
                    if fallback_key in kwargs:
                        target_id = str(kwargs[fallback_key])
                        break

            reason = None

            extracted_reason = _extract_nested_param(
                kwargs,
                reason_param
            )

            if extracted_reason is not None:
                reason = str(extracted_reason)
            else:
                reason = (
                    kwargs.get("reason")
                    or kwargs.get("justification")
                    or kwargs.get("change_reason")
                    or kwargs.get("x_change_reason")
                    or "Standard operational execution"
                )

            return {
                "request": request,
                "user_id": str(user_id),
                "username": str(username),
                "role": str(user_role),
                "target_id": target_id,
                "reason": reason,
                "machine_name": device_id,
                "ip_address": ip_address,
            }

        def _write_success_audit(
            context: dict,
            result: Any,
        ):
            target_id = context["target_id"]

            if not target_id and isinstance(result, dict):
                created_id = (
                    result.get("work_id")
                    or result.get("serial_no")
                    or result.get("location_id")
                    or result.get("authority_id")
                    or result.get("id")
                )

                if created_id is not None:
                    target_id = str(created_id)

            log_audit_activity(
                request=context["request"],
                user_id=context["user_id"],
                username=context["username"],
                role=context["role"],
                category=category,
                action_type=action_type,
                target_entity=target_entity,
                target_id=target_id,
                justification=context["reason"],
                machine_name=context["machine_name"],
                ip_address=context["ip_address"],
                extra_metadata={"status": "SUCCESS"},
            )

        def _write_failure_audit(
            context: dict,
            exc: Exception,
        ):
            status_code = getattr(exc, "status_code", 500)
            error_msg = getattr(exc, "detail", str(exc))

            log_audit_activity(
                request=context["request"],
                user_id=context["user_id"],
                username=context["username"],
                role=context["role"],
                category=category,
                action_type=action_type,
                target_entity=target_entity,
                target_id=context["target_id"],
                justification=(
                    f"Operation Failed ({status_code}): "
                    f"{error_msg} | Intent: {context['reason']}"
                ),
                machine_name=context["machine_name"],
                ip_address=context["ip_address"],
                extra_metadata={
                    "status": "FAILED",
                    "error_code": status_code,
                },
            )

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                context = _build_context(args, kwargs)

                try:
                    result = await func(*args, **kwargs)

                    _write_success_audit(
                        context,
                        result,
                    )

                    return result

                except Exception as exc:
                    _write_failure_audit(
                        context,
                        exc,
                    )
                    raise

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = _build_context(args, kwargs)

            try:
                result = func(*args, **kwargs)

                _write_success_audit(
                    context,
                    result,
                )

                return result

            except Exception as exc:
                _write_failure_audit(
                    context,
                    exc,
                )
                raise

        return sync_wrapper

    return decorator
