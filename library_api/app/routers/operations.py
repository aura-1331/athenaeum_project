from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.database import get_connection
from app.auth import get_current_user, require_role # 1. Import require_role
from app.audit_utils import audit_action
from app.services.operations_service import execute_operation

router = APIRouter(prefix="/operations", tags=["Operations"])

class OperationPayload(BaseModel):
    accession_no: str
    action: str
    actor: str
    notes: str = ""

@audit_action("EXECUTE_OPERATION")
@router.post("/execute", dependencies=[Depends(require_role(["The Keeper", "The Chief"]))]) # 2. Add Security Guard
def run_operation(
    payload: OperationPayload, 
    request: Request, 
    current_user: dict = Depends(get_current_user)
):
    # 3. Manual 'if current_user["role"]...' check removed

    db = get_connection()
    try:
        result = execute_operation(
            db,
            payload.accession_no,
            payload.action,
            payload.actor,
            payload.notes,
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
    # This remains as is (read-only), so standard login is sufficient.
    db = get_connection()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT action FROM get_allowed_transitions(%s)", (accession_no,))
            rows = cur.fetchall()
        return {"actions": [r[0] for r in rows]}
    finally:
        db.close()