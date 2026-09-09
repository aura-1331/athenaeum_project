import inspect
from functools import wraps
from typing import Optional, Any
from fastapi import Request
from app.services.audit_service import log_audit_activity


def _extract_nested_param(kwargs: dict, path: Optional[str]) -> Optional[Any]:
    """
    Extracts a value from kwargs supporting dotted attribute/dict access.
    Example: 'payload.serial_no' or 'x_change_reason'
    """
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
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _handle_call(func, is_async=True, args=args, kwargs=kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return _handle_call(func, is_async=False, args=args, kwargs=kwargs)

        def _handle_call(target_fn, is_async: bool, args: tuple, kwargs: dict):
            # 1. Telemetry and Request Context
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
                    or (request.client.host if request.client else "127.0.0.1")
                )
                device_id = request.headers.get("X-Device-ID") or request.headers.get("X-Machine-Name")

            # 2. Operator Context
            current_user = kwargs.get("current_user") or {}
            user_id = current_user.get("user_id") if isinstance(current_user, dict) else getattr(current_user, "user_id", "SYSTEM")
            username = current_user.get("username") or current_user.get("name") if isinstance(current_user, dict) else getattr(current_user, "username", "SYSTEM")
            user_role = current_user.get("role") if isinstance(current_user, dict) else getattr(current_user, "role", "OPERATOR")

            # 3. Target ID Extraction
            target_id = None
            extracted_target = _extract_nested_param(kwargs, target_id_param)
            if extracted_target is not None:
                target_id = str(extracted_target)
            else:
                for fallback_key in ("serial_no", "book_id", "work_id", "id", "authority_id"):
                    if fallback_key in kwargs:
                        target_id = str(kwargs[fallback_key])
                        break

            # 4. Reason / Justification Extraction
            reason = None
            extracted_reason = _extract_nested_param(kwargs, reason_param)
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

            # 5. Route Invocation & Audit Recording
            try:
                if is_async:
                    import asyncio
                    result = target_fn(*args, **kwargs)
                    if inspect.isawaitable(result):
                        result = asyncio.run(result) if not asyncio.get_event_loop().is_running() else result
                else:
                    result = target_fn(*args, **kwargs)

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
                    request=request,
                    user_id=str(user_id),
                    username=str(username),
                    role=str(user_role),
                    category=category,
                    action_type=action_type,
                    target_entity=target_entity,
                    target_id=target_id,
                    justification=reason,
                    machine_name=device_id,
                    ip_address=ip_address,
                    extra_metadata={"status": "SUCCESS"}
                )
                return result

            except Exception as e:
                status_code = getattr(e, "status_code", 500)
                error_msg = getattr(e, "detail", str(e))
                log_audit_activity(
                    request=request,
                    user_id=str(user_id),
                    username=str(username),
                    role=str(user_role),
                    category=category,
                    action_type=action_type,
                    target_entity=target_entity,
                    target_id=target_id,
                    justification=f"Operation Failed ({status_code}): {error_msg} | Intent: {reason}",
                    machine_name=device_id,
                    ip_address=ip_address,
                    extra_metadata={"status": "FAILED", "error_code": status_code}
                )
                raise

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator