from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_connection
from app.services.operations_service import execute_operation

router = APIRouter(prefix="/operations", tags=["Operations"])


class OperationPayload(BaseModel):
    accession_no: str
    action: str
    actor: str
    notes: str = ""


@router.post("/execute")
def run_operation(payload: OperationPayload):
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


# ✅ ENTERPRISE UPGRADE — Allowed Actions Endpoint
@router.get("/allowed/{accession_no}")
def get_allowed(accession_no: str):
    db = get_connection()

    try:
        with db.cursor() as cur:
            # this calls your DB transition authority layer
            cur.execute(
                """
                SELECT action
                FROM get_allowed_transitions(%s)
                """,
                (accession_no,),
            )
            rows = cur.fetchall()

        return {"actions": [r[0] for r in rows]}

    finally:
        db.close()