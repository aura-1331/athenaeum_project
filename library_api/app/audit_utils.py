from functools import wraps
from fastapi import Request, HTTPException
from app.database import record_audit
from app.token_manager import decode_token

def audit_action(action_type: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            
            # Extract user_id from token if available
            user_id = None
            if request:
                auth = request.headers.get("Authorization")
                if auth and auth.startswith("Bearer "):
                    try:
                        payload = decode_token(auth.split(" ")[1])
                        user_id = payload.get("sub")
                    except:
                        user_id = None

            try:
                # Execute the actual route logic
                result = await func(*args, **kwargs)
                
                # If we got here, it was a success
                await record_audit(
                    user_id=user_id,
                    action_type=f"{action_type}_SUCCESS",
                    request=request,
                    details="Action completed successfully."
                )
                return result

            except Exception as e:
                # Capture the error details
                status_code = getattr(e, 'status_code', 500)
                error_detail = str(e)
                
                # Log the failure to the database
                await record_audit(
                    user_id=user_id,
                    action_type=f"{action_type}_FAILED",
                    request=request,
                    details=f"Status: {status_code}. Error: {error_detail}"
                )
                
                # Re-raise the exception so the API returns the proper error
                raise e
                
        return wrapper
    return decorator