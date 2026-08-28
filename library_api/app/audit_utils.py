from functools import wraps
from inspect import iscoroutinefunction

from fastapi import Request
from fastapi.concurrency import run_in_threadpool

from app.database import record_audit
from app.token_manager import decode_token


def audit_action(action_type: str):
    def decorator(func):

        @wraps(func)
        async def wrapper(*args, **kwargs):

            print("========== AUDIT DEBUG ==========")
            print("AUDIT args:", args)
            print("AUDIT kwargs:", kwargs)

            # ------------------------------------------------
            # FIND REQUEST
            # ------------------------------------------------
            request = next(
                (arg for arg in args if isinstance(arg, Request)),
                None
            )

            if request is None:
                request = next(
                    (
                        value
                        for value in kwargs.values()
                        if isinstance(value, Request)
                    ),
                    None
                )

            print("AUDIT request found:", request is not None)

            # ------------------------------------------------
            # GET USER ID FROM ACCESS TOKEN
            # ------------------------------------------------
            user_id = None

            if request:
                auth = request.headers.get("Authorization")

                if auth and auth.startswith("Bearer "):
                    try:
                        payload = decode_token(auth.split(" ", 1)[1])
                        user_id = payload.get("sub")
                    except Exception as e:
                        print("AUDIT TOKEN ERROR:", e)

            print("AUDIT user_id:", user_id)
            print("AUDIT action:", action_type)

            try:

                # ------------------------------------------------
                # EXECUTE ORIGINAL ROUTE
                # Supports BOTH:
                #   def route(...)
                #   async def route(...)
                # ------------------------------------------------
                if iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = await run_in_threadpool(
                        func,
                        *args,
                        **kwargs
                    )

                print("AUDIT route SUCCESS")

                await record_audit(
                    user_id=user_id,
                    action_type=f"{action_type}_SUCCESS",
                    request=request,
                    details="Action completed successfully."
                )

                print("AUDIT SUCCESS RECORDED")

                return result

            except Exception as e:

                status_code = getattr(e, "status_code", 500)
                error_detail = str(e)

                print(
                    "AUDIT route FAILED:",
                    status_code,
                    error_detail
                )

                # Only attempt audit if Request was found.
                if request is not None:
                    await record_audit(
                        user_id=user_id,
                        action_type=f"{action_type}_FAILED",
                        request=request,
                        details=(
                            f"Status: {status_code}. "
                            f"Error: {error_detail}"
                        )
                    )

                    print("AUDIT FAILURE RECORDED")

                raise

        return wrapper

    return decorator