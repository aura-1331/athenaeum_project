import os
import uuid
from datetime import datetime, timedelta, timezone # Added timezone
from jose import JWTError, jwt
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in environment variables")

ALGORITHM = "HS256"

def create_token(user_data: dict, token_type: str = "access"):
    to_encode = user_data.copy()

    now = datetime.now(timezone.utc)
    
    if token_type == "access":
        expire = now + timedelta(minutes=30)
    else:  # refresh token
        expire = now + timedelta(days=7)
        to_encode["jti"] = str(uuid.uuid4())  # 🔥 THIS LINE FIXES YOUR ERROR

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": token_type,
        "iss": "athenaeum-api"
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(
    token, 
    SECRET_KEY, 
    algorithms=[ALGORITHM], 
    options={"leeway": 30}  # 👈 Add 30 seconds of grace period
)
        print("🔍 TOKEN PAYLOAD:", payload)
        # 🔒 Security Validations
        if payload.get("iss") != "athenaeum-api":
            raise HTTPException(status_code=401, detail="Invalid token issuer")

        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload.get("sub")
        role = payload.get("role", "Guest")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing subject")
        if role not in ["Sys_Arch", "Archivist", "Guest"]:
            role = "Guest"
        return {"user_id": user_id, "role": role}

    except JWTError as e:
        print("❌ JWT ERROR:", str(e))
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")