from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime

from app.auth import get_current_user
from app.database import get_connection, record_audit

router = APIRouter(
    prefix="/incidents",
    tags=["Archive Incidents"]
)


# -----------------------------
# REQUEST MODELS
# -----------------------------
class IncidentCreate(BaseModel):
    serial_no: int
    incident_type: str
    severity: str = "MEDIUM"
    description: str


class IncidentResolve(BaseModel):
    resolution_notes: str


# -----------------------------
# REPORT INCIDENT
# -----------------------------
@router.post("/report")
async def report_incident(
    payload: IncidentCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["The Keeper", "The Chief"]:
        raise HTTPException(
            status_code=403,
            detail="Only archive staff can report incidents."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        # verify item exists
        cur.execute(
            """
            SELECT serial_no
            FROM items
            WHERE serial_no = %s
            """,
            (payload.serial_no,)
        )

        item = cur.fetchone()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Item not found."
            )

        cur.execute(
            """
            INSERT INTO archive_incidents (
                serial_no,
                incident_type,
                severity,
                reported_by,
                description
            )
            VALUES (%s,%s,%s,%s,%s)
            RETURNING incident_id
            """,
            (
                payload.serial_no,
                payload.incident_type,
                payload.severity,
                current_user["user_id"],
                payload.description
            )
        )

        incident_id = cur.fetchone()[0]

        # auto update item status
        if payload.incident_type == "MISSING":
            cur.execute(
                """
                UPDATE items
                SET availability_status = 'MISSING'
                WHERE serial_no = %s
                """,
                (payload.serial_no,)
            )

        elif payload.incident_type == "DAMAGED":
            cur.execute(
                """
                UPDATE items
                SET availability_status = 'DAMAGED'
                WHERE serial_no = %s
                """,
                (payload.serial_no,)
            )

        await record_audit(
            current_user["user_id"],
            "REPORT_INCIDENT",
            request,
            str(incident_id),
            f"{payload.incident_type} reported for item {payload.serial_no}"
        )

        conn.commit()

        return {
            "message": "Incident reported successfully",
            "incident_id": incident_id
        }

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()


# -----------------------------
# VIEW OPEN INCIDENTS
# -----------------------------
@router.get("/open")
def get_open_incidents(
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["The Keeper", "The Chief"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                incident_id,
                serial_no,
                incident_type,
                severity,
                status,
                reported_at
            FROM archive_incidents
            WHERE status != 'RESOLVED'
            ORDER BY reported_at DESC
            """
        )

        rows = cur.fetchall()

        return [
            {
                "incident_id": r[0],
                "serial_no": r[1],
                "incident_type": r[2],
                "severity": r[3],
                "status": r[4],
                "reported_at": r[5]
            }
            for r in rows
        ]

    finally:
        cur.close()
        conn.close()


# -----------------------------
# RESOLVE INCIDENT
# -----------------------------
@router.patch("/resolve/{incident_id}")
async def resolve_incident(
    incident_id: int,
    payload: IncidentResolve,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["The Keeper", "The Chief"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT serial_no, incident_type
            FROM archive_incidents
            WHERE incident_id = %s
            AND status != 'RESOLVED'
            """,
            (incident_id,)
        )

        incident = cur.fetchone()

        if not incident:
            raise HTTPException(
                status_code=404,
                detail="Incident not found."
            )

        serial_no = incident[0]

        cur.execute(
            """
            UPDATE archive_incidents
            SET
                status = 'RESOLVED',
                resolution_notes = %s,
                resolved_at = CURRENT_TIMESTAMP
            WHERE incident_id = %s
            """,
            (
                payload.resolution_notes,
                incident_id
            )
        )

        # restore availability
        cur.execute(
            """
            UPDATE items
            SET availability_status = 'AVAILABLE'
            WHERE serial_no = %s
            """,
            (serial_no,)
        )

        await record_audit(
            current_user["user_id"],
            "RESOLVE_INCIDENT",
            request,
            str(incident_id),
            f"Resolved incident {incident_id}"
        )

        conn.commit()

        return {
            "message": "Incident resolved successfully"
        }

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()