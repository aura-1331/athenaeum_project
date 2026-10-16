# app/routers/operations.py

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.database import get_connection
from app.auth import get_current_user, require_role
from app.audit_utils import audit_action
from app.services.operations_service import execute_operation
from app.routers.review_utils import _audit_ledger

router = APIRouter(prefix="/operations", tags=["Operations"])


class OperationPayload(BaseModel):
    accession_no: str
    action: str
    # Kept for backwards-compatible request bodies; never used as audit identity.
    actor: str | None = None
    notes: str = ""


@router.post(
    "/execute",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))],
)
def run_operation(
    payload: OperationPayload,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    action = str(payload.action or "").strip()
    action_key = action.upper()
    accession_no = payload.accession_no
    notes = str(payload.notes or "")
    role_key = str(current_user.get("role") or "").strip().lower()

    # OVERRIDE changes availability directly and is restricted to The Chief.
    if action_key == "OVERRIDE":
        if role_key != "the chief":
            raise HTTPException(
                status_code=403,
                detail="Only The Chief can use OVERRIDE.",
            )
        if not notes.strip():
            raise HTTPException(
                status_code=400,
                detail="A written reason is required for OVERRIDE.",
            )

    if len(notes) > 2000:
        raise HTTPException(status_code=400, detail="Notes are too long.")
    db = get_connection(request=request)
    try:
        result = execute_operation(
            db,
            payload.accession_no,
            payload.action,
            str(
                current_user.get("username")
                or current_user.get("name")
                or current_user.get("user_id")
                or "Archive Operator"
            ),
            notes,
        )

        actor_name = str(
            current_user.get("username")
            or current_user.get("name")
            or current_user.get("user_id")
            or "Archive Operator"
        )
        # Keep native JSON-compatible results in the audit record; stringify
        # unexpected result types to avoid making audit serialization fail.
        if not isinstance(result, (dict, list, str, int, float, bool, type(None))):
            audit_result = str(result)
        else:
            audit_result = result

        # This endpoint writes its success audit explicitly. Do not also attach
        # @audit_action here, which would risk creating a duplicate event.
        _audit_ledger(
            request=request,
            current_user=current_user,
            conn=db,
            category="OPERATIONS",
            action_type="EXECUTE_OPERATION",
            target_entity="ACCESSION",
            target_id=accession_no,
            http_method="POST",
            justification=(
                notes
                or f"Executed operation '{action}' on holding {accession_no}"
            ),
            diff={
                "accession_no": accession_no,
                "action": action,
                # This value is request-body context only, not audit identity.
                "specified_actor": payload.actor,
                "authenticated_actor": actor_name,
                "notes": notes,
                "execution_result": audit_result,
            },
            extra={
                "accession_no": accession_no,
                "action": action,
                "override": action_key == "OVERRIDE",
            },
        )

        db.commit()
        return result

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        print(f"Operation execution/audit failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Operation could not be completed; changes were rolled back.",
        ) from exc
    finally:
        db.close()


@router.get(
    "/allowed/{accession_no}",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))],
)
@audit_action("VIEW_ALLOWED_OPERATIONS")
def get_allowed(
    accession_no: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    db = get_connection(request=request)
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT action FROM get_allowed_transitions(%s)",
                (accession_no,),
            )
            rows = cur.fetchall()
        return {"actions": [row[0] for row in rows]}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Allowed-operation lookup failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Unable to load allowed operations.",
        ) from exc
    finally:
        db.close()
