import asyncio
import platform
import time
import uuid
from urllib import response
import pyotp
import qrcode
import io
import base64
import secrets
import string
import json
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Request, Form, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError

from app.audit_utils import audit_action
from pdf.pdf_generator import generate_pdf
from app.database import get_connection, record_audit
from app.token_manager import (
    PUBLIC_KEY,
    ALGORITHM,
    REFRESH_EXPIRE_DAYS,
    create_token,
    consume_once,
)
from app.auth import router as auth_router, get_current_user, limiter

def consume_totp_once(user_id, totp) -> bool:
    """Allow a valid TOTP time-step to be consumed only once."""
    now = datetime.now(timezone.utc)
    time_step = int(now.timestamp()) // totp.interval
    ttl_seconds = totp.interval * 2

    return consume_once(
        f"2fa:totp:{user_id}:{time_step}",
        ttl_seconds
    )


from app.utils.security import (
    hash_password,
    verify_password,
    is_password_strong
)

from app.services.audit_service import log_audit_activity

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
    authority,
    profile
)

# ----------------------------
# Windows Event Loop Fix
# ----------------------------
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

# ----------------------------
# App Initialization & CORS
# ----------------------------
app = FastAPI(
    title="Athenaeum Library API",
    swagger_ui_parameters={"deepLinking": True},
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",      # Tauri Dev
        "http://tauri.localhost",     # Tauri Windows Production
        "https://tauri.localhost",
        "https://athenaeum-project.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

CHANGELOG_PATH = Path(__file__).resolve().parent / "changelog.json"


# ----------------------------
# Request Models
# ----------------------------
class RefreshRequest(BaseModel):
    refresh_token: str

class Verify2FARequest(BaseModel):
    token: str

class Login2FARequest(BaseModel):
    temp_token: str
    totp_code: str
    remember_me: bool = False

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
# SYSTEM CHANGELOG ROUTE
# ----------------------------
@app.get("/system/changelog", tags=["System"])
def get_system_changelog():
    if not CHANGELOG_PATH.exists():
        return []
    try:
        with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read changelog: {str(e)}")


# ----------------------------
# Chief Review / Final Decision
# ----------------------------
@app.post("/chief/decide-request/{request_id}")
async def chief_decide_request(
    request: Request,
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

        previous_status = request_data[5]

        if previous_status in ["APPROVE", "REJECT"]:
            raise HTTPException(
                status_code=400,
                detail="Request already processed"
            )

        temp_password = None
        operator_id = None

        if req.decision == "APPROVE":
            alphabet = (
                string.ascii_letters +
                string.digits +
                "!@#$%"
            )

            temp_password = "".join(
                secrets.choice(alphabet)
                for _ in range(12)
            )
            operator_id = generate_operator_id(request_data[2], cur)
            hashed = hash_password(temp_password)

            login_id = request_data[1].split("@")[0]

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
                    %s, %s, %s, %s, %s,
                    'APPROVED',
                    %s, %s
                )
                """,
                (
                    request_data[0],
                    request_data[1],
                    login_id,
                    operator_id,
                    request_data[2],
                    hashed,
                    request_data[4]
                )
            )

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

        admin_id = str(current_user.get("user_id") or current_user.get("sub") or "SYSTEM")
        admin_name = str(current_user.get("name") or current_user.get("username") or "The Chief")
        admin_role_val = str(current_user.get("role") or "The Chief")

        is_approved = req.decision == "APPROVE"
        action_type = "ACCESS_REQUEST_APPROVE" if is_approved else "ACCESS_REQUEST_REJECT"
        target_id = operator_id if is_approved else f"REQ-{request_id}"

        default_reason = (
            f"Approved access request #{request_id} for {request_data[0]} ({request_data[2]})"
            if is_approved
            else f"Rejected access request #{request_id} for {request_data[0]}"
        )

        log_audit_activity(
            request=request,
            user_id=admin_id,
            username=admin_name,
            role=admin_role_val,
            designation="Staff",
            category="GOVERNANCE",
            action_type=action_type,
            target_entity="ACCESS_REQUEST",
            target_id=target_id,
            justification=req.notes or default_reason,
            diff_payload={
                "status": {
                    "old": previous_status,
                    "new": req.decision
                }
            },
            extra_metadata={
                "request_id": request_id,
                "applicant_name": request_data[0],
                "applicant_email": request_data[1],
                "requested_role": request_data[2],
                "temporary_access": request_data[3],
                "temporary_expiry": str(request_data[4]) if request_data[4] else None,
                "assigned_operator_id": operator_id,
                "chief_notes": req.notes
            }
        )

        response = {
            "message": f"Request {req.decision.lower()}d successfully."
        }

        if is_approved:
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
    request: Request,
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
            RETURNING name, email, operator_id, role, status
            """,
            (user_id,)
        )
        revoked_user = cur.fetchone()

        if not revoked_user:
            raise HTTPException(status_code=404, detail="User not found.")

        conn.commit()

        target_name, target_email, target_op_id, target_role, _ = revoked_user

        admin_id = str(current_user.get("user_id") or current_user.get("sub") or "SYSTEM")
        admin_name = str(current_user.get("name") or current_user.get("username") or "The Chief")
        admin_role_val = str(current_user.get("role") or "The Chief")

        log_audit_activity(
            request=request,
            user_id=admin_id,
            username=admin_name,
            role=admin_role_val,
            designation="Staff",
            category="SECURITY",
            action_type="USER_REVOKE",
            target_entity="PERSONNEL",
            target_id=target_op_id or str(user_id),
            justification=f"Revoked credentials for {target_name} ({target_op_id or user_id})",
            diff_payload={
                "status": {
                    "old": "APPROVED",
                    "new": "REVOKED"
                }
            },
            extra_metadata={
                "revoked_user_id": user_id,
                "revoked_name": target_name,
                "revoked_email": target_email,
                "revoked_operator_id": target_op_id,
                "revoked_role": target_role
            }
        )

        return {
            "message": f"User access revoked for {target_name} ({target_op_id})."
        }

    finally:
        cur.close()
        conn.close()


