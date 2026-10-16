"""Archive incident reporting, review, history, and resolution routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_role
from app.database import get_connection
from app.audit_utils import audit_action
from app.routers.review_utils import _audit_ledger

router = APIRouter(prefix="/incidents", tags=["Archive Incidents"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class IncidentCreate(BaseModel):
    serial_no: int
    incident_type: str
    severity: str = "MEDIUM"
    description: str


class IncidentResolve(BaseModel):
    resolution_notes: str


# ---------------------------------------------------------------------------
# Report incident
# ---------------------------------------------------------------------------
@router.post(
    "/report",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))],
)
async def report_incident(
    payload: IncidentCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    # Validate the exact values supported by the incident UI.
    incident_type = str(payload.incident_type or "").strip().upper()
    severity = str(payload.severity or "").strip().upper()
    description = str(payload.description or "").strip()

    if incident_type not in {"MISSING", "DAMAGED"}:
        raise HTTPException(status_code=400, detail="Unknown incident type.")
    if severity not in {"LOW", "MEDIUM", "HIGH"}:
        raise HTTPException(status_code=400, detail="Unknown severity.")
    if not description:
        raise HTTPException(status_code=400, detail="Description is required.")
    if len(description) > 3000:
        raise HTTPException(status_code=400, detail="Description is too long.")

    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT availability_status, is_deleted
            FROM public.items
            WHERE serial_no = %s
            FOR UPDATE
            """,
            (payload.serial_no,),
        )
        item_row = cur.fetchone()
        if not item_row:
            raise HTTPException(status_code=404, detail="Item not found.")

        prior_status, is_deleted = item_row
        # Pending, rejected, deleted, or otherwise non-catalogued copies must not
        # be modified through incident reporting.
        if is_deleted or str(prior_status or "").strip().upper() in {"PENDING", "REJECTED"}:
            raise HTTPException(
                status_code=409,
                detail="Incidents can only be reported on approved, active items.",
            )

        cur.execute(
            """
            INSERT INTO public.archive_incidents
                (serial_no, incident_type, severity, reported_by, description)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING incident_id
            """,
            (
                payload.serial_no,
                incident_type,
                severity,
                current_user["user_id"],
                description,
            ),
        )
        incident_id = cur.fetchone()[0]

        # Reporting MISSING or DAMAGED changes the holding's availability state.
        new_status = incident_type
        cur.execute(
            """
            UPDATE public.items
            SET availability_status = %s
            WHERE serial_no = %s
              AND is_deleted = FALSE
            RETURNING availability_status
            """,
            (new_status, payload.serial_no),
        )
        changed_item = cur.fetchone()
        if not changed_item:
            raise HTTPException(
                status_code=409,
                detail="The holding changed before the incident could be recorded.",
            )
        new_status = changed_item[0]

        _audit_ledger(
            request=request,
            current_user=current_user,
            conn=conn,
            action_type="REPORT_INCIDENT",
            target_entity="INCIDENT",
            target_id=incident_id,
            category="PRESERVATION_INCIDENTS",
            http_method="POST",
            justification=description or f"Reported {severity} {incident_type} incident",
            diff={
                "incident_id": incident_id,
                "serial_no": payload.serial_no,
                "incident_type": incident_type,
                "severity": severity,
                "description": description,
                "item_status_transition": {
                    "from": prior_status,
                    "to": new_status,
                },
            },
            extra={
                "incident_id": incident_id,
                "serial_no": payload.serial_no,
                "severity": severity,
            },
        )

        conn.commit()
        return {
            "message": "Incident reported successfully",
            "incident_id": incident_id,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        print(f"Incident report failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="Unable to report incident.") from exc
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# View open incidents (read access is audited by the decorator)
# ---------------------------------------------------------------------------
@router.get(
    "/open",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))],
)
@audit_action("VIEW_OPEN_INCIDENTS")
def get_open_incidents(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT incident_id, serial_no, incident_type, severity, status, reported_at
            FROM public.archive_incidents
            WHERE status <> 'RESOLVED'
            ORDER BY reported_at DESC, incident_id DESC
            """
        )
        return [
            {
                "incident_id": row[0],
                "serial_no": row[1],
                "incident_type": row[2],
                "severity": row[3],
                "status": row[4],
                "reported_at": row[5],
            }
            for row in cur.fetchall()
        ]
    except Exception as exc:
        conn.rollback()
        print(f"Open incident lookup failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="Unable to load open incidents.") from exc
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# Incident history
# ---------------------------------------------------------------------------
@router.get(
    "/history",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))],
)
@audit_action("VIEW_INCIDENT_HISTORY")
def get_incident_history(
    request: Request,
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, max_length=300),
    incident_type: str | None = Query(None),
    severity: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    sort: str = Query("newest"),
):
    if incident_type and incident_type not in {"MISSING", "DAMAGED"}:
        raise HTTPException(status_code=400, detail="Unknown incident type filter.")
    if severity and severity not in {"LOW", "MEDIUM", "HIGH"}:
        raise HTTPException(status_code=400, detail="Unknown severity filter.")

    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        conditions = ["ai.status = 'RESOLVED'"]
        params: list[object] = []

        if search:
            conditions.append(
                """
                (
                    CAST(ai.incident_id AS TEXT) ILIKE %s
                    OR CAST(ai.serial_no AS TEXT) ILIKE %s
                    OR COALESCE(i.accession_no, '') ILIKE %s
                    OR COALESCE(ai.description, '') ILIKE %s
                    OR COALESCE(ai.resolution_notes, '') ILIKE %s
                    OR COALESCE(reporter.name, '') ILIKE %s
                )
                """
            )
            search_value = f"%{search}%"
            params.extend([search_value] * 6)

        if incident_type:
            conditions.append("ai.incident_type = %s")
            params.append(incident_type)
        if severity:
            conditions.append("ai.severity = %s")
            params.append(severity)
        if date_from:
            conditions.append("ai.reported_at >= %s::date")
            params.append(date_from)
        if date_to:
            conditions.append("ai.reported_at < (%s::date + INTERVAL '1 day')")
            params.append(date_to)

        where_clause = " AND ".join(conditions)
        order_clause = {
            "oldest": "ai.reported_at ASC, ai.incident_id ASC",
            "incident_id": "ai.incident_id DESC",
            "newest": "ai.reported_at DESC, ai.incident_id DESC",
        }.get(sort)
        if order_clause is None:
            raise HTTPException(
                status_code=400,
                detail="Sort must be newest, oldest, or incident_id.",
            )

        joins = """
            FROM public.archive_incidents ai
            LEFT JOIN public.items i ON i.serial_no = ai.serial_no
            LEFT JOIN public.users reporter ON reporter.user_id = ai.reported_by
            LEFT JOIN public.users assignee ON assignee.user_id = ai.assigned_to
        """
        cur.execute(
            f"SELECT COUNT(*) {joins} WHERE {where_clause}",
            tuple(params),
        )
        total = cur.fetchone()[0]
        offset = (page - 1) * page_size

        cur.execute(
            f"""
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
            {joins}
            WHERE {where_clause}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s
            """,
            tuple(params + [page_size, offset]),
        )
        rows = cur.fetchall()
        total_pages = (total + page_size - 1) // page_size if total else 0

        return {
            "items": [
                {
                    "incident_id": row[0],
                    "serial_no": row[1],
                    "accession_no": row[2],
                    "incident_type": row[3],
                    "severity": row[4],
                    "status": row[5],
                    "reported_by": row[6],
                    "reported_by_name": row[7],
                    "assigned_to": row[8],
                    "assigned_to_name": row[9],
                    "description": row[10],
                    "resolution_notes": row[11],
                    "reported_at": row[12],
                    "resolved_at": row[13],
                }
                for row in rows
            ],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        print(f"Incident history lookup failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="Unable to load incident history.") from exc
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# Resolve incident
# ---------------------------------------------------------------------------
@router.patch(
    "/resolve/{incident_id}",
    dependencies=[Depends(require_role(["The Keeper", "The Chief"]))],
)
async def resolve_incident(
    incident_id: int,
    payload: IncidentResolve,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    resolution_notes = str(payload.resolution_notes or "").strip()
    if not resolution_notes:
        raise HTTPException(status_code=400, detail="Resolution notes are required.")
    if len(resolution_notes) > 3000:
        raise HTTPException(status_code=400, detail="Resolution notes are too long.")

    conn = get_connection(request=request)
    cur = conn.cursor()
    try:
        # Lock the incident while resolving it so two requests cannot both resolve it.
        cur.execute(
            """
            SELECT serial_no, incident_type, severity, description, status
            FROM public.archive_incidents
            WHERE incident_id = %s
              AND status <> 'RESOLVED'
            FOR UPDATE
            """,
            (incident_id,),
        )
        incident = cur.fetchone()
        if not incident:
            raise HTTPException(
                status_code=404,
                detail="Incident not found or already resolved.",
            )

        affected_serial_no, incident_type, severity, description, prior_incident_status = incident

        cur.execute(
            """
            SELECT availability_status, is_deleted
            FROM public.items
            WHERE serial_no = %s
            FOR UPDATE
            """,
            (affected_serial_no,),
        )
        item_row = cur.fetchone()
        prior_item_status = item_row[0] if item_row else None
        item_deleted = bool(item_row[1]) if item_row else True
        resulting_item_status = prior_item_status

        cur.execute(
            """
            UPDATE public.archive_incidents
            SET status = 'RESOLVED',
                resolution_notes = %s,
                resolved_at = CURRENT_TIMESTAMP
            WHERE incident_id = %s
              AND status <> 'RESOLVED'
            RETURNING status
            """,
            (resolution_notes, incident_id),
        )
        resolved_row = cur.fetchone()
        if not resolved_row:
            raise HTTPException(
                status_code=409,
                detail="The incident changed before it could be resolved.",
            )

        # Only restore a live holding whose current state is actually MISSING or
        # DAMAGED. Never make a pending, rejected, deleted, or loaned item available.
        item_status_changed = False
        if (
            item_row
            and not item_deleted
            and str(prior_item_status or "").strip().upper() in {"MISSING", "DAMAGED"}
        ):
            cur.execute(
                """
                UPDATE public.items
                SET availability_status = 'AVAILABLE'
                WHERE serial_no = %s
                  AND is_deleted = FALSE
                  AND availability_status IN ('MISSING', 'DAMAGED')
                RETURNING availability_status
                """,
                (affected_serial_no,),
            )
            updated_item = cur.fetchone()
            if updated_item:
                resulting_item_status = updated_item[0]
                item_status_changed = True

        _audit_ledger(
            request=request,
            current_user=current_user,
            conn=conn,
            action_type="RESOLVE_INCIDENT",
            target_entity="INCIDENT",
            target_id=incident_id,
            category="PRESERVATION_INCIDENTS",
            http_method="PATCH",
            justification=resolution_notes,
            diff={
                "incident_id": incident_id,
                "serial_no": affected_serial_no,
                "incident_type": incident_type,
                "severity": severity,
                "description": description,
                "resolution_notes": resolution_notes,
                "status_transition": {
                    "from": prior_incident_status,
                    "to": resolved_row[0],
                },
                "item_status_transition": {
                    "from": prior_item_status,
                    "to": resulting_item_status,
                    "changed": item_status_changed,
                },
            },
            extra={
                "incident_id": incident_id,
                "serial_no": affected_serial_no,
                "item_status_changed": item_status_changed,
            },
            before={"status": prior_incident_status},
            after={"status": resolved_row[0]},
        )

        conn.commit()
        return {"message": "Incident resolved successfully"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        print(f"Incident resolution failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="Unable to resolve incident.") from exc
    finally:
        cur.close()
        conn.close()
