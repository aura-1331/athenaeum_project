# app/routers/circulation.py

from fastapi import APIRouter, Depends, HTTPException, Request, status
from datetime import datetime, timedelta, timezone  # 🛡️ Added 'timedelta' and 'timezone'
from app.auth import get_current_user
from app.database import get_connection, record_audit, get_config_value
from pydantic import BaseModel

router = APIRouter(prefix="/circulation", tags=["Circulation & Fines"])

class ReturnRequest(BaseModel):
    notes: str | None = None

# --- CONSTANTS ---
# Replace the hardcoded rate with:

# ---------------------------------------------------------------------------------------------------------------------#
# ---------------------------------BOOK ISSUING LOGIC------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------------------------#

@router.post("/issue/{serial_no}", status_code=201)
async def issue_book(
    serial_no: int,
    borrower_id: int,
    days: int = 14,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] not in ["The Keeper", "The Chief"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = get_connection()
    cur = conn.cursor()
    try:
        if days == 14:
            db_days = get_config_value('DEFAULT_LOAN_DAYS')
            if db_days:
                days = int(db_days)

        cur.execute("SELECT SUM(amount) FROM fines WHERE user_id = %s AND status = 'UNPAID'", (borrower_id,))
        debt = cur.fetchone()[0] or 0
        if debt > 0:
            raise HTTPException(status_code=400, detail=f"Outstanding fines: {debt}")

        cur.execute("SELECT availability_status, is_deleted FROM public.items WHERE serial_no = %s", (serial_no,))
        item = cur.fetchone()
        if not item or item[1] is True:
            raise HTTPException(status_code=404, detail="Not found")
        if item[0] != 'AVAILABLE':
            raise HTTPException(status_code=400, detail="Unavailable")

        due_date = datetime.now(timezone.utc) + timedelta(days=days)

        cur.execute("""
            INSERT INTO loans (serial_no, user_id, due_date, issued_by, status)
            VALUES (%s, %s, %s, %s, 'ACTIVE') RETURNING loan_id
        """, (serial_no, borrower_id, due_date, current_user['user_id']))
        loan_id = cur.fetchone()[0]

        cur.execute(
    """
    UPDATE public.items
    SET availability_status = 'IN_RESEARCH_USE'
    WHERE serial_no = %s
    """,
    (serial_no,)
    )
        
        await record_audit(current_user['user_id'], "ISSUE_BOOK", request, str(loan_id), f"Assigned item {serial_no} for research access")
        conn.commit()
        return {"loan_id": loan_id, "due_date": due_date}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# ----------------------------------------------------------------------------------------------------------------------------------------#
# -------------------------------------------------BOOK  RETURNING LOGIC------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------------------------------------------#        

@router.post("/return/{serial_no}")
async def return_book(
    serial_no: int,
    request: Request,
    return_data: ReturnRequest,
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] not in ["The Keeper", "The Chief"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT loan_id, user_id, due_date FROM loans WHERE serial_no = %s AND status = 'ACTIVE'", (serial_no,))
        loan = cur.fetchone()
        if not loan:
            raise HTTPException(status_code=404, detail="No active loan")

        loan_id, borrower_id, due_date = loan
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)
            
        return_date = datetime.now(timezone.utc)
        
        cur.execute("UPDATE loans SET return_date = %s, status = 'RETURNED', notes = %s WHERE loan_id = %s", 
                    (return_date, return_data.notes, loan_id))
        cur.execute("UPDATE public.items SET availability_status = 'AVAILABLE' WHERE serial_no = %s", (serial_no,))

        fine_amount = 0
        days_late = 0
        if return_date > due_date:
            days_late = (return_date - due_date).days
            if days_late > 0:
                rate = get_config_value('DAILY_FINE_RATE') or 10.0
                fine_amount = days_late * float(rate)
                cur.execute("INSERT INTO fines (loan_id, user_id, amount, status) VALUES (%s, %s, %s, 'UNPAID')",
                            (loan_id, borrower_id, fine_amount))

        await record_audit(current_user['user_id'], "RETURN_BOOK", request, str(loan_id), f"Returned {serial_no}")
        conn.commit()
        return {"status": "success", "fine": fine_amount}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
# ----------------------------------------------------------------------------------------------------------------------------------------#
# -------------------------------------------------RETURNING OVERDUE LOGIC------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------------------------------------------#        


@router.get("/overdue", tags=["Circulation Monitoring"])
async def list_overdue_books(current_user: dict = Depends(get_current_user)):
    """Lists all books that are past their due date but haven't been returned."""
    if current_user['role'] not in ["The Keeper", "The Chief"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                l.loan_id, l.serial_no, w.title, u.name as borrower, 
                l.due_date, (CURRENT_TIMESTAMP - l.due_date) as delay
            FROM loans l
            JOIN public.items i ON l.serial_no = i.serial_no
            JOIN public.works w ON i.work_id = w.work_id
            JOIN users u ON l.user_id = u.user_id
            WHERE l.status = 'ACTIVE' AND l.due_date < CURRENT_TIMESTAMP
            ORDER BY l.due_date ASC
        """)
        rows = cur.fetchall()
        
        overdue_list = [
            {
                "loan_id": r[0],
                "serial_no": r[1],
                "title": r[2],
                "borrower": r[3],
                "due_date": r[4].date(),
                "days_late": r[5].days
            } for r in rows
        ]
        
        return {"count": len(overdue_list), "overdue_items": overdue_list}
    finally:
        cur.close()
        conn.close()         

# ----------------------------------------------------------------------------------------------------------------------------------------#
# -------------------------------------------------------LATE FINE LOGIC------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------------------------------------------#        


@router.post("/fines/pay/{fine_id}")
async def pay_fine(
    fine_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Records payment of a fine."""
    if current_user['role'] not in ["The Keeper", "The Chief"]:
        raise HTTPException(status_code=403, detail="Staff only.")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE fines SET status = 'PAID', paid_at = CURRENT_TIMESTAMP, processed_by = %s
            WHERE fine_id = %s AND status = 'UNPAID' RETURNING amount, user_id
        """, (current_user['user_id'], fine_id))
        res = cur.fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="Fine not found or already paid.")

        await record_audit(current_user['user_id'], "PAY_FINE", request, str(fine_id), f"Received {res[0]} from User {res[1]}")
        conn.commit()
        return {"status": "paid", "amount": res[0]}
    finally:
        cur.close()
        conn.close()

       