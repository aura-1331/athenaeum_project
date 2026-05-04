import asyncio
import platform

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware



import time
import os

from fastapi.responses import Response
from pdf.pdf_generator import generate_pdf
from jose import jwt, JWTError
from app.auth import SECRET_KEY, ALGORITHM
from datetime import datetime, timezone
from app.database import get_connection, record_audit
from app.auth import create_token, get_current_user
from app.utils.security import hash_password, verify_password, is_password_strong
from app.routers import (
    catalogue, items, search, status_audit, dashboard,
    accessions, health, reports, bulk, analytics, operations,
    print as print_router,
    circulation, admin_config, profile
)

class RefreshRequest(BaseModel):
    refresh_token: str

app = FastAPI(
    title="Athenaeum Library API",
    swagger_ui_parameters={"deepLinking": True},
    components={
        "securitySchemes": {
            "OAuth2PasswordBearer": {
                "type": "oauth2",
                "flows": {
                    "password": {
                        "tokenUrl": "token",
                        "scopes": {}
                    }
                }
            }
        }
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.middleware("http")
async def request_logger(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    print(f"{request.method} {request.url.path} {response.status_code} {process_time:.2f}ms")
    return response


def normalize_role(role: str) -> str:
    role = role.lower()

    if "architect" in role:
        return "Sys_Arch"
    if "archivist" in role:
        return "Archivist"
    if "guest" in role:
        return "Guest"

    return "Guest"
@app.post("/token", tags=["Security"])
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_connection()
    cur = conn.cursor()
    try:
        query = """
            SELECT user_id, hashed_password, role, status 
            FROM users 
            WHERE email = %s OR login_id = %s
        """
        cur.execute(query, (form_data.username, form_data.username))
        user = cur.fetchone()

        if not user or not verify_password(form_data.password, user[1]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if user[3] != 'APPROVED':
            raise HTTPException(status_code=403, detail=f"Access denied: Account is {user[3]}")

        await record_audit(
        user_id=user[0], 
        action_type="LOGIN", 
        request=request, 
        details="System access granted via secure handshake.",
        valid_reason="LOGIN_SUCCESS"   # 🔥 ADD THIS
        )
        normalized_role = normalize_role(user[2])
        # ✅ create tokens
        access_token = create_token(
            user_data={"sub": str(user[0]), "role": normalized_role},
            token_type="access"
        )

        refresh_token = create_token(
            user_data={"sub": str(user[0]), "role": normalized_role},
            token_type="refresh"
        )

        # 🔥 decode refresh token
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload["jti"]
        expires = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        # 🔥 store in DB
        cur.execute(
            "INSERT INTO refresh_tokens (token_id, user_id, expires_at) VALUES (%s, %s, %s)",
            (jti, payload["sub"], expires)
        )
        conn.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "role": normalized_role
        }

    finally:
        cur.close()
        conn.close()


@app.post("/refresh", tags=["Security"])
async def refresh_token(req: RefreshRequest):
    conn = get_connection()
    cur = conn.cursor()
    try:
        payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        jti = payload.get("jti")

        # 🔍 check DB
        cur.execute(
            "SELECT user_id, expires_at FROM refresh_tokens WHERE token_id = %s",
            (jti,)
        )
        token = cur.fetchone()

        if not token:
            raise HTTPException(status_code=401, detail="Token revoked")

        # ⏳ check expiry
        if token[1].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Token expired")

        # ✅ create new access token
        new_access = create_token(
    {
        "sub": payload["sub"],
        "role": normalize_role(payload.get("role", "Guest"))
    },
    token_type="access"
    )

        return {"access_token": new_access}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    finally:
        cur.close()
        conn.close()

@app.post("/admin/create-user", tags=["Admin Operations"])
async def admin_create_user(
    name: str, email: str, login_id: str, role: str, password: str,
    current_user: dict = Depends(get_current_user) 
):
    admin_role = current_user.get("role")
    if admin_role == "Guest":
        raise HTTPException(status_code=403, detail="Access Denied.")
    
    if admin_role == "Archivist" and role in ["Sys_Arch", "Archivist"]:
        raise HTTPException(status_code=403, detail="Archivists can only create GUEST accounts.")

    if not is_password_strong(password):
        raise HTTPException(status_code=400, detail="Password too weak.")

    conn = get_connection()
    cur = conn.cursor()
    try:
        hashed = hash_password(password)
        cur.execute(
            "INSERT INTO users (name, email, login_id, role, status, hashed_password) VALUES (%s, %s, %s, %s, 'APPROVED', %s)",
            (name, email, login_id, role, hashed)
        )
        conn.commit()
        return {"status": "success", "message": f"User {login_id} created."}
    finally:
        cur.close()
        conn.close()
        
@app.post("/logout", tags=["Security"])
async def logout(req: RefreshRequest):
    conn = get_connection()
    cur = conn.cursor()
    try:
        payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")

        cur.execute("DELETE FROM refresh_tokens WHERE token_id = %s", (jti,))
        conn.commit()

        return {"message": "Logged out successfully"}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    finally:
        cur.close()
        conn.close()
       



app.include_router(print_router.router)
app.include_router(health.router)
app.include_router(catalogue.router)
app.include_router(items.router, dependencies=[Depends(get_current_user)])
app.include_router(search.router, dependencies=[Depends(get_current_user)])
app.include_router(circulation.router, dependencies=[Depends(get_current_user)])
app.include_router(dashboard.router, dependencies=[Depends(get_current_user)])
app.include_router(profile.router, dependencies=[Depends(get_current_user)])
app.include_router(operations.router, dependencies=[Depends(get_current_user)])
app.include_router(status_audit.router, dependencies=[Depends(get_current_user)])
app.include_router(admin_config.router, dependencies=[Depends(get_current_user)])