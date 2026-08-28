from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional

from app.auth import get_current_user, require_role
from app.database import get_connection
from app.audit_utils import audit_action


router = APIRouter(
    prefix="/authority",
    tags=["Authority Management"]
)


# ============================================================
# LIST AUTHORITIES
# ============================================================

@router.get(
    "/",
    dependencies=[Depends(require_role(["The Chief"]))]
)
@audit_action("VIEW_AUTHORITIES")
def list_authorities(
    request: Request,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT
                authority_id,
                authority_code,
                preferred_name,
                authority_type,
                status,
                notes,
                created_at,
                updated_at,
                created_by,
                updated_by,
                verified_at,
                verified_by
            FROM public.authority_records
        """

        params = []

        if status:
            query += " WHERE status = %s"
            params.append(status.upper())

        query += " ORDER BY authority_id"

        cur.execute(query, tuple(params))

        columns = [desc[0] for desc in cur.description]

        rows = [
            dict(zip(columns, row))
            for row in cur.fetchall()
        ]

        return {
            "data": rows,
            "total": len(rows)
        }

    finally:
        cur.close()
        conn.close()


# ============================================================
# GET ONE AUTHORITY
# ============================================================

@router.get(
    "/{authority_id}",
    dependencies=[Depends(require_role(["The Chief"]))]
)
@audit_action("VIEW_AUTHORITY")
def get_authority(
    authority_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                authority_id,
                authority_code,
                preferred_name,
                authority_type,
                status,
                notes,
                created_at,
                updated_at,
                created_by,
                updated_by,
                verified_at,
                verified_by
            FROM public.authority_records
            WHERE authority_id = %s
            """,
            (authority_id,)
        )

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Authority record not found."
            )

        columns = [desc[0] for desc in cur.description]

        authority = dict(zip(columns, row))

        # --------------------------------------------------------
        # GET VARIANT NAMES
        # --------------------------------------------------------

        cur.execute(
            """
            SELECT
                variant_id,
                variant_name,
                variant_type,
                notes,
                created_at,
                created_by
            FROM public.authority_variants
            WHERE authority_id = %s
            ORDER BY variant_id
            """,
            (authority_id,)
        )

        variant_columns = [desc[0] for desc in cur.description]

        authority["variants"] = [
            dict(zip(variant_columns, variant))
            for variant in cur.fetchall()
        ]

        # --------------------------------------------------------
        # GET WORKS CONNECTED TO THIS AUTHORITY
        # --------------------------------------------------------

        cur.execute(
            """
            SELECT
                wa.work_id,
                wa.relationship_type,
                wa.sequence_no,
                w.title,
                w.author
            FROM public.work_authorities wa
            LEFT JOIN public.works w
                ON w.work_id = wa.work_id
            WHERE wa.authority_id = %s
            ORDER BY wa.sequence_no, wa.work_id
            """,
            (authority_id,)
        )

        work_columns = [desc[0] for desc in cur.description]

        authority["works"] = [
            dict(zip(work_columns, work))
            for work in cur.fetchall()
        ]

        return authority

    finally:
        cur.close()
        conn.close()


# ============================================================
# VERIFY AUTHORITY
# ============================================================

@router.patch(
    "/{authority_id}/verify",
    dependencies=[Depends(require_role(["The Chief"]))]
)
@audit_action("AUTHORITY_VERIFY")
def verify_authority(
    authority_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                authority_id,
                authority_code,
                preferred_name,
                status
            FROM public.authority_records
            WHERE authority_id = %s
            FOR UPDATE
            """,
            (authority_id,)
        )

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Authority record not found."
            )

        existing_status = row[3]

        # --------------------------------------------------------
        # ALREADY VERIFIED
        # --------------------------------------------------------

        if existing_status == "VERIFIED":
            raise HTTPException(
                status_code=409,
                detail="Authority is already verified."
            )

        # --------------------------------------------------------
        # REJECTED CANNOT BE VERIFIED DIRECTLY
        # --------------------------------------------------------

        if existing_status == "REJECTED":
            raise HTTPException(
                status_code=409,
                detail="Rejected authority cannot be verified directly."
            )

        # --------------------------------------------------------
        # VERIFY
        # --------------------------------------------------------

        cur.execute(
            """
            UPDATE public.authority_records
            SET
                status = 'VERIFIED',
                verified_at = CURRENT_TIMESTAMP,
                verified_by = %s,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = %s
            WHERE authority_id = %s
            RETURNING
                authority_id,
                authority_code,
                preferred_name,
                authority_type,
                status,
                verified_at,
                verified_by,
                updated_at,
                updated_by
            """,
            (
                current_user["user_id"],
                current_user["user_id"],
                authority_id
            )
        )

        result = cur.fetchone()

        conn.commit()

        columns = [desc[0] for desc in cur.description]

        return {
            "status": "success",
            "message": "Authority verified successfully.",
            "authority": dict(zip(columns, result))
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        print(f"Authority verification error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Failed to verify authority."
        )

    finally:
        cur.close()
        conn.close()


# ============================================================
# REJECT AUTHORITY
# ============================================================

@router.patch(
    "/{authority_id}/reject",
    dependencies=[Depends(require_role(["The Chief"]))]
)
@audit_action("AUTHORITY_REJECT")
def reject_authority(
    authority_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                authority_id,
                authority_code,
                preferred_name,
                status
            FROM public.authority_records
            WHERE authority_id = %s
            FOR UPDATE
            """,
            (authority_id,)
        )

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Authority record not found."
            )

        existing_status = row[3]

        # --------------------------------------------------------
        # VERIFIED CANNOT BE REJECTED DIRECTLY
        # --------------------------------------------------------

        if existing_status == "VERIFIED":
            raise HTTPException(
                status_code=409,
                detail="Verified authority cannot be rejected directly."
            )

        # --------------------------------------------------------
        # ALREADY REJECTED
        # --------------------------------------------------------

        if existing_status == "REJECTED":
            raise HTTPException(
                status_code=409,
                detail="Authority is already rejected."
            )

        # --------------------------------------------------------
        # REJECT
        # --------------------------------------------------------

        cur.execute(
            """
            UPDATE public.authority_records
            SET
                status = 'REJECTED',
                updated_at = CURRENT_TIMESTAMP,
                updated_by = %s
            WHERE authority_id = %s
            RETURNING
                authority_id,
                authority_code,
                preferred_name,
                authority_type,
                status,
                updated_at,
                updated_by
            """,
            (
                current_user["user_id"],
                authority_id
            )
        )

        result = cur.fetchone()

        conn.commit()

        columns = [desc[0] for desc in cur.description]

        return {
            "status": "success",
            "message": "Authority rejected successfully.",
            "authority": dict(zip(columns, result))
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        print(f"Authority rejection error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Failed to reject authority."
        )

    finally:
        cur.close()
        conn.close()