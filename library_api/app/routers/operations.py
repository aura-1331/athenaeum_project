# app/routers/operations.py

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.database import get_connection
from app.auth import get_current_user, require_role
from app.audit_utils import audit_action
from app.services.operations_service import execute_operation
from app.services.audit_service import log_audit_activity

router = APIRouter(prefix="/operations", tags=["Operations"])

class OperationPayload(BaseModel):
    accession_no: str
    action: str
    actor: str
    notes: str = ""

@audit_action("EXECUTE_OPERATION")
@router.post("/execute", dependencies=[Depends(require_role(["The Keeper", "The Chief"]))])
def run_operation(
    payload: OperationPayload, 
    request: Request, 
    current_user: dict = Depends(get_current_user)
):
    db = get_connection()
    try:
        result = execute_operation(
            db,
            payload.accession_no,
            payload.action,
            payload.actor,
            payload.notes,
        )

        # Cryptographic ledger anchor
        actor_id = str(current_user.get("user_id", "UNKNOWN"))
        actor_name = str(current_user.get("username") or current_user.get("name") or payload.actor or "Archive Operator")
        actor_role = str(current_user.get("role", "The Keeper"))

        log_audit_activity(
            request=request,
            user_id=actor_id,
            username=actor_name,
            role=actor_role,
            designation=str(current_user.get("designation") or actor_role),
            category="OPERATIONS",
            action_type="EXECUTE_OPERATION",
            target_entity="ACCESSION",
            target_id=payload.accession_no,
            endpoint=request.url.path,
            http_method="POST",
            justification=payload.notes or f"Executed operation '{payload.action}' on holding {payload.accession_no}",
            diff_payload={
                "accession_no": payload.accession_no,
                "action": payload.action,
                "specified_actor": payload.actor,
                "notes": payload.notes,
                "execution_result": result if isinstance(result, (dict, list, str, int, bool)) else str(result)
            },
            extra_metadata={
                "accession_no": payload.accession_no,
                "action": payload.action
            }
        )

        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@audit_action("VIEW_ALLOWED_OPERATIONS")
@router.get("/allowed/{accession_no}")
def get_allowed(
    accession_no: str, 
    request: Request, 
    current_user: dict = Depends(get_current_user)
):
    db = get_connection()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT action FROM get_allowed_transitions(%s)", (accession_no,))
            rows = cur.fetchall()
        return {"actions": [r[0] for r in rows]}
    finally:
        db.close()