# -----------------------------
# Keeper Review Recommendation
# -----------------------------
@app.post("/keeper/recommend-request/{request_id}")
async def keeper_recommend_request(
    request: Request,
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
            SELECT full_name, email, requested_role, status
            FROM access_requests
            WHERE request_id=%s
            """,
            (request_id,)
        )
        req_row = cur.fetchone()
        if not req_row:
            raise HTTPException(status_code=404, detail="Request not found.")

        previous_status = req_row[3]

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

        keeper_id = str(current_user.get("user_id") or current_user.get("sub") or "SYSTEM")
        keeper_name = str(current_user.get("name") or current_user.get("username") or "The Keeper")

        log_audit_activity(
            request=request,
            user_id=keeper_id,
            username=keeper_name,
            role="The Keeper",
            designation="Staff",
            category="GOVERNANCE",
            action_type="ACCESS_REQUEST_RECOMMEND",
            target_entity="ACCESS_REQUEST",
            target_id=f"REQ-{request_id}",
            justification=req.notes or f"Keeper recommended {req.recommendation} for {req_row[0]}",
            diff_payload={
                "status": {"old": previous_status, "new": "KEEPER_REVIEWED"},
                "recommendation": {"old": None, "new": req.recommendation}
            },
            extra_metadata={
                "request_id": request_id,
                "applicant_name": req_row[0],
                "applicant_email": req_row[1],
                "requested_role": req_row[2],
                "recommendation": req.recommendation,
                "keeper_notes": req.notes
            }
        )

        return {
            "message": "Recommendation submitted."
        }

    finally:
        cur.close()
        conn.close()

# ----------------------------
# KEEPER NOTIFICATIONS
# ----------------------------
@app.get("/notifications")
async def get_notifications(
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        user_id = current_user["user_id"]

        cur.execute(
            """
            SELECT
                n.notification_id,
                n.message,
                n.is_read,
                n.created_at
            FROM public.chief_notifications n
            INNER JOIN public.users u
                ON u.identity_id = n.identity_id
            WHERE u.user_id = %s
                AND n.is_read IS NOT TRUE
            ORDER BY n.created_at DESC, n.notification_id DESC
            """,
            (user_id,)
        )

        rows = cur.fetchall()

        return [
            {
                "notification_id": row[0],
                "message": row[1],
                "is_read": row[2],
                "created_at": row[3]
            }
            for row in rows
        ]

    finally:
        cur.close()
        conn.close()


# ---------------------------------
# KEEPER NOTIFICATIONS MARK AS READ
# ---------------------------------


@app.post("/notifications/read")
async def mark_notifications_read(
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        user_id = current_user["user_id"]

        cur.execute("""
            UPDATE public.chief_notifications n
            SET is_read = TRUE
            FROM public.users u
            WHERE n.identity_id = u.identity_id
              AND u.user_id = %s
              AND n.is_read IS NOT TRUE
        """, (user_id,))

        conn.commit()

        return {"status": "success"}

    finally:
        cur.close()
        conn.close()

# ----------------------------
# Request Logger Middleware
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
# Role Normalization & Helpers
# ----------------------------
def normalize_role(role: str) -> str:
    role = role.lower().strip()

    if role in ["the chief", "chief"]:
        return "The Chief"
    if role in ["the keeper", "keeper"]:
        return "The Keeper"
    if role in ["the seeker", "seeker"]:
        return "The Seeker"
    if role == "temporary seeker":
        return "Temporary Seeker"

    return "INVALID"

def generate_operator_id(role: str, cur=None) -> str:
    normalized_role = normalize_role(role)

    role_codes = {
        "The Chief": "13F",
        "The Keeper": "27K",
        "The Seeker": "41S",
        "Temporary Seeker": "T9X"
    }

    role_code = role_codes.get(normalized_role, "UNK")
    prefix = f"ATH{role_code}"

    if cur is not None:
        try:
            cur.execute(
                "SELECT operator_id FROM users WHERE operator_id LIKE %s",
                (f"{prefix}%",)
            )
            rows = cur.fetchall()
            highest_seq = 0
            for (op_id,) in rows:
                if op_id and len(op_id) == 8 and op_id.startswith(prefix):
                    seq_str = op_id[len(prefix):]
                    if seq_str.isdigit():
                        highest_seq = max(highest_seq, int(seq_str))
            return f"{prefix}{highest_seq + 1:02d}"
        except Exception:
            pass

    return f"{prefix}{secrets.randbelow(99) + 1:02d}"


# ----------------------------
# LOGIN & TOKEN ISSUANCE
# ----------------------------
@app.post("/token", tags=["Security"])
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    remember_me: bool = Form(False),
    otp_code: str | None = Form(None)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT user_id, hashed_password, role, status, expires_at, name, operator_id
            FROM users
            WHERE UPPER(operator_id)=UPPER(%s)
            """,
            (form_data.username,)
        )

        user = cur.fetchone()

        if not user or not verify_password(form_data.password, user[1]):
            log_audit_activity(
                request=request,
                user_id=str(user[0]) if user else "UNKNOWN",
                username=user[5] if user else form_data.username,
                role=user[2] if user else "UNKNOWN",
                designation="Staff",
                category="SECURITY",
                action_type="LOGIN_FAILED",
                target_entity="SESSION",
                target_id=form_data.username,
                justification="Failed authentication attempt: invalid credentials"
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        if user[3] != "APPROVED":
            raise HTTPException(
                status_code=403,
                detail=f"Account is {user[3]}"
            )

        if user[4] and user[4].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=403,
                detail="Temporary access expired"
            )

        cur.execute(
            """
            SELECT twofa_secret, twofa_enabled
            FROM users
            WHERE user_id=%s
            """,
            (user[0],)
        )

        twofa_data = cur.fetchone()

        # 2FA Challenge Evaluation
        if twofa_data and twofa_data[1]:
            if otp_code:
                totp = pyotp.TOTP(twofa_data[0])
                if not totp.verify(otp_code.strip()):
                    log_audit_activity(
                        request=request,
                        user_id=str(user[0]),
                        username=user[5],
                        role=user[2],
                        designation="Staff",
                        category="SECURITY",
                        action_type="2FA_LOGIN_FAILED",
                        target_entity="SESSION",
                        target_id=user[6],
                        justification="Primary login failed: invalid 2FA passcode submitted",
                        extra_metadata={"operator_id": user[6]}
                    )
                    raise HTTPException(status_code=401, detail="Invalid 2FA passcode")

                if not consume_totp_once(user[0], totp):
                    raise HTTPException(
                        status_code=401,
                        detail="2FA code already used."
                    )

            else:
                preauth_token = create_token(
                    {
                        "sub": str(user[0]),
                        "scope": "2fa_preauth",
                        "role": normalize_role(user[2]),
                        "jti": str(uuid.uuid4())
                    },
                    token_type="access"
                )

                log_audit_activity(
                    request=request,
                    user_id=str(user[0]),
                    username=user[5],
                    role=user[2],
                    designation="Staff",
                    category="SECURITY",
                    action_type="2FA_CHALLENGE_ISSUED",
                    target_entity="SESSION",
                    target_id=user[6],
                    justification="Primary credentials accepted; 2FA verification challenge issued",
                    extra_metadata={"operator_id": user[6]}
                )

                return {
                    "twofa_required": True,
                    "temp_token": preauth_token,
                    "operator_id": user[6],
                    "message": "Two-factor authentication required"
                }

        # Successful Login Audit (Chained)
        normalized_role = normalize_role(user[2])
        is_2fa_login = bool(twofa_data and twofa_data[1] and otp_code)

        log_audit_activity(
            request=request,
            user_id=str(user[0]),
            username=user[5],
            role=normalized_role,
            designation="Staff",
            category="SECURITY",
            action_type="LOGIN_SUCCESS_2FA" if is_2fa_login else "LOGIN",
            target_entity="SESSION",
            target_id=user[6],
            justification="Operator successfully authenticated" + (" via direct 2FA OTP" if is_2fa_login else ""),
            extra_metadata={"operator_id": user[6]}
        )

        access_token = create_token(
            {
                "sub": str(user[0]),
                "role": normalized_role
            },
            token_type="access"
        )

        response_payload = {
            "access_token": access_token,
            "token_type": "bearer",
            "role": normalized_role,
            "user_name": user[5],
            "user_id": str(user[0]),
            "operator_id": user[6]
        }

        if remember_me:
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
            expires = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

            cur.execute(
                """
                INSERT INTO refresh_tokens (token_id, user_id, expires_at)
                VALUES (%s, %s, %s)
                """,
                (jti, payload["sub"], expires)
            )


            response.set_cookie(
                key="refresh_token",
             value=refresh_token,
                httponly=True,
             secure=False,
                samesite="Strict",
                max_age=REFRESH_EXPIRE_DAYS * 86400,
            )

        conn.commit()
        return response_payload

    finally:
        cur.close()
        conn.close()


