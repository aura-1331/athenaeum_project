import logging
import secrets

from fastapi import (
    Body,
    HTTPException,
    Depends,
    Request,
    Response,
    APIRouter
)


from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.audit_utils import audit_action
from app.database import get_connection
from app.token_manager import (
    create_token,
    decode_token,
    rotate_refresh_token,
    revoke_refresh_token
)

# -------------------------
# ENVIRONMENT
# -------------------------

load_dotenv()

# -------------------------
# ROUTER
# -------------------------

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# -------------------------
# RATE LIMITING
# -------------------------

limiter = Limiter(
    key_func=get_remote_address
)

# -------------------------
# OAUTH2
# -------------------------

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token"
)

# -------------------------
# PASSWORD HASHING
# -------------------------

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

# Precomputed dummy hash to prevent username enumeration timing attacks
DUMMY_HASH = pwd_context.hash("dummy_password")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

# -------------------------
# LOGGING
# -------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------
# CURRENT USER
# -------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme)
):
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail="Invalid access token"
        )

    return {
        "user_id": payload["sub"],
        "role": payload.get("role", "Guest")
    }

# -------------------------
# CSRF TOKEN
# -------------------------

def generate_csrf_token():
    return secrets.token_urlsafe(32)

# -------------------------
# LOGIN
# -------------------------

@audit_action("LOGIN_ACTION")
@limiter.limit("5/minute")
@router.post("/token")
async def login(
    request: Request,
    response: Response,
    username: str = Body(...),
    password: str = Body(...)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                user_id,
                hashed_password,
                role
            FROM users
            WHERE login_id = %s
            """,
            (username,)
        )

        row = cur.fetchone()

        stored_hash = row[1] if row else DUMMY_HASH

        if not row or not verify_password(password, stored_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        user_id = row[0]
        role = row[2]

        user_payload = {
            "sub": str(user_id),
            "role": role
        }

        access_token = create_token(
            user_payload,
            "access"
        )

        refresh_token = create_token(
            user_payload,
            "refresh"
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="Strict"
        )

        response.set_cookie(
            key="csrf_token",
            value=generate_csrf_token(),
            secure=True,
            samesite="Strict"
        )

        return {
            "access_token": access_token
        }

    finally:
        cur.close()
        conn.close()

# -------------------------
# CHECK IDENTITY
# -------------------------

@audit_action("IDENTITY_CHECK")
@limiter.limit("5/minute")
@router.post("/check-identity")
async def check_identity(
    request: Request,
    payload: dict
):
    identity_code = payload.get("identity_code")

    if (
        not identity_code
        or not identity_code.isdigit()
        or len(identity_code) != 5
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid identity format"
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                name,
                status
            FROM users
            WHERE operator_id = %s
            """,
            (f"ATH{identity_code}",)
        )

        user = cur.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Unable to verify identity"
            )

        if user[1] != "APPROVED":
            raise HTTPException(
                status_code=403,
                detail="Account inactive"
            )

        return {
            "message": "Identity verified",
            "name": user[0]
        }

    finally:
        cur.close()
        conn.close()

# -------------------------
# REFRESH TOKEN
# -------------------------

@audit_action("TOKEN_REFRESH")
@limiter.limit("5/minute")
@router.post("/refresh")
async def refresh(
    request: Request
):
    refresh_token = request.cookies.get(
        "refresh_token"
    )

    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Missing refresh token"
        )

    return rotate_refresh_token(
        refresh_token
    )

# -------------------------
# LOGOUT
# -------------------------

@audit_action("LOGOUT_ACTION")
@router.post("/logout")
async def logout(
    request: Request,
    response: Response
):
    refresh_token = request.cookies.get(
        "refresh_token"
    )

    if refresh_token:
        revoke_refresh_token(
            refresh_token
        )

    response.delete_cookie(
        "refresh_token"
    )

    response.delete_cookie(
        "csrf_token"
    )

    return {
        "message": "Logged out successfully"
    }
def require_role(allowed_roles: list[str]):
    # Normalize roles: treat 'Sys_Arch' as 'The Chief'
    def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role")
        # Map Sys_Arch to The Chief
        effective_role = "The Chief" if user_role == "Sys_Arch" else user_role
        
        if effective_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Operation requires: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker