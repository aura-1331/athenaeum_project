from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth import get_current_user
from app.database import get_connection
from app.audit_utils import audit_action

router = APIRouter(prefix="/profile", tags=["User Profile"])


@router.get("/me")
@audit_action("VIEW_PROFILE")
async def get_my_profile(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Return the authenticated user's profile, active loans, and unpaid fines."""
    conn = get_connection(request=request)
    cur = conn.cursor()

    try:
        user_id = current_user["user_id"]

        # 1. Get active loans belonging to the authenticated user.
        cur.execute(
            """
            SELECT l.loan_id, l.serial_no, w.title, l.due_date
            FROM public.loans AS l
            JOIN public.items AS i ON l.serial_no = i.serial_no
            JOIN public.works AS w ON i.work_id = w.work_id
            WHERE l.user_id = %s
              AND l.status = 'ACTIVE'
            ORDER BY l.due_date ASC NULLS LAST, l.loan_id ASC
            """,
            (user_id,),
        )
        loans = cur.fetchall()

        # 2. Get unpaid fines belonging to the authenticated user.
        cur.execute(
            """
            SELECT fine_id, amount, status
            FROM public.fines
            WHERE user_id = %s
              AND status = 'UNPAID'
            ORDER BY fine_id ASC
            """,
            (user_id,),
        )
        fines = cur.fetchall()

        unpaid_fines = [
            {
                "fine_id": fine[0],
                "amount": float(fine[1] or 0),
                "status": fine[2],
            }
            for fine in fines
        ]

        return {
            "user_info": {
                "name": current_user.get("name"),
                "email": current_user.get("email"),
                "role": current_user["role"],
            },
            "active_loans": [
                {
                    "loan_id": row[0],
                    "serial_no": row[1],
                    "title": row[2],
                    # Leave date serialization to FastAPI. PostgreSQL DATE values
                    # are already datetime.date objects and have no .date() method.
                    "due_date": row[3],
                }
                for row in loans
            ],
            "unpaid_fines": unpaid_fines,
            "total_debt": sum(fine["amount"] for fine in unpaid_fines),
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"Profile lookup failed for user {current_user.get('user_id')}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Unable to load the user profile.",
        ) from exc
    finally:
        cur.close()
        conn.close()