# ----------------------------
# 2FA LOGIN VERIFICATION
# ----------------------------
@app.post("/login/verify-2fa", tags=["Security"])
@limiter.limit("5/minute")
async def verify_login_2fa(
    request: Request,
    req: Login2FARequest,
    response: Response
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        try:
            payload = jwt.decode(
                req.temp_token,
                PUBLIC_KEY,
                algorithms=[ALGORITHM],
                audience="athenaeum-client",
                issuer="athenaeum-api"
            )
        except JWTError:
            raise HTTPException(status_code=401, detail="2FA session expired. Please log in again.")

        if payload.get("scope") != "2fa_preauth":
            raise HTTPException(status_code=401, detail="Invalid token scope for 2FA.")

        user_id = int(payload["sub"])

        cur.execute(
            """
            SELECT user_id, twofa_secret, twofa_enabled, role, name, operator_id, status
            FROM users
            WHERE user_id=%s
            """,
            (user_id,)
        )
        user = cur.fetchone()

        if not user or not user[1] or user[6] != "APPROVED":
            raise HTTPException(status_code=403, detail="Account is disabled or 2FA is misconfigured.")

        totp = pyotp.TOTP(user[1])

        if not totp.verify(req.totp_code.strip()):
            log_audit_activity(
                request=request,
                user_id=str(user[0]),
                username=user[4],
                role=user[3],
                designation="Staff",
                category="SECURITY",
                action_type="2FA_LOGIN_FAILED",
                target_entity="SESSION",
                target_id=user[5],
                justification="Failed second-factor authentication: incorrect TOTP code entered",
                extra_metadata={"operator_id": user[5]}
            )
            raise HTTPException(status_code=401, detail="Invalid 2FA code.")

        if not consume_totp_once(user[0], totp):
            raise HTTPException(
                status_code=401,
                detail="2FA code already used."
            )

        preauth_jti = payload.get("jti")
        if not preauth_jti:
            raise HTTPException(
                status_code=401,
                detail="Invalid 2FA session."
            )

        try:
            preauth_exp = int(payload["exp"])
            preauth_ttl = max(
                1,
                preauth_exp - int(datetime.now(timezone.utc).timestamp())
            )
        except (KeyError, TypeError, ValueError):
            raise HTTPException(
                status_code=401,
                detail="Invalid 2FA session."
            )

        if not consume_once(
            f"2fa:preauth:{preauth_jti}",
            preauth_ttl
        ):
            raise HTTPException(
                status_code=401,
                detail="2FA session already used."
            )

        log_audit_activity(
            request=request,
            user_id=str(user[0]),
            username=user[4],
            role=user[3],
            designation="Staff",
            category="SECURITY",
            action_type="LOGIN_SUCCESS_2FA",
            target_entity="SESSION",
            target_id=user[5],
            justification="Second-factor TOTP challenge verified successfully",
            extra_metadata={"operator_id": user[5]}
        )

        normalized_role = normalize_role(user[3])

        access_token = create_token(
            {
                "sub": str(user[0]),
                "role": normalized_role
            },
            token_type="access"
        )

        response_payload = {
            "access_token": access_token,
            "token_type": "bearer",
            "role": normalized_role,
            "user_name": user[4],
            "user_id": str(user[0]),
            "operator_id": user[5]
        }

        if req.remember_me:
            refresh_token = create_token(
                {
                    "sub": str(user[0]),
                    "role": normalized_role
                },
                token_type="refresh"
            )

            refresh_payload = jwt.decode(
                refresh_token,
                PUBLIC_KEY,
                algorithms=[ALGORITHM],
                audience="athenaeum-client",
                issuer="athenaeum-api"
            )

            jti = refresh_payload["jti"]
            expires = datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)

            cur.execute(
                """
                INSERT INTO refresh_tokens (token_id, user_id, expires_at)
                VALUES (%s, %s, %s)
                """,
                (jti, refresh_payload["sub"], expires)
            )

            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=False,
                samesite="Strict",
                max_age=REFRESH_EXPIRE_DAYS * 86400,
            )


        conn.commit()
        return response_payload

    finally:
        cur.close()
        conn.close()



