import uuid
import redis

from pathlib import Path
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import HTTPException

# -------------------------
# RSA KEYS
# -------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "private.pem", "r") as f:
    PRIVATE_KEY = f.read()

with open(BASE_DIR / "public.pem", "r") as f:
    PUBLIC_KEY = f.read()

if not PRIVATE_KEY or not PUBLIC_KEY:
    raise RuntimeError("Missing RSA keys")

# -------------------------
# JWT CONFIG
# -------------------------

ISSUER = "athenaeum-api"
AUDIENCE = "athenaeum-client"
ALGORITHM = "RS256"

ACCESS_EXPIRE_MINUTES = 15
REFRESH_EXPIRE_DAYS = 7

# -------------------------
# REDIS
# -------------------------

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

# -------------------------
# TOKEN CREATION
# -------------------------

def create_token(user_data: dict, token_type: str = "access"):

    now = datetime.now(timezone.utc)
    payload = user_data.copy()

    if token_type == "access":
        expire = now + timedelta(
            minutes=ACCESS_EXPIRE_MINUTES
        )

    elif token_type == "refresh":
        expire = now + timedelta(
            days=REFRESH_EXPIRE_DAYS
        )

        payload["jti"] = str(uuid.uuid4())

    else:
        raise ValueError(
            f"Invalid token type: {token_type}"
        )

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
# REFRESH TOKEN VALIDATION
# -------------------------

def verify_refresh_token(token: str):

    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    jti = payload.get("jti")

    if not jti:
        raise HTTPException(
            status_code=401,
            detail="Missing token identifier"
        )

    if redis_client.get(f"revoked:{jti}"):

        raise HTTPException(
            status_code=401,
            detail="Token revoked"
        )

    return payload

# -------------------------
# REVOKE REFRESH TOKEN
# -------------------------

def revoke_refresh_token(token: str):

    payload = verify_refresh_token(token)

    jti = payload["jti"]

    redis_client.setex(
        f"revoked:{jti}",
        REFRESH_EXPIRE_DAYS * 86400,
        "revoked"
    )

# -------------------------
# ROTATE REFRESH TOKEN
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