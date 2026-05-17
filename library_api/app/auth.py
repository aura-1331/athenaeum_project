import os
import uuid
import secrets
import redis
import logging
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Request,
    Response,
    status
)
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

# -------------------------
# CONFIG
# -------------------------
with open("private.pem", "r") as f:
    PRIVATE_KEY = f.read()

with open("public.pem", "r") as f:
    PUBLIC_KEY = f.read()

if not PRIVATE_KEY or not PUBLIC_KEY:
    raise RuntimeError("Missing RSA keys")

ISSUER = "athenaeum-api"
AUDIENCE = "athenaeum-client"

ACCESS_EXPIRE_MINUTES = 15
REFRESH_EXPIRE_DAYS = 7

ALGORITHM = "RS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# -------------------------
# REDIS
# -------------------------
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

# -------------------------
# PASSWORD HASHING
# -------------------------
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

# -------------------------
# LOGGING
# -------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# -------------------------
# FASTAPI APP
# -------------------------
app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# -------------------------
# TOKEN CREATION
# -------------------------
def create_token(user_data: dict, token_type="access"):
    now = datetime.now(timezone.utc)

    payload = user_data.copy()

    if token_type == "access":
        expire = now + timedelta(minutes=ACCESS_EXPIRE_MINUTES)

    elif token_type == "refresh":
        expire = now + timedelta(days=REFRESH_EXPIRE_DAYS)
        payload["jti"] = str(uuid.uuid4())

    else:
        raise ValueError("Invalid token type")

    payload.update({
        "exp": expire,
        "iat": now,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "type": token_type
    })

    return jwt.encode(
        payload,
        PRIVATE_KEY,
        algorithm=ALGORITHM
    )

# -------------------------
# TOKEN VALIDATION
# -------------------------
def decode_token(token: str):
    try:
        payload = jwt.decode(
            token,
            PUBLIC_KEY,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE
        )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

# -------------------------
# CURRENT USER
# -------------------------
def get_current_user(
    token: str = Depends(oauth2_scheme)
):
    payload = decode_token(token)

    if payload["type"] != "access":
        raise HTTPException(
            status_code=401,
            detail="Invalid access token"
        )

    return {
        "user_id": payload["sub"],
        "role": payload.get("role", "Guest")
    }

# -------------------------
# REFRESH VALIDATION
# -------------------------
def verify_refresh_token(token: str):
    payload = decode_token(token)

    if payload["type"] != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    jti = payload.get("jti")

    if redis_client.get(f"revoked:{jti}"):
        raise HTTPException(
            status_code=401,
            detail="Token revoked"
        )

    return payload

# -------------------------
# REVOKE TOKEN
# -------------------------
def revoke_refresh_token(token: str):
    payload = verify_refresh_token(token)
    jti = payload["jti"]

    ttl = REFRESH_EXPIRE_DAYS * 86400

    redis_client.setex(
        f"revoked:{jti}",
        ttl,
        "revoked"
    )

# -------------------------
# ROTATE TOKENS
# -------------------------
def rotate_refresh_token(token: str):
    payload = verify_refresh_token(token)

    revoke_refresh_token(token)

    new_payload = {
        "sub": payload["sub"],
        "role": payload.get("role", "Guest")
    }

    return {
        "access_token": create_token(
            new_payload,
            "access"
        ),
        "refresh_token": create_token(
            new_payload,
            "refresh"
        )
    }

# -------------------------
# CSRF TOKEN
# -------------------------
def generate_csrf_token():
    return secrets.token_urlsafe(32)

# -------------------------
# LOGIN ROUTE
# -------------------------
@app.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    username: str,
    password: str
):
    # Replace with DB lookup
    stored_hash = hash_password("admin123")

    if not verify_password(password, stored_hash):
        logger.warning("Failed login attempt")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    user_payload = {
        "sub": username,
        "role": "Sys_Arch"
    }

    access_token = create_token(
        user_payload,
        "access"
    )

    refresh_token = create_token(
        user_payload,
        "refresh"
    )

    csrf_token = generate_csrf_token()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="Strict"
    )

    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        secure=True,
        samesite="Strict"
    )

    return {
        "access_token": access_token
    }

# -------------------------
# REFRESH ROUTE
# -------------------------
@app.post("/refresh")
def refresh(request: Request):
    refresh_token = request.cookies.get(
        "refresh_token"
    )

    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Missing refresh token"
        )

    return rotate_refresh_token(refresh_token)

# -------------------------
# LOGOUT ROUTE
# -------------------------
@app.post("/logout")
def logout(
    request: Request,
    response: Response
):
    refresh_token = request.cookies.get(
        "refresh_token"
    )

    if refresh_token:
        revoke_refresh_token(refresh_token)

    response.delete_cookie("refresh_token")
    response.delete_cookie("csrf_token")

    return {
        "message": "Logged out successfully"
    }