# -------------------------------
# PUBLIC ACCESS REQUEST
# -------------------------------
@app.post("/request-access")
async def request_access(request: Request, req: AccessRequestModel):
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
            RETURNING request_id
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

        new_request_id = cur.fetchone()[0]
        conn.commit()

        log_audit_activity(
            request=request,
            user_id="PUBLIC_APPLICANT",
            username=req.full_name,
            role="Applicant",
            designation="Public",
            category="ACCESS_CONTROL",
            action_type="ACCESS_REQUEST_SUBMIT",
            target_entity="ACCESS_REQUEST",
            target_id=f"REQ-{new_request_id}",
            justification=f"Inbound registration by {req.full_name} for role {req.requested_role}",
            extra_metadata={
                "request_id": new_request_id,
                "email": req.email,
                "organization": req.organization,
                "purpose": req.purpose,
                "requested_role": req.requested_role,
                "temporary_access": req.temporary_access
            }
        )

        return {
            "message": "Access request submitted"
        }

    finally:
        cur.close()
        conn.close()


# ----------------------------
# CREATE USER
# ----------------------------
@app.post("/admin/create-user")
async def admin_create_user(
    request: Request,
    name: str,
    email: EmailStr,
    role: str,
    password: str,
    current_user: dict = Depends(get_current_user)
):
    admin_role = current_user.get("role")

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

        operator_id = generate_operator_id(role, cur)
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

        admin_id = str(current_user.get("user_id") or current_user.get("sub") or "SYSTEM")
        admin_name = str(current_user.get("name") or current_user.get("username") or "The Chief")
        admin_role_val = str(current_user.get("role") or "The Chief")

        log_audit_activity(
            request=request,
            user_id=admin_id,
            username=admin_name,
            role=admin_role_val,
            designation="Staff",
            category="GOVERNANCE",
            action_type="USER_PROVISION",
            target_entity="PERSONNEL",
            target_id=operator_id,
            justification=f"Provisioned operator {name} ({operator_id}) with role {role}",
            extra_metadata={
                "created_operator_id": operator_id,
                "created_name": name,
                "created_email": email,
                "assigned_role": role
            }
        )

        return {
            "message": "User created successfully",
            "operator_id": operator_id
        }

    finally:
        cur.close()
        conn.close()


