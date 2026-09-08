from functools import wraps
from inspect import iscoroutinefunction
from typing import Optional
from fastapi import Request
from fastapi.concurrency import run_in_threadpool

from app.token_manager import decode_token
from app.services.audit_service import log_audit_activity


def audit_action(
    action_type: str,
    category: str = "CATALOG_API",
    target_entity: Optional[str] = None,
    target_id_param: Optional[str] = None,
    reason_param: Optional[str] = None,
):
    """
    Decorator that intercepts route execution, extracts caller identity,
    dynamic target IDs, and justification reasons, then writes an immutable
    entry into audit_activities.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 1. Locate Request object
            request = next(
                (arg for arg in args if isinstance(arg, Request)),
                None
            )
            if request is None:
                request = next(
                    (v for v in kwargs.values() if isinstance(v, Request)),
                    None
                )

            # 2. Extract user metadata from Bearer JWT
            user_id = "ANONYMOUS"
            username = "Anonymous User"
            role = "GUEST"
            designation = "External"

            if request:
                auth = request.headers.get("Authorization")
                if auth and auth.startswith("Bearer "):
                    try:
                        payload = decode_token(auth.split(" ", 1)[1])
                        user_id = str(payload.get("sub") or payload.get("user_id") or "SYSTEM")
                        username = payload.get("user_name") or payload.get("username") or "Authenticated User"
                        role = payload.get("role") or "OPERATOR"
                        designation = payload.get("designation") or "Staff"
                    except Exception as e:
                        print(f"[AUDIT] Token decode error: {e}")

            # 3. Dynamic target_id extraction
            target_id = None
            if target_id_param and target_id_param in kwargs:
                target_id = str(kwargs[target_id_param])
            else:
                # Common path/query param names used across endpoints
                id_candidates = ("book_id", "work_id", "serial_no", "item_id", "id", "user_id")
                for key in id_candidates:
                    if key in kwargs and kwargs[key] is not None:
                        target_id = str(kwargs[key])
                        break

            # If still not found, check path_params on the request
            if target_id is None and request and hasattr(request, "path_params"):
                for key in ("book_id", "work_id", "serial_no", "item_id", "id", "user_id"):
                    if key in request.path_params:
                        target_id = str(request.path_params[key])
                        break

            # 4. Dynamic justification/reason extraction
            reason = None
            if reason_param and reason_param in kwargs:
                reason = str(kwargs[reason_param])
            else:
                reason = kwargs.get("reason") or kwargs.get("justification") or kwargs.get("change_reason")
            
            # Check query params if not found in kwargs
            if not reason and request and hasattr(request, "query_params"):
                reason = request.query_params.get("reason") or request.query_params.get("justification")

            success_justification = reason if reason else "Standard route execution succeeded."

            # 5. Execute route
            try:
                if iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = await run_in_threadpool(func, *args, **kwargs)

                # Record SUCCESS with extracted target_id and reason
                log_audit_activity(
                    request=request,
                    user_id=user_id,
                    username=username,
                    role=role,
                    designation=designation,
                    category=category,
                    action_type=f"{action_type}_SUCCESS",
                    target_entity=target_entity,
                    target_id=target_id,
                    justification=success_justification,
                )

                return result

            except Exception as e:
                status_code = getattr(e, "status_code", 500)
                error_msg = str(e)
                failure_justification = f"Route failed ({status_code}): {error_msg}"
                if reason:
                    failure_justification = f"{reason} | {failure_justification}"

                # Record FAILURE
                log_audit_activity(
                    request=request,
                    user_id=user_id,
                    username=username,
                    role=role,
                    designation=designation,
                    category=category,
                    action_type=f"{action_type}_FAILED",
                    target_entity=target_entity,
                    target_id=target_id,
                    justification=failure_justification,
                )
                raise

        return wrapper
    return decorator