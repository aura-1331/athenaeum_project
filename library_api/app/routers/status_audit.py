from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional, Dict, Any, List
from app.database import get_connection
from app.auth import get_current_user, require_role
from app.audit_utils import audit_action

router = APIRouter(prefix="/status_audit", tags=["status_audit"])

def generate_field_diffs(action_type: str, old_val: Optional[dict], new_val: Optional[dict]) -> List[str]:
    diffs = []
    old_val, new_val = old_val or {}, new_val or {}
    ignored = {'updated_at', 'changed_at', 'timestamp', 'id', 'created_at', 'work_id', 'serial_no', 'status'}
    
    if action_type == 'INSERT':
        details = [f"{k.replace('_', ' ')}: \"{v}\"" for k, v in new_val.items() if k not in ignored and v]
        return [f"Created record entry -> {', '.join(details)}"] if details else ["Registered new entry."]
    if action_type == 'DELETE': return ["Removed entry."]

    all_keys = set(old_val.keys()).union(set(new_val.keys()))
    for key in sorted(all_keys):
        if key in ignored: continue
        if old_val.get(key) != new_val.get(key):
            diffs.append(f"Changed {key.replace('_', ' ')}: [{old_val.get(key)}] to [{new_val.get(key)}]")
    return diffs

@audit_action("VIEW_SYSTEM_LOGS")
@router.get("/system-logs", dependencies=[Depends(require_role(["The Chief"]))]) # 🛡️ SECURED
def list_system_audit_logs(
    request: Request,
    limit: int = 100, 
    offset: int = 0, 
    action_filter: Optional[str] = None,
    actor_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT id, actor_username, actor_role, user_id, action_type, 
                   target_module, target_id, old_value, new_value, 
                   device_id, ip_address, change_reason, 
                   to_char(timestamp, 'DD-MM-YYYY HH24:MI:SS') as timestamp
            FROM public.system_audit_log
        """
        where, params = [], []
        if action_filter:
            where.append("action_type = %s"); params.append(action_filter.upper())
        if actor_filter:
            where.append("actor_username ILIKE %s"); params.append(f"%{actor_filter}%")
        
        if where: query += " WHERE " + " AND ".join(where)
        query += " ORDER BY id DESC"
        
        cursor.execute(query, tuple(params))
        raw_rows = cursor.fetchall()
        normalized_rows = [dict(zip([d[0] for d in cursor.description], row)) for row in raw_rows]

        grouped_logs = []
        skip_indices = set()

        for i, current in enumerate(normalized_rows):
            if i in skip_indices: continue

            initial_diffs = generate_field_diffs(current["action_type"], current["old_value"], current["new_value"])
            seen_diffs = set(initial_diffs)
            combined_diffs = list(initial_diffs)
            
            target_id_display = current["target_id"]
            resolved_reason = current["change_reason"]
            
            for j in range(i + 1, min(i + 8, len(normalized_rows))):
                candidate = normalized_rows[j]
                if current["timestamp"] == candidate["timestamp"] and current["actor_username"] == candidate["actor_username"]:
                    skip_indices.add(j)
                    if candidate["change_reason"] and candidate["change_reason"] not in ("Routine operational adjustment", "New registration initialization sequencing"):
                        resolved_reason = candidate["change_reason"]
                    
                    more_diffs = generate_field_diffs(candidate["action_type"], candidate["old_value"], candidate["new_value"])
                    for diff_line in more_diffs:
                        if diff_line not in seen_diffs:
                            seen_diffs.add(diff_line)
                            combined_diffs.append(diff_line)
                    if candidate["target_module"] == "items": target_id_display = candidate["target_id"]

            title_context = (current["new_value"] or {}).get("title") or (current["old_value"] or {}).get("title")
            summary_desc = f"Modified record metrics for asset: \"{title_context}\"" if title_context else (f"Registered entity #{target_id_display}" if current["action_type"] == "INSERT" else f"Update inside {current['target_module']}")

            grouped_logs.append({
                "id": current["id"], "timestamp": current["timestamp"],
                "actor_username": current["actor_username"], "actor_role": current["actor_role"],
                "user_id": current["user_id"] or 3, "action_type": "CREATE" if current["action_type"] == "INSERT" else current["action_type"],
                "target_id": target_id_display, "summary": summary_desc,
                "detailed_diffs": combined_diffs, "change_reason": resolved_reason or "New registration initialization sequencing",
                "device_id": current["device_id"] or "Desktop Browser Workstation", "ip_address": current["ip_address"] or "127.0.0.1"
            })
        
        return grouped_logs[offset : offset + limit]
    finally:
        cursor.close(); conn.close()