# ----------------------------
# ADMIN: LIST USERS
# ----------------------------
@app.get("/admin/users", tags=["Admin"])
async def list_users(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["The Chief", "The Keeper"]:
        raise HTTPException(status_code=403, detail="Access Denied")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT user_id, name, email, operator_id, role, status
            FROM users
            ORDER BY user_id ASC
            """
        )
        rows = cur.fetchall()
        return [
            {
                "user_id": r[0],
                "name": r[1],
                "email": r[2],
                "operator_id": r[3],
                "role": r[4],
                "status": r[5]
            }
            for r in rows
        ]
    finally:
        cur.close()
        conn.close()


# ----------------------------
# ADMIN: LIST ACCESS REQUESTS
# ----------------------------
@app.get("/admin/access-requests", tags=["Admin"])
async def list_access_requests(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["The Chief", "The Keeper"]:
        raise HTTPException(status_code=403, detail="Access Denied")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT request_id, full_name, email, organization, purpose, requested_role, status
            FROM access_requests
            WHERE status IN ('PENDING', 'KEEPER_REVIEWED')
            ORDER BY request_id DESC
            """
        )
        rows = cur.fetchall()
        return [
            {
                "request_id": r[0],
                "full_name": r[1],
                "email": r[2],
                "organization": r[3],
                "purpose": r[4],
                "requested_role": r[5],
                "status": r[6]
            }
            for r in rows
        ]
    finally:
        cur.close()
        conn.close()


