from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth import get_current_user
from app.database import get_connection

router = APIRouter(prefix="/profile", tags=["User Profile"])

@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Get Active Loans
        cur.execute("""
            SELECT l.loan_id, l.serial_no, w.title, l.due_date 
            FROM loans l
            JOIN public.items i ON l.serial_no = i.serial_no
            JOIN public.works w ON i.work_id = w.work_id
            WHERE l.user_id = %s AND l.status = 'ACTIVE'
        """, (current_user['user_id'],))
        loans = cur.fetchall()

        # 2. Get Unpaid Fines
        cur.execute("""
            SELECT fine_id, amount, status 
            FROM fines 
            WHERE user_id = %s AND status = 'UNPAID'
        """, (current_user['user_id'],))
        fines = cur.fetchall()

        return {
            "user_info": {
                "name": current_user.get("name"),
                "email": current_user.get("email"),
                "role": current_user['role']
            },
            "active_loans": [
                {"loan_id": r[0], "serial_no": r[1], "title": r[2], "due_date": r[3].date()} 
                for r in loans
            ],
            "unpaid_fines": [
                {"fine_id": f[0], "amount": float(f[1]), "status": f[2]} 
                for f in fines
            ],
            "total_debt": sum(float(f[1]) for f in fines)
        }
    finally:
        cur.close()
        conn.close()