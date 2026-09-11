# app/routers/incidents.py

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from app.auth import get_current_user, require_role
from app.database import get_connection
from app.audit_utils import audit_action
from app.services.audit_service import log_audit_activity

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
@router.post(
    "/report",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))]
)
async def report_incident(
    payload: IncidentCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        # 1. Fetch item availability baseline
        cur.execute(
            "SELECT availability_status FROM items WHERE serial_no = %s", 
            (payload.serial_no,)
        )
        item_row = cur.fetchone()
        if not item_row:
            raise HTTPException(status_code=404, detail="Item not found.")
        
        prior_status = item_row[0]

        # 2. Record incident
        cur.execute("""
            INSERT INTO archive_incidents (serial_no, incident_type, severity, reported_by, description)
            VALUES (%s, %s, %s, %s, %s) RETURNING incident_id
        """, (payload.serial_no, payload.incident_type, payload.severity, current_user["user_id"], payload.description))
        
        incident_id = cur.fetchone()[0]

        # 3. Transition item status if applicable
        new_status = prior_status
        if payload.incident_type in ["MISSING", "DAMAGED"]:
            new_status = payload.incident_type
            cur.execute(
                "UPDATE items SET availability_status = %s WHERE serial_no = %s", 
                (new_status, payload.serial_no)
            )

        conn.commit()

        # 4. Cryptographic ledger anchor
        actor_id = str(current_user.get("user_id", "UNKNOWN"))
        actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
        actor_role = str(current_user.get("role", "The Keeper"))

        log_audit_activity(
            request=request,
            user_id=actor_id,
            username=actor_name,
            role=actor_role,
            designation=str(current_user.get("designation") or actor_role),
            category="PRESERVATION_INCIDENTS",
            action_type="REPORT_INCIDENT",
            target_entity="INCIDENT",
            target_id=str(incident_id),
            endpoint=request.url.path,
            http_method="POST",
            justification=payload.description or f"Reported {payload.severity} {payload.incident_type} incident",
            diff_payload={
                "incident_id": incident_id,
                "serial_no": payload.serial_no,
                "incident_type": payload.incident_type,
                "severity": payload.severity,
                "description": payload.description,
                "item_status_transition": {
                    "from": prior_status,
                    "to": new_status
                }
            },
            extra_metadata={
                "incident_id": incident_id,
                "serial_no": payload.serial_no,
                "severity": payload.severity
            }
        )

        return {"message": "Incident reported successfully", "incident_id": incident_id}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# -----------------------------
# VIEW OPEN INCIDENTS
# -----------------------------
@audit_action("VIEW_OPEN_INCIDENTS")
@router.get(
    "/open",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))]
)
def get_open_incidents(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT incident_id, serial_no, incident_type, severity, status, reported_at
            FROM archive_incidents WHERE status != 'RESOLVED' ORDER BY reported_at DESC
        """)
        return [{"incident_id": r[0], "serial_no": r[1], "incident_type": r[2], 
                 "severity": r[3], "status": r[4], "reported_at": r[5]} for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


# -----------------------------
# INCIDENT HISTORY
# -----------------------------
@audit_action("VIEW_INCIDENT_HISTORY")
@router.get(
    "/history",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))]
)
def get_incident_history(
    request: Request,
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
    incident_type: str | None = Query(None),
    severity: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    sort: str = Query("newest")
):
    conn = get_connection(request=request)
    cur = conn.cursor()

    try:
        conditions = ["ai.status = 'RESOLVED'"]
        params = []

        if search:
            conditions.append("""
                (
                    CAST(ai.incident_id AS TEXT) ILIKE %s
                    OR CAST(ai.serial_no AS TEXT) ILIKE %s
                    OR COALESCE(i.accession_no, '') ILIKE %s
                    OR COALESCE(ai.description, '') ILIKE %s
                    OR COALESCE(ai.resolution_notes, '') ILIKE %s
                    OR COALESCE(reporter.name, '') ILIKE %s
                )
            """)

            search_value = f"%{search}%"
            params.extend([search_value] * 6)

        if incident_type:
            conditions.append("ai.incident_type = %s")
            params.append(incident_type)

        if severity:
            conditions.append("ai.severity = %s")
            params.append(severity)

        if date_from:
            conditions.append("ai.reported_at >= %s")
            params.append(date_from)

        if date_to:
            conditions.append("ai.reported_at < (%s::date + INTERVAL '1 day')")
            params.append(date_to)

        where_clause = " AND ".join(conditions)

        if sort == "oldest":
            order_clause = "ai.reported_at ASC"
        elif sort == "incident_id":
            order_clause = "ai.incident_id DESC"
        else:
            order_clause = "ai.reported_at DESC"

        count_query = f"""
            SELECT COUNT(*)
            FROM archive_incidents ai
            LEFT JOIN items i ON i.serial_no = ai.serial_no
            LEFT JOIN users reporter ON reporter.user_id = ai.reported_by
            LEFT JOIN users assignee ON assignee.user_id = ai.assigned_to
            WHERE {where_clause}
        """

        cur.execute(count_query, params)
        total = cur.fetchone()[0]

        offset = (page - 1) * page_size

        history_query = f"""
            SELECT
                ai.incident_id,
                ai.serial_no,
                i.accession_no,
                ai.incident_type,
                ai.severity,
                ai.status,
                ai.reported_by,
                reporter.name AS reported_by_name,
                ai.assigned_to,
                assignee.name AS assigned_to_name,
                ai.description,
                ai.resolution_notes,
                ai.reported_at,
                ai.resolved_at
            FROM archive_incidents ai
            LEFT JOIN items i ON i.serial_no = ai.serial_no
            LEFT JOIN users reporter ON reporter.user_id = ai.reported_by
            LEFT JOIN users assignee ON assignee.user_id = ai.assigned_to
            WHERE {where_clause}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s
        """

        cur.execute(history_query, params + [page_size, offset])
        rows = cur.fetchall()

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "items": [
                {
                    "incident_id": r[0],
                    "serial_no": r[1],
                    "accession_no": r[2],
                    "incident_type": r[3],
                    "severity": r[4],
                    "status": r[5],
                    "reported_by": r[6],
                    "reported_by_name": r[7],
                    "assigned_to": r[8],
                    "assigned_to_name": r[9],
                    "description": r[10],
                    "resolution_notes": r[11],
                    "reported_at": r[12],
                    "resolved_at": r[13]
                }
                for r in rows
            ],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        }

    finally:
        cur.close()
        conn.close()


# -----------------------------
# RESOLVE INCIDENT
# -----------------------------
@audit_action("RESOLVE_INCIDENT")
@router.patch(
    "/resolve/{incident_id}",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))]
)
async def resolve_incident(
    incident_id: int,
    payload: IncidentResolve,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        # 1. Fetch incident details and affected serial_no
        cur.execute("""
            SELECT serial_no, incident_type, severity, description 
            FROM archive_incidents 
            WHERE incident_id = %s AND status != 'RESOLVED'
        """, (incident_id,))
        incident = cur.fetchone()
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found or already resolved.")

        affected_serial_no = incident[0]
        incident_type = incident[1]

        # 2. Mark incident as resolved
        cur.execute("""
            UPDATE archive_incidents 
            SET status = 'RESOLVED', resolution_notes = %s, resolved_at = CURRENT_TIMESTAMP
            WHERE incident_id = %s
        """, (payload.resolution_notes, incident_id))

        # 3. Restore holding status to AVAILABLE
        cur.execute(
            "UPDATE items SET availability_status = 'AVAILABLE' WHERE serial_no = %s", 
            (affected_serial_no,)
        )

        conn.commit()

        # 4. Cryptographic ledger anchor
        actor_id = str(current_user.get("user_id", "UNKNOWN"))
        actor_name = str(current_user.get("username") or current_user.get("name") or "Archive Operator")
        actor_role = str(current_user.get("role", "The Keeper"))

        log_audit_activity(
            request=request,
            user_id=actor_id,
            username=actor_name,
            role=actor_role,
            designation=str(current_user.get("designation") or actor_role),
            category="PRESERVATION_INCIDENTS",
            action_type="RESOLVE_INCIDENT",
            target_entity="INCIDENT",
            target_id=str(incident_id),
            endpoint=request.url.path,
            http_method="PATCH",
            justification=payload.resolution_notes or f"Resolved incident {incident_id} for holding {affected_serial_no}",
            diff_payload={
                "incident_id": incident_id,
                "serial_no": affected_serial_no,
                "incident_type": incident_type,
                "resolution_notes": payload.resolution_notes,
                "status_transition": {"from": "OPEN", "to": "RESOLVED"},
                "item_status_transition": {"from": incident_type, "to": "AVAILABLE"}
            },
            extra_metadata={
                "incident_id": incident_id,
                "serial_no": affected_serial_no
            }
        )

        return {"message": "Incident resolved successfully"}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()