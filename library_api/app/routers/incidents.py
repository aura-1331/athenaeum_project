from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.auth import get_current_user
from app.database import get_connection
from app.audit_utils import audit_action  # 🛡️ Standardized auditing

router = APIRouter(prefix="/incidents", tags=["Archive Incidents"])

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
@audit_action("REPORT_INCIDENT")
@router.post("/report")
async def report_incident(
    payload: IncidentCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["The Keeper", "The Chief"]:
        raise HTTPException(status_code=403, detail="Forbidden.")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT serial_no FROM items WHERE serial_no = %s", (payload.serial_no,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Item not found.")

        cur.execute("""
            INSERT INTO archive_incidents (serial_no, incident_type, severity, reported_by, description)
            VALUES (%s, %s, %s, %s, %s) RETURNING incident_id
        """, (payload.serial_no, payload.incident_type, payload.severity, current_user["user_id"], payload.description))
        
        incident_id = cur.fetchone()[0]

        if payload.incident_type in ["MISSING", "DAMAGED"]:
            cur.execute("UPDATE items SET availability_status = %s WHERE serial_no = %s", 
                        (payload.incident_type, payload.serial_no))

        conn.commit()
        return {"message": "Incident reported successfully", "incident_id": incident_id}
    finally:
        cur.close(); conn.close()

# -----------------------------
# VIEW OPEN INCIDENTS
# -----------------------------
@audit_action("VIEW_OPEN_INCIDENTS")
@router.get("/open")
def get_open_incidents(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["The Keeper", "The Chief"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT incident_id, serial_no, incident_type, severity, status, reported_at
            FROM archive_incidents WHERE status != 'RESOLVED' ORDER BY reported_at DESC
        """)
        return [{"incident_id": r[0], "serial_no": r[1], "incident_type": r[2], 
                 "severity": r[3], "status": r[4], "reported_at": r[5]} for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()

# -----------------------------
# RESOLVE INCIDENT
# -----------------------------
@audit_action("RESOLVE_INCIDENT")
@router.patch("/resolve/{incident_id}")
async def resolve_incident(
    incident_id: int,
    payload: IncidentResolve,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["The Keeper", "The Chief"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        cur.execute("SELECT serial_no FROM archive_incidents WHERE incident_id = %s AND status != 'RESOLVED'", (incident_id,))
        incident = cur.fetchone()
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found or already resolved.")

        cur.execute("""
            UPDATE archive_incidents SET status = 'RESOLVED', resolution_notes = %s, resolved_at = CURRENT_TIMESTAMP
            WHERE incident_id = %s
        """, (payload.resolution_notes, incident_id))

        cur.execute("UPDATE items SET availability_status = 'AVAILABLE' WHERE serial_no = %s", (incident[0],))

        conn.commit()
        return {"message": "Incident resolved successfully"}
    finally:
        cur.close(); conn.close()