# ----------------------------
# CHANGE PASSWORD
# ----------------------------
@app.post("/change-password")
async def change_password(
    request: Request,
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
            SELECT hashed_password, name, role, operator_id
            FROM users
            WHERE user_id=%s
            """,
            (user_id,)
        )

        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User record not found")

        if not verify_password(current_password, user[0]):
            raise HTTPException(
                status_code=401,
                detail="Current password incorrect"
            )

        if not is_password_strong(new_password):
            raise HTTPException(
                status_code=400,
                detail="Weak password"
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

        cur.execute(
            """
            DELETE FROM refresh_tokens
            WHERE user_id=%s
            """,
            (user_id,)
        )

        conn.commit()

        log_audit_activity(
            request=request,
            user_id=str(user_id),
            username=str(user[1]),
            role=str(user[2]),
            designation="Staff",
            category="SECURITY",
            action_type="PASSWORD_CHANGE",
            target_entity="USER_CREDENTIALS",
            target_id=user[3] or str(user_id),
            justification="Operator-initiated credential rotation",
            diff_payload={"password": {"old": "[PROTECTED]", "new": "[PROTECTED]"}},
            extra_metadata={"operator_id": user[3]}
        )

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
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        user_id = current_user["user_id"]
        secret = pyotp.random_base32()

        cur.execute(
            """
            SELECT name, role, operator_id
            FROM users
            WHERE user_id=%s
            """,
            (user_id,)
        )
        user_info = cur.fetchone()

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

        if user_info:
            log_audit_activity(
                request=request,
                user_id=str(user_id),
                username=str(user_info[0]),
                role=str(user_info[1]),
                designation="Staff",
                category="SECURITY",
                action_type="2FA_SETUP_INIT",
                target_entity="MFA_DEVICE",
                target_id=user_info[2] or str(user_id),
                justification="Operator initialized 2FA registration ceremony",
                extra_metadata={"operator_id": user_info[2]}
            )

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
@limiter.limit("5/minute")
async def verify_2fa(
    request: Request,
    req: Verify2FARequest,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        user_id = current_user["user_id"]

        cur.execute(
            """
            SELECT twofa_secret, name, role, operator_id
            FROM users
            WHERE user_id=%s
            """,
            (user_id,)
        )

        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User record not found")

        secret = user[0]
        totp = pyotp.TOTP(secret)

        if not totp.verify(req.token):
            log_audit_activity(
                request=request,
                user_id=str(user_id),
                username=str(user[1]),
                role=str(user[2]),
                designation="Staff",
                category="SECURITY",
                action_type="2FA_VERIFY_FAILED",
                target_entity="MFA_DEVICE",
                target_id=user[3] or str(user_id),
                justification="Failed 2FA verification attempt: invalid TOTP token submitted",
                extra_metadata={"operator_id": user[3]}
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid 2FA token"
            )

        if not consume_totp_once(user_id, totp):
            raise HTTPException(
                status_code=401,
                detail="2FA code already used."
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

        log_audit_activity(
            request=request,
            user_id=str(user_id),
            username=str(user[1]),
            role=str(user[2]),
            designation="Staff",
            category="SECURITY",
            action_type="2FA_ENABLE",
            target_entity="MFA_DEVICE",
            target_id=user[3] or str(user_id),
            justification="Enrolled and verified TOTP multi-factor authenticator",
            diff_payload={"twofa_enabled": {"old": False, "new": True}},
            extra_metadata={"operator_id": user[3]}
        )

        return {
            "message": "2FA enabled"
        }

    finally:
        cur.close()
        conn.close()


# ----------------------------
# ROUTER REGISTRATION
# ----------------------------
app.include_router(print_router.router)
app.include_router(health.router)
app.include_router(catalogue.router)
app.include_router(authority.router, dependencies=[Depends(get_current_user)])
app.include_router(auth_router)
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
