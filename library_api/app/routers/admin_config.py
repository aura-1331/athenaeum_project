from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth import get_current_user, require_role  # 1. Imported require_role
from app.database import get_connection
from app.audit_utils import audit_action

router = APIRouter(
    prefix="/admin/config",
    tags=["System Configuration"]
)

@audit_action("UPDATE_CONFIG")
@router.patch("/{key}", dependencies=[Depends(require_role(["The Chief"]))]) # 2. Added Security Guard
async def update_config(
    key: str,
    new_value: float,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    # 3. Manual 'if current_user["role"] != "The Chief":' block removed
    
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            UPDATE system_config
            SET
                config_value = %s,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = %s
            WHERE config_key = %s
            RETURNING config_key
            """,
            (
                new_value,
                current_user["user_id"],
                key.upper()
            )
        )

        result = cur.fetchone()

        if not result:
            conn.rollback()
            raise HTTPException(
                status_code=404,
                detail="Configuration key not found."
            )

        conn.commit()

        return {
            "status": "success",
            "message": f"{key.upper()} updated to {new_value}"
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        print(f"Config Update Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update configuration."
        )
    finally:
        cur.close()
        conn.close()