import asyncio
import platform
import time
import pyotp
import qrcode
import io
import base64
import secrets
import string

from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError

from pdf.pdf_generator import generate_pdf
from app.database import get_connection, record_audit
from app.auth import (
    PUBLIC_KEY,
    ALGORITHM,
    create_token,
    get_current_user
)

from app.utils.security import (
    hash_password,
    verify_password,
    is_password_strong
)

from app.routers import (
    catalogue,
    items,
    search,
    status_audit,
    dashboard,
    incidents,
    health,
    reports,
    locations,
    analytics,
    operations,
    print as print_router,
    circulation,
    admin_config,
    profile
)

# ----------------------------
# Windows Fix
# ----------------------------
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )


# ----------------------------
# Request Models
# ----------------------------
class RefreshRequest(BaseModel):
    refresh_token: str


class Verify2FARequest(BaseModel):
    token: str

class AccessRequestModel(BaseModel):
    full_name: str
    email: EmailStr
    organization: str
    purpose: str
    requested_role: str
    temporary_access: bool = False
    temporary_expiry: datetime | None = None

class KeeperRecommendationModel(BaseModel):
    recommendation: str
    notes: str | None = None

class ChiefDecisionModel(BaseModel):
    decision: str
    notes: str | None = None    

# ----------------------------
# App Init
# ----------------------------
app = FastAPI(
    title="Athenaeum Library API",
    swagger_ui_parameters={"deepLinking": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ----------------------------
# Chief Review / Final Decision
# ----------------------------

@app.post("/chief/decide-request/{request_id}")
async def chief_decide_request(
    request_id: int,
    req: ChiefDecisionModel,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "The Chief":
        raise HTTPException(
            status_code=403,
            detail="Only The Chief can make final decisions."
        )

    if req.decision not in ["APPROVE", "REJECT"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid decision."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
          SELECT full_name,
            email,
            requested_role,
            temporary_access,
            temporary_expiry,
            status
FROM access_requests
WHERE request_id=%s
            """,
            (request_id,)
        )

        request_data = cur.fetchone()

        if not request_data:
            raise HTTPException(
                status_code=404,
                detail="Request not found"
            )

        if request_data[5] in ["APPROVE", "REJECT"]:
            raise HTTPException(
                status_code=400,
                detail="Request already processed"
            )

        temp_password = None

        if req.decision == "APPROVE":
            # Generate secure temporary password
            alphabet = (
                string.ascii_letters +
                string.digits +
                "!@#$%"
            )

            temp_password = "".join(
                secrets.choice(alphabet)
                for _ in range(12)
            )
            operator_id = generate_operator_id(request_data[2])
            hashed = hash_password(temp_password)

            # Generate login_id from email
            login_id = request_data[1].split("@")[0]

            # Prevent duplicate login IDs
            cur.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE login_id=%s
                """,
                (login_id,)
            )

            existing_login = cur.fetchone()[0]

            if existing_login > 0:
                login_id = f"{login_id}{request_id}"

        cur.execute(
            """
            INSERT INTO users (
                name,
                email,
                login_id,
                operator_id,
                role,
                status,
                hashed_password,
                expires_at
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                'APPROVED',
                %s,
                %s
            )
            """,
            (
                request_data[0],   # full_name
                request_data[1],   # email
                login_id,
                operator_id,
                request_data[2],   # requested role
                hashed,
                request_data[4]    # temporary expiry
            )
        )

        # Update request status
        cur.execute(
            """
            UPDATE access_requests
            SET chief_decision=%s,
                chief_notes=%s,
                status=%s
            WHERE request_id=%s
            """,
            (
                req.decision,
                req.notes,
                req.decision,
                request_id
            )
        )

        conn.commit()

        response = {
            "message": f"Request {req.decision.lower()}d successfully."
        }

        if req.decision == "APPROVE":
            response["temporary_password"] = temp_password
            response["operator_id"] = operator_id
        return response

    finally:
        cur.close()
        conn.close()

# -------------------------
# REVOKE USER
# -------------------------
@app.post("/chief/revoke-user/{user_id}")
async def revoke_user(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "The Chief":
        raise HTTPException(
            status_code=403,
            detail="Only The Chief can revoke users."
        )

    if user_id == int(current_user["user_id"]):
        raise HTTPException(
            status_code=400,
            detail="Chief cannot revoke themselves."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            UPDATE users
            SET status='REVOKED'
            WHERE user_id=%s
            """,
            (user_id,)
        )

        conn.commit()

        return {
            "message": "User access revoked."
        }

    finally:
        cur.close()
        conn.close()     

#-----------------------------
# Keeper review recommendation 
#-----------------------------


@app.post("/keeper/recommend-request/{request_id}")
async def keeper_recommend_request(
    request_id: int,
    req: KeeperRecommendationModel,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "The Keeper":
        raise HTTPException(
            status_code=403,
            detail="Only The Keeper can recommend requests."
        )

    if req.recommendation not in ["APPROVE", "REJECT"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid recommendation."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            UPDATE access_requests
            SET keeper_recommendation=%s,
                keeper_notes=%s,
                status='KEEPER_REVIEWED'
            WHERE request_id=%s
            """,
            (
                req.recommendation,
                req.notes,
                request_id
            )
        )

        conn.commit()

        return {
            "message": "Recommendation submitted."
        }

    finally:
        cur.close()
        conn.close()

# ----------------------------
# Request Logger
# ----------------------------
@app.middleware("http")
async def request_logger(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000

    print(
        f"{request.method} "
        f"{request.url.path} "
        f"{response.status_code} "
        f"{process_time:.2f}ms"
    )

    return response


# ----------------------------
# Role Normalization
# ----------------------------
def normalize_role(role: str) -> str:
    role = role.lower().strip()

    if role == "the chief" or role == "chief":
        return "The Chief"

    if role == "the keeper" or role == "keeper":
        return "The Keeper"

    if role == "the seeker" or role == "seeker":
        return "The Seeker"

    if role == "temporary seeker":
        return "Temporary Seeker"

    return "INVALID"
# ----------------------------
# OPERATOR ID GENERATION
# ----------------------------
def generate_operator_id(role):
    normalized_role = normalize_role(role)

    role_codes = {
        "The Chief": "13F",
        "The Keeper": "27K",
        "The Seeker": "41S",
        "Temporary Seeker": "T9X"
    }

    role_code = role_codes.get(normalized_role, "UNK")

    suffix = ''.join(
        secrets.choice(
            string.ascii_uppercase + string.digits
        ) for _ in range(4)
    )

    return f"ATH-ARC-{role_code}-{suffix}"
# ----------------------------
# LOGIN
# ----------------------------
@app.post("/token", tags=["Security"])
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT user_id, hashed_password, role, status, expires_at
            FROM users
            WHERE UPPER(operator_id)=UPPER(%s)
            """,
            (form_data.username,)
        )

        user = cur.fetchone()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        if not verify_password(
            form_data.password,
            user[1]
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        if user[3] != "APPROVED":
            raise HTTPException(
                status_code=403,
                detail=f"Account is {user[3]}"
            )
        
        if user[4] and user[4].replace(
            tzinfo=timezone.utc
        ) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=403,
                detail="Temporary access expired"
            )
        # Check 2FA
        cur.execute(
            """
            SELECT twofa_secret, twofa_enabled
            FROM users
            WHERE user_id=%s
            """,
            (user[0],)
        )

        twofa_data = cur.fetchone()

        if twofa_data and twofa_data[1]:
            raise HTTPException(
                status_code=401,
                detail="2FA verification required"
            )

        await record_audit(
            user_id=user[0],
            action_type="LOGIN",
            request=request,
            details="Secure login success",
            valid_reason="LOGIN_SUCCESS"
        )

        normalized_role = normalize_role(user[2])

        access_token = create_token(
            {
                "sub": str(user[0]),
                "role": normalized_role
            },
            token_type="access"
        )

        refresh_token = create_token(
            {
                "sub": str(user[0]),
                "role": normalized_role
            },
            token_type="refresh"
        )

        payload = jwt.decode(
            refresh_token,
            PUBLIC_KEY,
            algorithms=[ALGORITHM],
            audience="athenaeum-client",
            issuer="athenaeum-api"
        )

        jti = payload["jti"]

        expires = datetime.fromtimestamp(
            payload["exp"],
            tz=timezone.utc
        )

        cur.execute(
            """
            INSERT INTO refresh_tokens
            (token_id, user_id, expires_at)
            VALUES (%s, %s, %s)
            """,
            (
                jti,
                payload["sub"],
                expires
            )
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


# ----------------------------
# REFRESH
# ----------------------------
@app.post("/refresh", tags=["Security"])
async def refresh_token(req: RefreshRequest):
    conn = get_connection()
    cur = conn.cursor()

    try:
        payload = jwt.decode(
            req.refresh_token,
            PUBLIC_KEY,
            algorithms=[ALGORITHM],
            audience="athenaeum-client",
            issuer="athenaeum-api"
        )

        jti = payload.get("jti")

        cur.execute(
            """
            SELECT user_id, expires_at
            FROM refresh_tokens
            WHERE token_id=%s
            """,
            (jti,)
        )

        token = cur.fetchone()

        if not token:
            raise HTTPException(401, "Token revoked")

        new_access = create_token(
            {
                "sub": payload["sub"],
                "role": normalize_role(
                    payload.get("role", "The Seeker")
                )
            },
            token_type="access"
        )

        return {"access_token": new_access}

    finally:
        cur.close()
        conn.close()
#-------------------------------
# PUBLIC ACCESS REQUEST 
#-------------------------------
    
 
@app.post("/request-access")
async def request_access(req: AccessRequestModel):
    allowed_roles = [
        "The Seeker",
        "Temporary Seeker"
    ]

    if req.requested_role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid role request"
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Prevent duplicate pending requests
        cur.execute(
            """
            SELECT request_id
            FROM access_requests
            WHERE email=%s
            AND status IN ('PENDING', 'KEEPER_REVIEWED')
            """,
            (req.email,)
        )

        existing = cur.fetchone()

        if existing:
            raise HTTPException(
                status_code=400,
                detail="You already have a pending request."
            )

        # Insert new request
        cur.execute(
            """
            INSERT INTO access_requests (
                full_name,
                email,
                organization,
                purpose,
                requested_role,
                temporary_access,
                temporary_expiry
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                req.full_name,
                req.email,
                req.organization,
                req.purpose,
                req.requested_role,
                req.temporary_access,
                req.temporary_expiry
            )
        )

        conn.commit()

        return {
            "message": "Access request submitted"
        }

    finally:
        cur.close()
        conn.close()

# ----------------------------
# LOGOUT
# ----------------------------
@app.post("/logout", tags=["Security"])
async def logout(req: RefreshRequest):
    conn = get_connection()
    cur = conn.cursor()

    try:
        payload = jwt.decode(
            req.refresh_token,
            PUBLIC_KEY,
            algorithms=[ALGORITHM],
            audience="athenaeum-client",
            issuer="athenaeum-api"
        )

        jti = payload.get("jti")

        cur.execute(
            """
            DELETE FROM refresh_tokens
            WHERE token_id=%s
            """,
            (jti,)
        )

        conn.commit()

        return {
            "message": "Logged out successfully"
        }

    finally:
        cur.close()
        conn.close()


# ----------------------------
# CREATE USER
# ----------------------------
@app.post("/admin/create-user")
async def admin_create_user(
    name: str,
    email: EmailStr,
    role: str,
    password: str,
    current_user: dict = Depends(get_current_user)
):
    admin_role = current_user.get("role")

    # Allowed roles validation
    allowed_roles = [
        "The Chief",
        "The Keeper",
        "The Seeker",
        "Temporary Seeker"
    ]

    normalized_input_role = normalize_role(role)

    if role == "Temporary Seeker":
        normalized_input_role = "Temporary Seeker"

    if normalized_input_role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Only authorized Athenaeum roles are allowed."
        )

    role = normalized_input_role

    if admin_role in ["The Seeker", "Temporary Seeker"]:
     raise HTTPException(
        status_code=403,
        detail="Access Denied"
    )

    if (
        admin_role == "The Keeper"
        and role in ["The Chief", "The Keeper"]
    ):
        raise HTTPException(
            403,
            "The Keeper can only create Seekers"
        )

    if not is_password_strong(password):
        raise HTTPException(
            400,
            "Password too weak"
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT identity_id
            FROM identity_registry
            WHERE primary_email = %s
            """,
            (email,)
        )

        existing_identity = cur.fetchone()

        if existing_identity:
            identity_id = existing_identity[0]

            # Notify Chief about returning identity
            cur.execute(
                """
                INSERT INTO chief_notifications (
                    identity_id,
                    message
                )
                VALUES (%s, %s)
                """,
                (
                    identity_id,
                    f"Returning identity detected: {name} ({email}) was reissued access."
                )
            )

        else:
            cur.execute(
                """
                INSERT INTO identity_registry (
                    full_name,
                    primary_email
                )
                VALUES (%s, %s)
                RETURNING identity_id
                """,
                (
                    name,
                    email
                )
            )

            identity_id = cur.fetchone()[0]

        # Only one active Chief allowed
        if role == "The Chief":
            cur.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE role = 'The Chief'
                AND status = 'APPROVED'
                """
            )

            chief_count = cur.fetchone()[0]

            if chief_count >= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Only one Chief allowed"
                )

        operator_id = generate_operator_id(role)
        hashed = hash_password(password)

        cur.execute(
            """
            INSERT INTO users (
                name,
                email,
                operator_id,
                role,
                status,
                hashed_password,
                identity_id
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                'APPROVED',
                %s,
                %s
            )
            """,
            (
                name,
                email,
                operator_id,
                role,
                hashed,
                identity_id
            )
        )

        conn.commit()

        return {
            "message": "User created successfully",
            "operator_id": operator_id
        }

    finally:
        cur.close()
        conn.close()


# ----------------------------
# CHANGE PASSWORD
# ----------------------------
@app.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        user_id = current_user["user_id"]

        cur.execute(
            """
            SELECT hashed_password
            FROM users
            WHERE user_id=%s
            """,
            (user_id,)
        )

        user = cur.fetchone()

        if not verify_password(
            current_password,
            user[0]
        ):
            raise HTTPException(
                401,
                "Current password incorrect"
            )

        if not is_password_strong(new_password):
            raise HTTPException(
                400,
                "Weak password"
            )

        new_hash = hash_password(new_password)

        cur.execute(
            """
            UPDATE users
            SET hashed_password=%s
            WHERE user_id=%s
            """,
            (new_hash, user_id)
        )

        conn.commit()

        return {
            "message": "Password updated"
        }

    finally:
        cur.close()
        conn.close()


# ----------------------------
# SETUP 2FA
# ----------------------------
@app.post("/setup-2fa")
async def setup_2fa(
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        user_id = current_user["user_id"]

        secret = pyotp.random_base32()

        cur.execute(
            """
            UPDATE users
            SET twofa_secret=%s
            WHERE user_id=%s
            """,
            (secret, user_id)
        )

        conn.commit()

        totp = pyotp.TOTP(secret)

        uri = totp.provisioning_uri(
            name=str(user_id),
            issuer_name="Athenaeum"
        )

        qr = qrcode.make(uri)

        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")

        qr_base64 = base64.b64encode(
            buffer.getvalue()
        ).decode()

        return {
            "secret": secret,
            "qr_code": qr_base64
        }

    finally:
        cur.close()
        conn.close()


# ----------------------------
# VERIFY 2FA
# ----------------------------
@app.post("/verify-2fa")
async def verify_2fa(
    req: Verify2FARequest,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        user_id = current_user["user_id"]

        cur.execute(
            """
            SELECT twofa_secret
            FROM users
            WHERE user_id=%s
            """,
            (user_id,)
        )

        user = cur.fetchone()

        secret = user[0]

        totp = pyotp.TOTP(secret)

        if not totp.verify(req.token):
            raise HTTPException(
                401,
                "Invalid 2FA token"
            )

        cur.execute(
            """
            UPDATE users
            SET twofa_enabled=TRUE
            WHERE user_id=%s
            """,
            (user_id,)
        )

        conn.commit()

        return {
            "message": "2FA enabled"
        }

    finally:
        cur.close()
        conn.close()


# ----------------------------
# ROUTERS
# ----------------------------
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
app.include_router(incidents.router, dependencies=[Depends(get_current_user)])
app.include_router(locations.router, dependencies=[Depends(get_current_user)])
app.include_router(reports.router, dependencies=[Depends(get_current_user)])
app.include_router(analytics.router, dependencies=[Depends(get_current_user)])