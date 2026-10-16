from fastapi import APIRouter, Depends, HTTPException, Request
import logging

from app.auth import get_current_user, require_role
from app.database import get_connection
from app.routers.review_utils import _audit_ledger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/status-transitions",
    dependencies=[Depends(require_role(["The Chief"]))],
)
def status_transition_counts(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    conn = None
    cursor = None
    try:
        conn = get_connection(request=request)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT old_status, new_status, COUNT(*)
            FROM public.status_audit
            GROUP BY old_status, new_status
            ORDER BY COUNT(*) DESC
            """
        )

        rows = cursor.fetchall()
        result = [
            {"old_status": row[0], "new_status": row[1], "count": row[2]}
            for row in rows
        ]

        # Record access to this Chief-only governance analytics endpoint.
        _audit_ledger(
            request=request,
            current_user=current_user,
            conn=conn,
            action_type="ANALYTICS_STATUS_TRANSITIONS_VIEW",
            target_entity="STATUS_AUDIT",
            target_id="aggregate",
            category="AUDIT_ANALYTICS",
            justification="Accessed status-transition analytics.",
            diff={"returned_groups": len(result)},
            extra={"returned_groups": len(result)},
            http_method="GET",
        )
        conn.commit()
        return result

    except Exception as exc:
        logger.exception("Failed to retrieve status-transition analytics")
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                logger.warning("Rollback failed after analytics request error")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        ) from exc
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                logger.warning("Failed to close analytics database cursor")
        if conn is not None:
            try:
                conn.close()
            except Exception:
                logger.warning("Failed to close analytics database connection")
