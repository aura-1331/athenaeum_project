from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth import get_current_user
from app.database import get_connection, record_audit

router = APIRouter(prefix="/admin/config", tags=["System Configuration"])

@router.patch("/{key}")
async def update_config(
    key: str, 
    new_value: float, 
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] != "The Chief":
        raise HTTPException(status_code=403, detail="Only The Chief can update system configurations.")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE system_config 
            SET config_value = %s, updated_at = CURRENT_TIMESTAMP, updated_by = %s
            WHERE config_key = %s
            RETURNING config_key
        """, (new_value, current_user['user_id'], key.upper()))
        
        result = cur.fetchone()
        
        if not result:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Configuration key not found.")

        await record_audit(
            user_id=current_user['user_id'],
            action_type="UPDATE_CONFIG",
            request=request,
            target_id=key.upper(),
            details=f"Policy Change: {key.upper()} updated to {new_value}"
        )

        conn.commit()
        return {"status": "success", "message": f"{key.upper()} updated to {new_value}"}
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Config Update Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update configuration.")
    finally:
        cur.close()
        conn.close()