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
from app.token_manager import redis_client
from app.token_manager import (
    create_token,
    decode_token,
    rotate_refresh_token,
    revoke_refresh_token,
    REFRESH_EXPIRE_DAYS
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
    tokenUrl="/token"
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
    request: Request,
    token: str = Depends(oauth2_scheme)
):
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail="Invalid access token"
        )

    user_id = payload["sub"]
    role = payload.get("role", "Guest")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT status
            FROM users
            WHERE user_id = %s
            """,
            (user_id,)
        )

        user = cur.fetchone()

        if not user or user[0] != "APPROVED":
            raise HTTPException(
                status_code=401,
                detail="Account inactive"
            )

    finally:
        cur.close()
        conn.close()

    # Make authenticated identity available to database/audit context.
    request.state.actor_name = user_id
    request.state.actor_role = role

    return {
        "user_id": user_id,
        "role": role
    }


# -------------------------
# CSRF TOKEN
# -------------------------

def generate_csrf_token():
    return secrets.token_urlsafe(32)


# -------------------------
# CHECK IDENTITY
# -------------------------

@router.post("/check-identity")
@limiter.limit("5/minute")
@audit_action("IDENTITY_CHECK")
async def check_identity(
    request: Request,
    payload: dict
):
    raw_code = payload.get("identity_code", "")
    identity_code = (
        raw_code.strip().upper()
        if isinstance(raw_code, str)
        else ""
    )

    if (
        not identity_code
        or not identity_code.isalnum()
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

@router.post("/refresh")
@limiter.limit("5/minute")
@audit_action("TOKEN_REFRESH")
async def refresh(
    request: Request,
    response: Response
):
    refresh_token = request.cookies.get(
        "refresh_token"
    )

    print(
        "REFRESH COOKIE RECEIVED:",
        bool(refresh_token)
    )

    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Missing refresh token"
        )

    # -------------------------
    # VALIDATE JWT
    # -------------------------

    payload = decode_token(
        refresh_token
    )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    token_id = payload.get("jti")
    user_id = payload.get("sub")

    if not token_id or not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    # -------------------------
    # VALIDATE DATABASE SESSION
    # -------------------------

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT 1
            FROM refresh_tokens
            WHERE token_id = %s
              AND user_id = %s
              AND expires_at > NOW()
            """,
            (
                token_id,
                str(user_id)
            )
        )

        session_exists = cur.fetchone()

    finally:
        cur.close()
        conn.close()

    if not session_exists:
        # A missing database session can mean either an expired/revoked
        # session or a previously rotated refresh token being replayed.
        # If Redis confirms this JTI was revoked by rotation, treat it as
        # refresh-token reuse and invalidate every refresh session for
        # this user.
        if redis_client.get(f"revoked:{token_id}"):
            reuse_conn = get_connection()
            reuse_cur = reuse_conn.cursor()

            try:
                reuse_cur.execute(
                    """
                    DELETE FROM refresh_tokens
                    WHERE user_id = %s
                    """,
                    (str(user_id),)
                )
                reuse_conn.commit()

            finally:
                reuse_cur.close()
                reuse_conn.close()

            raise HTTPException(
                status_code=401,
                detail="Refresh token reuse detected"
            )

        raise HTTPException(
            status_code=401,
            detail="Refresh session revoked"
        )

    # -------------------------
    # ROTATE REFRESH TOKEN
    # -------------------------

    result = rotate_refresh_token(
        refresh_token
    )

    # -------------------------
    # STORE NEW REFRESH SESSION
    # -------------------------

    new_refresh_token = result["refresh_token"]

    new_payload = decode_token(
        new_refresh_token
    )

    new_jti = new_payload["jti"]

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Remove the old session record because
        # the old refresh token has now been rotated.
        cur.execute(
            """
            DELETE FROM refresh_tokens
            WHERE token_id = %s
            """,
            (token_id,)
        )

        # Store the newly issued refresh token.
        cur.execute(
            """
            INSERT INTO refresh_tokens (
                token_id,
                user_id,
                expires_at
            )
            VALUES (
                %s,
                %s,
                NOW() + INTERVAL '7 days'
            )
            """,
            (
                new_jti,
                str(user_id)
            )
        )

        conn.commit()

    finally:
        cur.close()
        conn.close()

    # -------------------------
    # SET ROTATED COOKIE
    # -------------------------

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,
        samesite="Strict",
        max_age=REFRESH_EXPIRE_DAYS * 86400,
        path="/"
    )

    return {
        "access_token": result["access_token"],
        "token_type": result["token_type"],
    }


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
        try:
            payload = decode_token(
                refresh_token
            )

            token_id = payload.get("jti")
            user_id = payload.get("sub")

            if token_id:
                revoke_refresh_token(
                    refresh_token
                )

                conn = get_connection()
                cur = conn.cursor()

                try:
                    cur.execute(
                        """
                        DELETE FROM refresh_tokens
                        WHERE token_id = %s
                          AND user_id = %s
                        """,
                        (
                            token_id,
                            str(user_id)
                        )
                    )

                    conn.commit()

                finally:
                    cur.close()
                    conn.close()

        except HTTPException:
            # Even if the refresh token is already invalid,
            # continue clearing the browser cookies.
            pass

    response.delete_cookie(
        "refresh_token"
    )

    response.delete_cookie(
        "csrf_token"
    )

    return {
        "message": "Logged out successfully"
    }


# -------------------------
# ROLE CHECK
# -------------------------

def require_role(
    allowed_roles: list[str]
):
    # Normalize roles: treat 'Sys_Arch' as 'The Chief'
    def role_checker(
        current_user: dict = Depends(get_current_user)
    ):
        user_role = current_user.get("role")

        # Map Sys_Arch to The Chief
        effective_role = (
            "The Chief"
            if user_role == "Sys_Arch"
            else user_role
        )

        if effective_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Operation requires: "
                    f"{', '.join(allowed_roles)}"
                )
            )

        return current_user

    return role_checker